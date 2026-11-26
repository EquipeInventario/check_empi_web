from datetime import datetime, timezone, timedelta
import base64
import hashlib
import hmac
import json
import time
import secrets
import logging
import os

import pymysql
from fastapi import FastAPI, Depends, HTTPException, Header, BackgroundTasks
from urllib.parse import urlsplit
from concurrent.futures import ThreadPoolExecutor
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

app = FastAPI(title="API Manutenção Predial", docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://manutencao-predial.inventario-pg.workers.dev",
        "https://manutencao-predial.pages.dev",
    ],
    allow_origin_regex=r"http://(?:localhost|127\.0\.0\.1)(?::[0-9]{1,5})?",
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Accept", "Authorization", "Content-Type"],
)
log = logging.getLogger(__name__)
TABLES = ("usuarios", "prioridades_os", "status_os", "ordens_servico", "historico_os", "anexos_os")
HEADERS = {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff", "X-API-Version": "vercel-16"}


@app.exception_handler(RequestValidationError)
async def invalid_request(request, exc):
    # Do not return submitted input, especially passwords, in validation errors.
    return JSONResponse({"detail": "Dados da requisição inválidos."}, status_code=422, headers=HEADERS)


def get_connection():
    DB_HOST = os.getenv("DB_HOST")
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_NAME = os.getenv("DB_NAME")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))

    if not all((DB_HOST, DB_USER, DB_PASSWORD, DB_NAME)) or not 1 <= DB_PORT <= 65535:
        raise ValueError("Configuração MySQL incompleta ou inválida")

    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        port=DB_PORT,
        charset="utf8mb4",
        autocommit=False,
        connect_timeout=5,
        read_timeout=5,
        write_timeout=5,
        ssl_verify_cert=True,
        ssl_verify_identity=True,
    )


@app.get("/")
def root():
    return JSONResponse({"status": "ok", "message": "API de Manutencao Predial funcionando"}, headers=HEADERS)

 
@app.get("/api/ping")
def ping():
    return JSONResponse({"status": "ok"}, headers=HEADERS)


@app.get("/api/health")
def health():
    try:
        conn = get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                if cursor.fetchone() != (1,):
                    raise RuntimeError("Resposta inesperada do MySQL")
                for table in TABLES:
                    cursor.execute(f"SELECT 1 FROM `{table}` LIMIT 0")
        finally:
            conn.close()
    except Exception as exc:
        log.warning("MySQL indisponível: %s", type(exc).__name__)
        return JSONResponse({"status": "unavailable", "database": "unavailable"}, status_code=503, headers=HEADERS)
    return JSONResponse({"status": "ok", "database": "connected"}, headers=HEADERS)

# Autenticação: cadastro de usuários exclusivamente no MySQL.
# Senhas novas usam PBKDF2; registros legados permanecem compatíveis.
ROLES = {"SOLICITANTE", "MANUTENCAO", "ADMINISTRADOR"}
TOKEN_TTL = 1800

class LoginInput(BaseModel):
    login: str = Field(min_length=1, max_length=80)
    senha: str = Field(min_length=1, max_length=255)

def auth_error(status=401):
    return HTTPException(status_code=status,
        detail="Usuário ou sessão inválidos." if status == 401 else "Autenticação indisponível.",
        headers={**HEADERS, **({"WWW-Authenticate": "Bearer"} if status == 401 else {})})

def auth_config():
    secret = os.getenv("AUTH_TOKEN_SECRET", "").encode("utf-8")
    if len(secret) < 32:
        raise auth_error(503)
    return secret

def b64(data):
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")

def credential_binding(stored):
    return b64(hmac.digest(auth_config(), b"credential:" + str(stored).encode("utf-8"), "sha256"))

def issue_token(user_id, stored, purpose="session"):
    secret = auth_config()
    payload = b64(json.dumps({"sub": int(user_id), "exp": int(time.time()) + TOKEN_TTL,
                              "nonce": secrets.token_urlsafe(16), "purpose":purpose,
                              "credential":credential_binding(stored)}, separators=(",", ":")).encode())
    return payload + "." + b64(hmac.digest(secret, payload.encode("ascii"), "sha256"))

def verify_token(token, purpose="session"):
    secret = auth_config()
    try:
        if len(token) > 1024: raise ValueError()
        payload, signature = token.split(".")
        expected = b64(hmac.digest(secret, payload.encode("ascii"), "sha256"))
        if not hmac.compare_digest(signature, expected): raise ValueError()
        claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        if type(claims["sub"]) is not int or claims["sub"] < 1 or claims["exp"] <= time.time():
            raise ValueError()
        if claims["purpose"] != purpose or not isinstance(claims["credential"],str):
            raise ValueError()
        return claims
    except (ValueError, KeyError, TypeError, UnicodeError):
        raise auth_error() from None

def find_auth_user(*, login=None, user_id=None):
    try:
        conn = get_connection()
        try:
            with conn.cursor() as cursor:
                if login is not None:
                    cursor.execute("SELECT id,nome,login,senha_hash,perfil,filial_id,ativo,senha_temporaria_expira_em,senha_temporaria_usada_em FROM usuarios WHERE login=%s LIMIT 1", (login,))
                else:
                    cursor.execute("SELECT id,nome,login,senha_hash,perfil,filial_id,ativo,senha_temporaria_expira_em,senha_temporaria_usada_em FROM usuarios WHERE id=%s LIMIT 1", (user_id,))
                return cursor.fetchone()
        finally:
            conn.close()
    except Exception as exc:
        log.warning("Autenticação indisponível: %s", type(exc).__name__)
        raise auth_error(503) from None

def public_user(row):
    return {"id": int(row[0]), "nome": row[1], "login": row[2], "perfil": row[4],
            "filial_id": str(row[5]) if row[5] is not None else None}

def allowed_user(row):
    return bool(row and row[4] in ROLES and row[6] == 1)

def temporary_pending(row):
    return any(row[7:9])

def authenticated_row(authorization,purpose="session"):
    if not authorization or not authorization.startswith("Bearer "):
        raise auth_error()
    claims=verify_token(authorization[7:],purpose)
    row=find_auth_user(user_id=claims["sub"])
    if not allowed_user(row) or not hmac.compare_digest(claims["credential"],credential_binding(row[3])):
        raise auth_error()
    return row

def current_user(authorization: str | None = Header(default=None)):
    row=authenticated_row(authorization)
    if temporary_pending(row): raise auth_error()
    return public_user(row)

def hash_password(password):
    salt=secrets.token_bytes(16)
    digest=hashlib.pbkdf2_hmac("sha256",password.encode("utf-8"),salt,600000)
    return "pbkdf2_sha256$600000$"+b64(salt)+"$"+b64(digest)

def verify_password(stored,password):
    stored=str(stored)
    if not stored.startswith("pbkdf2_sha256$"):
        return hmac.compare_digest(stored.encode("utf-8"),password.encode("utf-8"))
    try:
        _,rounds,salt,expected=stored.split("$")
        if rounds!="600000": return False
        raw=base64.urlsafe_b64decode(salt+"="*(-len(salt)%4))
        if len(raw)!=16: return False
        digest=hashlib.pbkdf2_hmac("sha256",password.encode("utf-8"),raw,600000)
        return hmac.compare_digest(b64(digest),expected)
    except (ValueError,TypeError):
        return False

@app.post("/api/auth/login")
def login(data: LoginInput):
    auth_config()
    name = data.login.strip()
    row = find_auth_user(login=name)
    if not allowed_user(row) or row[2] != name:
        raise auth_error()
    if not verify_password(row[3],data.senha):
        raise auth_error()
    if temporary_pending(row):
        now=db_now()
        if row[7] is None or row[8] is not None or row[7]<=now:
            raise auth_error()
        def consume(cursor):
            cursor.execute("UPDATE usuarios SET senha_temporaria_usada_em=%s WHERE id=%s AND senha_hash=%s AND ativo=1 AND senha_temporaria_expira_em>%s AND senha_temporaria_usada_em IS NULL",
                           (now,row[0],row[3],now))
            if cursor.rowcount!=1: raise auth_error()
        transaction(consume)
        return login_response(row,row[3],True)
    return login_response(row,row[3])

def login_response(row,stored,temporary=False):
    return JSONResponse({"token":issue_token(row[0],stored,"password_change" if temporary else "session"),
                         "expires_in":TOKEN_TTL,"usuario":public_user(row),"trocar_senha":temporary},headers=HEADERS)

class ChangePasswordInput(BaseModel):
    senha: str = Field(min_length=8,max_length=64)

@app.post("/api/auth/trocar-senha")
def change_temporary_password(data:ChangePasswordInput,authorization: str | None=Header(default=None)):
    row=authenticated_row(authorization,"password_change")
    if not temporary_pending(row) or row[7] is None or row[8] is None:
        raise auth_error()
    if not data.senha.strip() or verify_password(row[3],data.senha):
        raise order_error(422,"Informe uma senha definitiva diferente da temporária.")
    hashed=hash_password(data.senha)
    def write(cursor):
        cursor.execute("UPDATE usuarios SET senha_hash=%s,senha_temporaria_expira_em=NULL,senha_temporaria_usada_em=NULL WHERE id=%s AND senha_hash=%s AND ativo=1 AND senha_temporaria_expira_em IS NOT NULL AND senha_temporaria_usada_em IS NOT NULL",
                       (hashed,row[0],row[3]))
        if cursor.rowcount!=1: raise auth_error()
    transaction(write)
    return login_response(row,hashed)

@app.get("/api/auth/me")
def me(user=Depends(current_user)):
    return JSONResponse({"usuario": user}, headers=HEADERS)

# Cadastros de referência somente leitura; não retorna usuários ou OS.
@app.get("/api/cadastros-os")
def order_catalogs(user=Depends(current_user)):
    try:
        conn = get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id, filial FROM indicadores_matriz.filiais WHERE ativo = 'S' ORDER BY filial, id")
                branches = [{"id": int(row[0]), "name": row[1]} for row in cursor.fetchall()]
                if user["perfil"] != "ADMINISTRADOR":
                    branches = [b for b in branches if str(b["id"]) == user["filial_id"]]
                cursor.execute("SELECT id, descricao FROM prioridades_os WHERE ativo = 1 ORDER BY ordem, id")
                priorities = [{"id": int(row[0]), "name": row[1]} for row in cursor.fetchall()]
                cursor.execute("SELECT id, descricao FROM status_os WHERE ativo = 1 ORDER BY ordem, id")
                statuses = [{"id": int(row[0]), "name": row[1]} for row in cursor.fetchall()]
        finally:
            conn.close()
    except Exception as exc:
        log.warning("Cadastros OS indisponíveis: %s", type(exc).__name__)
        return JSONResponse({"status": "unavailable"}, status_code=503, headers=HEADERS)
    return JSONResponse({"filiais": branches, "prioridades": priorities, "status": statuses}, headers=HEADERS)

# Ordens de serviço: fonte única MySQL. Não recebe autor, número ou status do cliente.
class OrderInput(BaseModel):
    branchId: int = Field(gt=0)
    priorityId: int = Field(gt=0)
    location: str = Field(min_length=1, max_length=200)
    service: str = Field(min_length=1, max_length=20000)
    notes: str = Field(default="", max_length=20000)

class ActionInput(BaseModel):
    action: str
    detail: str = Field(default="", max_length=20000)
    notes: str = Field(default="", max_length=20000)
    ownerId: int | None = Field(default=None, gt=0)
    priorityId: int | None = Field(default=None, gt=0)
    due: str = Field(default="", max_length=10)

def order_error(status, detail):
    return HTTPException(status_code=status, detail=detail, headers=HEADERS)

def order_scope(user):
    if user["perfil"] == "ADMINISTRADOR":
        return "1=1", ()
    if not user["filial_id"]:
        return "1=0", ()
    return "o.filial_id=%s", (user["filial_id"],)

ORDER_SELECT = """
SELECT o.id,o.filial_id,o.local,o.descricao,o.prioridade_id,p.descricao,s.descricao,
       o.aberto_por,u.nome,o.responsavel_id,r.nome,o.data_abertura,o.data_inicio,
       o.data_finalizacao,o.prazo,o.observacoes,o.descricao_solucao,f.filial
FROM ordens_servico o
JOIN prioridades_os p ON p.id=o.prioridade_id
JOIN status_os s ON s.id=o.status_id
LEFT JOIN usuarios u ON u.id=o.aberto_por
LEFT JOIN usuarios r ON r.id=o.responsavel_id
LEFT JOIN indicadores_matriz.filiais f ON f.id=o.filial_id
"""

# Horário civil de Brasília, compatível com as colunas DATETIME existentes.
BR_TZ = timezone(timedelta(hours=-3))
def db_now():
    return datetime.now(BR_TZ).replace(tzinfo=None, microsecond=0)
def stamp(value):
    if not value: return ""
    if isinstance(value, datetime) and value.tzinfo is None:
        value = value.replace(tzinfo=BR_TZ)
    return value.isoformat()
def text_value(value):
    return str(value) if value is not None else ""
def order_json(row, history):
    finished = row[13]
    final_notes = ""
    if row[6] == "Concluída":
        for event in reversed(history):
            if event["action"] == "Serviço concluído":
                final_notes = event.get("finalNotes", "")
                break
    return {"id":int(row[0]), "branchId":int(row[1]), "location":text_value(row[2]),
            "service":text_value(row[3]), "priorityId":int(row[4]), "priority":row[5],
            "status":row[6], "requesterId":int(row[7]), "requester":text_value(row[8]),
            "ownerId":int(row[9]) if row[9] else None, "owner":text_value(row[10]),
            "openedAt":stamp(row[11]), "startedAt":stamp(row[12]), "finishedAt":stamp(finished),
            "completed":finished.date().isoformat() if finished and row[6]=="Concluída" else "",
            "due":stamp(row[14]), "notes":text_value(row[15]), "solution":text_value(row[16]),
            "finalNotes":final_notes, "branchName":text_value(row[17]),
            "history":[{k:v for k,v in e.items() if k!="finalNotes"} for e in history]}

def histories(cursor, ids):
    result = {}
    if not ids: return result
    placeholders = ",".join(["%s"] * len(ids))
    cursor.execute("SELECT h.ordem_id,h.acao,h.descricao,h.data_registro,h.dados_novos,u.nome FROM historico_os h LEFT JOIN usuarios u ON u.id=h.usuario_id WHERE h.ordem_id IN ("+placeholders+") ORDER BY h.id", tuple(ids))
    labels = {"ABERTURA":"Ordem aberta","EDICAO":"Solicitação atualizada","PRIORIDADE":"Prioridade alterada","ATRIBUICAO":"Responsável atribuído","INICIO":"Serviço iniciado","CONCLUSAO":"Serviço concluído","REABERTURA":"Ordem reaberta"}
    for oid,action,detail,at,new,actor in cursor.fetchall():
        payload = json.loads(new) if isinstance(new,(str,bytes)) else (new or {})
        result.setdefault(oid, []).append({"action":labels.get(action,action),"at":stamp(at),
            "detail":text_value(detail),"actor":text_value(actor),"finalNotes":text_value(payload.get("finalNotes")) if isinstance(payload,dict) else ""})
    return result

def read_order(cursor, oid):
    cursor.execute(ORDER_SELECT+" WHERE o.id=%s",(oid,))
    row=cursor.fetchone()
    if row is None: raise RuntimeError("Ordem não encontrada após gravação")
    return order_json(row,histories(cursor,[oid]).get(oid,[]))

def validate_order_input(cursor,data,user):
    if not data.location.strip() or not data.service.strip():
        raise order_error(422,"Informe local e descrição.")
    if user["perfil"]!="ADMINISTRADOR" and str(data.branchId)!=user["filial_id"]:
        raise order_error(403,"Filial não autorizada.")
    cursor.execute("SELECT id FROM indicadores_matriz.filiais WHERE id=%s AND ativo='S'",(data.branchId,))
    if not cursor.fetchone(): raise order_error(422,"Filial inválida ou inativa.")
    cursor.execute("SELECT id FROM prioridades_os WHERE id=%s AND ativo=1",(data.priorityId,))
    if not cursor.fetchone(): raise order_error(422,"Prioridade inválida ou inativa.")

def status_id(cursor,label):
    cursor.execute("SELECT id FROM status_os WHERE descricao=%s AND ativo=1",(label,))
    row=cursor.fetchone()
    if not row: raise order_error(503,"Status não configurado.")
    return row[0]

def log_order(cursor,oid,user,action,detail,at,old=None,new=None):
    cursor.execute("INSERT INTO historico_os (ordem_id,usuario_id,acao,descricao,dados_anteriores,dados_novos,data_registro) VALUES (%s,%s,%s,%s,%s,%s,%s)",
        (oid,user["id"],action,detail,json.dumps(old,ensure_ascii=False,default=str) if old is not None else None,
         json.dumps(new,ensure_ascii=False,default=str) if new is not None else None,at))

def transaction(fn):
    conn=None
    try:
        conn=get_connection()
        with conn.cursor() as cursor:
            result=fn(cursor)
        conn.commit()
        return result
    except HTTPException:
        if conn: conn.rollback()
        raise
    except Exception as exc:
        if conn: conn.rollback()
        log.warning("Gravação OS indisponível: %s",type(exc).__name__)
        raise order_error(503,"Não foi possível confirmar a gravação. Consulte as ordens antes de tentar novamente.") from None
    finally:
        if conn: conn.close()

# Administração de usuários: somente administradores autenticados.
class AdminUserInput(BaseModel):
    model_config = {"extra": "forbid"}
    nome: str = Field(min_length=1,max_length=120)
    login: str = Field(min_length=1,max_length=80)
    gerar_senha_temporaria: bool = False
    perfil: str
    filial_id: int | None = Field(default=None,gt=0)
    ativo: bool = True

def admin_user(user=Depends(current_user)):
    if user["perfil"]!="ADMINISTRADOR":
        raise order_error(403,"Acesso exclusivo do administrador.")
    return user

ADMIN_USER_SELECT = """SELECT u.id,u.nome,u.login,u.perfil,u.filial_id,u.ativo,f.filial
FROM usuarios u LEFT JOIN indicadores_matriz.filiais f ON f.id=u.filial_id"""

def admin_user_json(row):
    return {"id":int(row[0]),"nome":row[1],"login":row[2],"perfil":row[3],
            "filial_id":int(row[4]) if row[4] is not None else None,
            "ativo":bool(row[5]),"filial":row[6] or ""}

@app.get("/api/admin/usuarios")
def admin_list_users(user=Depends(admin_user)):
    def read(cursor):
        cursor.execute(ADMIN_USER_SELECT+" ORDER BY u.nome,u.id")
        return {"usuarios":[admin_user_json(row) for row in cursor.fetchall()]}
    return JSONResponse(transaction(read),headers=HEADERS)

def admin_save_user(data,user,uid=None):
    nome,login=data.nome.strip(),data.login.strip()
    if not nome or not login or data.perfil not in ROLES:
        raise order_error(422,"Informe nome, login e perfil válido.")
    if data.perfil!="ADMINISTRADOR" and data.filial_id is None:
        raise order_error(422,"Informe a filial do usuário.")
    if uid==user["id"] and (not data.ativo or data.perfil!="ADMINISTRADOR"):
        raise order_error(409,"Não é possível desativar ou remover seu próprio perfil administrativo.")
    # O administrador não informa a senha; a API gera e devolve uma única vez.
    alphabet="ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
    temporary="".join(secrets.choice(alphabet) for _ in range(10)) if uid is None or data.gerar_senha_temporaria else None
    hashed=hash_password(temporary) if temporary is not None else None
    expires=db_now()+timedelta(days=1) if hashed else None
    def write(cursor):
        target=uid
        if uid is not None:
            cursor.execute("SELECT id FROM usuarios WHERE id=%s FOR UPDATE",(uid,))
            if not cursor.fetchone(): raise order_error(404,"Usuário não encontrado.")
        if data.filial_id is not None:
            cursor.execute("SELECT id FROM indicadores_matriz.filiais WHERE id=%s AND ativo='S'",(data.filial_id,))
            if not cursor.fetchone(): raise order_error(422,"Filial inválida ou inativa.")
        cursor.execute("SELECT id FROM usuarios WHERE login=%s AND (%s IS NULL OR id<>%s) LIMIT 1",(login,uid,uid))
        if cursor.fetchone(): raise order_error(409,"Login já cadastrado.")
        try:
            if uid is None:
                cursor.execute("INSERT INTO usuarios (nome,login,senha_hash,perfil,filial_id,ativo,senha_temporaria_expira_em,senha_temporaria_usada_em) VALUES (%s,%s,%s,%s,%s,%s,%s,NULL)",
                    (nome,login,hashed,data.perfil,data.filial_id,int(data.ativo),expires))
                target=cursor.lastrowid
            else:
                sql="UPDATE usuarios SET nome=%s,login=%s,perfil=%s,filial_id=%s,ativo=%s"
                args=(nome,login,data.perfil,data.filial_id,int(data.ativo))
                if hashed:
                    sql+=",senha_hash=%s,senha_temporaria_expira_em=%s,senha_temporaria_usada_em=NULL";args+=(hashed,expires)
                cursor.execute(sql+" WHERE id=%s",(*args,uid))
        except Exception as exc:
            if getattr(exc,"args",()) and exc.args[0]==1062:
                raise order_error(409,"Login já cadastrado.") from None
            raise
        cursor.execute(ADMIN_USER_SELECT+" WHERE u.id=%s",(target,))
        return {"usuario":admin_user_json(cursor.fetchone())}
    result=transaction(write)
    if temporary is not None:
        result["senha_temporaria"]=temporary
    return JSONResponse(result,status_code=201 if uid is None else 200,headers=HEADERS)

@app.post("/api/admin/usuarios")
def admin_create_user(data:AdminUserInput,user=Depends(admin_user)):
    return admin_save_user(data,user)

@app.post("/api/admin/usuarios/{uid}")
def admin_edit_user(uid:int,data:AdminUserInput,user=Depends(admin_user)):
    return admin_save_user(data,user,uid)

@app.get("/api/ordens")
def list_orders(user=Depends(current_user)):
    conn=None
    try:
        conn=get_connection()
        with conn.cursor() as cursor:
            where,args=order_scope(user)
            cursor.execute(ORDER_SELECT+" WHERE "+where+" ORDER BY o.id",args)
            rows=cursor.fetchall()
            history=histories(cursor,[row[0] for row in rows])
            return JSONResponse({"ordens":[order_json(row,history.get(row[0],[])) for row in rows]},headers=HEADERS)
    except Exception as exc:
        log.warning("Consulta OS indisponível: %s",type(exc).__name__)
        raise order_error(503,"Não foi possível consultar as ordens.") from None
    finally:
        if conn: conn.close()

@app.post("/api/ordens")
def create_order(data:OrderInput,background:BackgroundTasks,user=Depends(current_user)):
    if user["perfil"]!="ADMINISTRADOR" and str(data.branchId)!=user["filial_id"]:
        raise order_error(403,"Filial não autorizada.")
    def write(cursor):
        validate_order_input(cursor,data,user)
        pending=status_id(cursor,"Pendente")
        at=db_now()
        cursor.execute("INSERT INTO ordens_servico (filial_id,local,descricao,prioridade_id,status_id,aberto_por,data_abertura,observacoes) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            (str(data.branchId),data.location.strip(),data.service.strip(),data.priorityId,pending,user["id"],at,data.notes.strip()))
        oid=cursor.lastrowid
        log_order(cursor,oid,user,"ABERTURA","Ordem aberta",at,new=data.model_dump())
        return read_order(cursor,oid)
    order=transaction(write)
    schedule_push(background,order,"created")
    return JSONResponse({"ordem":order},status_code=201,headers=HEADERS,background=background)

def lock_order(cursor,oid,user):
    where,args=order_scope(user)
    cursor.execute("SELECT o.aberto_por,o.responsavel_id,o.filial_id,s.descricao,o.local,o.descricao,o.prioridade_id,o.observacoes,o.prazo,o.descricao_solucao,o.data_inicio,o.data_finalizacao FROM ordens_servico o JOIN status_os s ON s.id=o.status_id WHERE o.id=%s AND "+where+" FOR UPDATE",(oid,*args))
    row=cursor.fetchone()
    if row is None: raise order_error(404,"Ordem não encontrada.")
    return row

@app.get("/api/ordens/{oid}/imagens/permissao")
def image_permission(oid:int,fase:str,operacao:str,user=Depends(current_user)):
    if oid<1 or fase not in ("abertura","conclusao") or operacao not in ("leitura","envio"):
        raise order_error(422,"Solicitação de imagem inválida.")
    def check(cursor):
        row=lock_order(cursor,oid,user)
        if operacao=="envio":
            admin=user["perfil"]=="ADMINISTRADOR"
            if fase=="abertura":
                allowed=row[3]=="Pendente" and (admin or row[0]==user["id"])
            else:
                allowed=row[3]=="Em andamento" and (admin or (user["perfil"]=="MANUTENCAO" and row[1]==user["id"]))
            if not allowed:
                raise order_error(403,"Envio de imagens não autorizado nesta etapa da OS.")
        return {"permitido":True,"ordem_id":oid,"fase":fase}
    return JSONResponse(transaction(check),headers=HEADERS)

@app.post("/api/ordens/{oid}/editar")
def edit_order(oid:int,data:OrderInput,background:BackgroundTasks,user=Depends(current_user)):
    priority_changed=False
    def write(cursor):
        nonlocal priority_changed
        row=lock_order(cursor,oid,user)
        if row[3]!="Pendente": raise order_error(409,"Somente OS pendentes podem ser editadas.")
        if user["perfil"]!="ADMINISTRADOR" and row[0]!=user["id"]: raise order_error(403,"Somente o solicitante ou administrador pode editar.")
        if user["perfil"]=="MANUTENCAO" and data.priorityId!=row[6]: raise order_error(403,"Alteração de prioridade reservada ao solicitante e administrador.")
        if row[1] is not None and str(data.branchId)!=str(row[2]): raise order_error(409,"Não é possível mudar a filial de uma OS atribuída.")
        validate_order_input(cursor,data,user)
        priority_changed = row[6] != data.priorityId
        cursor.execute("UPDATE ordens_servico SET filial_id=%s,local=%s,descricao=%s,prioridade_id=%s,observacoes=%s WHERE id=%s",
            (str(data.branchId),data.location.strip(),data.service.strip(),data.priorityId,data.notes.strip(),oid))
        log_order(cursor,oid,user,"EDICAO","Solicitação atualizada",db_now(),old={"branchId":row[2],"location":row[4],"service":row[5],"priorityId":row[6],"notes":row[7]},new=data.model_dump())
        return read_order(cursor,oid)
    order=transaction(write)
    if priority_changed: schedule_push(background,order,"priority")
    return JSONResponse({"ordem":order},headers=HEADERS,background=background)

@app.get("/api/ordens/{oid}/executores")
def order_executors(oid:int,user=Depends(current_user)):
    if user["perfil"] not in ("ADMINISTRADOR","MANUTENCAO"): raise order_error(403,"Atribuição reservada à manutenção.")
    def read(cursor):
        row=lock_order(cursor,oid,user)
        if user["perfil"]!="ADMINISTRADOR" and str(row[2])!=user["filial_id"]: raise order_error(403,"Filial não autorizada.")
        cursor.execute("SELECT id,nome FROM usuarios WHERE ativo=1 AND perfil='MANUTENCAO' AND filial_id=%s ORDER BY nome,id",(str(row[2]),))
        return [{"id":int(i),"name":n} for i,n in cursor.fetchall()]
    return JSONResponse({"executores":transaction(read)},headers=HEADERS)

@app.post("/api/ordens/{oid}/acao")
def order_action(oid:int,data:ActionInput,background:BackgroundTasks,user=Depends(current_user)):
    if data.action=="priority":
        if user["perfil"] not in ("SOLICITANTE","ADMINISTRADOR"):
            raise order_error(403,"Alteração de prioridade reservada ao solicitante e administrador.")
    elif user["perfil"] not in ("ADMINISTRADOR","MANUTENCAO"):
        raise order_error(403,"Ação reservada à manutenção.")
    changed=True
    def write(cursor):
        nonlocal changed
        row=lock_order(cursor,oid,user)
        at=db_now(); action=data.action; detail=data.detail.strip(); new=None
        if action=="priority":
            if user["perfil"]=="SOLICITANTE" and row[0]!=user["id"]:
                raise order_error(403,"Somente o autor ou administrador pode alterar a prioridade.")
            if row[3] not in ("Pendente","Em andamento"): raise order_error(409,"OS concluída não pode ter prioridade alterada.")
            if data.priorityId is None: raise order_error(422,"Selecione a prioridade.")
            cursor.execute("SELECT id,descricao FROM prioridades_os WHERE id=%s AND ativo=1",(data.priorityId,))
            priority=cursor.fetchone()
            if not priority: raise order_error(422,"Prioridade inválida ou inativa.")
            if row[6]==data.priorityId:
                changed=False
                return read_order(cursor,oid)
            cursor.execute("UPDATE ordens_servico SET prioridade_id=%s WHERE id=%s",(data.priorityId,oid))
            log_order(cursor,oid,user,"PRIORIDADE","Nova prioridade: "+priority[1],at,old={"priorityId":row[6]},new={"priorityId":data.priorityId,"priority":priority[1]})
            return read_order(cursor,oid)
        elif action=="start":
            if user["perfil"]!="ADMINISTRADOR" and str(row[2])!=user["filial_id"]: raise order_error(403,"Filial não autorizada.")
            if row[3]!="Pendente": raise order_error(409,"Somente OS pendentes podem ser iniciadas.")
            if data.ownerId is None: raise order_error(422,"Selecione o responsável pelo serviço.")
            due=None
            if data.due:
                try: due=datetime.strptime(data.due,"%Y-%m-%d").date()
                except ValueError: raise order_error(422,"Prazo inválido.")
            cursor.execute("SELECT nome FROM usuarios WHERE id=%s AND ativo=1 AND perfil='MANUTENCAO' AND filial_id=%s",(data.ownerId,str(row[2])))
            executor=cursor.fetchone()
            if not executor: raise order_error(422,"Responsável inválido ou inativo.")
            running=status_id(cursor,"Em andamento")
            cursor.execute("UPDATE ordens_servico SET responsavel_id=%s,prazo=%s,status_id=%s,iniciado_por=%s,data_inicio=%s WHERE id=%s",
                (data.ownerId,due,running,user["id"],at,oid))
            event="INICIO"; detail="Responsável pelo serviço: "+executor[0]
            new={"ownerId":data.ownerId,"due":data.due,"status":"Em andamento","startedAt":stamp(at)}
        elif action=="finish":
            if row[3]!="Em andamento": raise order_error(409,"OS não está em andamento.")
            if user["perfil"]!="ADMINISTRADOR" and row[1]!=user["id"]: raise order_error(403,"Somente o executor pode concluir.")
            if not detail: raise order_error(422,"Informe a solução aplicada.")
            cursor.execute("UPDATE ordens_servico SET status_id=%s,finalizado_por=%s,data_finalizacao=%s,descricao_solucao=%s WHERE id=%s",(status_id(cursor,"Concluída"),user["id"],at,detail,oid))
            event="CONCLUSAO"; new={"solution":detail,"finalNotes":data.notes.strip()}
        elif action=="reopen":
            if row[3]!="Concluída" or not detail: raise order_error(409,"Informe justificativa para reabrir uma OS concluída.")
            if user["perfil"]!="ADMINISTRADOR" and str(row[2])!=user["filial_id"]: raise order_error(403,"Filial não autorizada.")
            cursor.execute("UPDATE ordens_servico SET status_id=%s,iniciado_por=NULL,finalizado_por=NULL,data_inicio=NULL,data_finalizacao=NULL,descricao_solucao=NULL WHERE id=%s",(status_id(cursor,"Pendente"),oid))
            event="REABERTURA"
        else: raise order_error(422,"Ação desconhecida.")
        log_order(cursor,oid,user,event,detail,at,old={"status":row[3],"ownerId":row[1],"due":row[8],"solution":row[9],"startedAt":row[10],"finishedAt":row[11]},new=new)
        return read_order(cursor,oid)
    order=transaction(write)
    if changed:
        schedule_push(background,order,data.action)
    return JSONResponse({"ordem":order},headers=HEADERS,background=background)


# Web Push nativo. O cadastro pertence ao usuário autenticado, não à filial
# enviada pelo navegador. O destino é reavaliado a cada evento confirmado.
PUSH_RECIPIENTS_SQL = """
SELECT d.endpoint_hash,d.endpoint,d.p256dh,d.auth
FROM notificacoes_dispositivos d
JOIN usuarios u ON u.id=d.usuario_id
WHERE u.ativo=1 AND (u.perfil='ADMINISTRADOR'
 OR (u.perfil IN ('SOLICITANTE','MANUTENCAO') AND u.filial_id=%s))
"""
PUSH_EVENTS={"created":"Nova ordem de serviço","start":"Serviço iniciado","finish":"Serviço concluído","priority":"Prioridade alterada","reopen":"OS reaberta"}

def valid_push_endpoint(endpoint):
    try:
        url=urlsplit(endpoint)
        host=url.hostname or ""
        allowed=(host in ("fcm.googleapis.com","updates.push.services.mozilla.com","push.services.mozilla.com","android.googleapis.com","web.push.apple.com")
                 or host.endswith(".push.apple.com") or host.endswith(".notify.windows.com") or host.endswith(".wns.windows.com"))
        return (allowed and url.scheme=="https" and url.port in (None,443)
                and not url.username and not url.password and not url.fragment
                and bool(url.path) and url.path!="/" and not any(c.isspace() or ord(c)<32 for c in endpoint))
    except (ValueError,TypeError):
        return False

class PushEndpoint(BaseModel):
    endpoint: str = Field(min_length=1,max_length=2048)

class PushKeys(BaseModel):
    p256dh: str = Field(min_length=80,max_length=100)
    auth: str = Field(min_length=20,max_length=30)

class PushInput(PushEndpoint):
    keys: PushKeys

def push_key_bytes(value):
    return base64.b64decode(value+"="*(-len(value)%4),altchars=b"-_",validate=True)

def push_config():
    from py_vapid import Vapid
    from cryptography.hazmat.primitives.serialization import Encoding,PublicFormat
    private=os.getenv("VAPID_PRIVATE_KEY","").strip()
    subject="https://manutencao-predial.inventario-pg.workers.dev"
    if not private:
        raise order_error(503,"Notificações ainda não configuradas.")
    try:
        key=Vapid.from_string(private)
        public=b64(key.public_key.public_bytes(Encoding.X962,PublicFormat.UncompressedPoint))
    except Exception:
        raise order_error(503,"Configuração de notificações inválida.") from None
    return key,public,subject

@app.get("/api/notificacoes/chave")
def notification_key(user=Depends(current_user)):
    _,public,_=push_config()
    return JSONResponse({"publicKey":public},headers=HEADERS)

@app.post("/api/notificacoes/inscrever")
def notification_subscribe(data:PushInput,user=Depends(current_user)):
    push_config()
    if user["perfil"]!="ADMINISTRADOR" and not user["filial_id"]:
        raise order_error(403,"Usuário sem filial vinculada.")
    try:
        from cryptography.hazmat.primitives.asymmetric import ec
        if not valid_push_endpoint(data.endpoint) or len(push_key_bytes(data.keys.auth))!=16:
            raise ValueError()
        ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(),push_key_bytes(data.keys.p256dh))
    except Exception:
        raise order_error(422,"Inscrição de notificações inválida.") from None
    digest=hashlib.sha256(data.endpoint.encode()).digest()
    def write(cursor):
        cursor.execute("SELECT usuario_id FROM notificacoes_dispositivos WHERE endpoint_hash=%s FOR UPDATE",(digest,))
        existing=cursor.fetchone()
        if existing and existing[0]!=user["id"]:
            raise order_error(409,"Dispositivo vinculado a outra conta. Desative e ative novamente.")
        if existing:
            cursor.execute("UPDATE notificacoes_dispositivos SET p256dh=%s,auth=%s WHERE endpoint_hash=%s AND usuario_id=%s",
                (data.keys.p256dh,data.keys.auth,digest,user["id"]))
        else:
            cursor.execute("INSERT INTO notificacoes_dispositivos (endpoint_hash,usuario_id,endpoint,p256dh,auth) VALUES (%s,%s,%s,%s,%s)",
                (digest,user["id"],data.endpoint,data.keys.p256dh,data.keys.auth))
        return {"enabled":True}
    return JSONResponse(transaction(write),headers=HEADERS)

@app.post("/api/notificacoes/situacao")
def notification_status(data:PushEndpoint,user=Depends(current_user)):
    digest=hashlib.sha256(data.endpoint.encode()).digest()
    def read(cursor):
        cursor.execute("SELECT 1 FROM notificacoes_dispositivos WHERE endpoint_hash=%s AND usuario_id=%s",(digest,user["id"]))
        return {"enabled":bool(cursor.fetchone())}
    return JSONResponse(transaction(read),headers=HEADERS)

@app.post("/api/notificacoes/desativar")
def notification_unsubscribe(data:PushEndpoint,user=Depends(current_user)):
    digest=hashlib.sha256(data.endpoint.encode()).digest()
    def write(cursor):
        cursor.execute("DELETE FROM notificacoes_dispositivos WHERE endpoint_hash=%s AND usuario_id=%s",(digest,user["id"]))
        return {"enabled":False}
    return JSONResponse(transaction(write),headers=HEADERS)

def schedule_push(background,order,event):
    if event in PUSH_EVENTS and os.getenv("VAPID_PRIVATE_KEY"):
        background.add_task(send_order_push,order,event)

def deliver_push(row,key,subject,payload):
    from pywebpush import webpush
    import requests
    digest,endpoint,p256dh,auth=row
    if not valid_push_endpoint(endpoint): return None
    class SafeSession(requests.Session):
        def request(self,*args,**kwargs):
            kwargs["allow_redirects"]=False
            return super().request(*args,**kwargs)
    try:
        with SafeSession() as session:
            webpush(subscription_info={"endpoint":endpoint,"keys":{"p256dh":p256dh,"auth":auth}},
                data=payload,vapid_private_key=key,vapid_claims={"sub":subject},
                ttl=300,timeout=4,requests_session=session)
    except Exception as exc:
        response=getattr(exc,"response",None)
        status=getattr(response,"status_code",None)
        if status in (404,410): return digest
        log.warning("Web Push não entregue: %s / %s",type(exc).__name__,status)
    return None

def send_order_push(order,event):
    # Best effort pós-commit: nenhuma falha de push desfaz a OS.
    conn=None
    try:
        key,_,subject=push_config()
        conn=get_connection()
        with conn.cursor() as cursor:
            cursor.execute(PUSH_RECIPIENTS_SQL,(str(order["branchId"]),))
            rows=cursor.fetchall()
        conn.close(); conn=None
        # Sem descrição, nomes ou fotos na tela bloqueada.
        payload=json.dumps({"title":PUSH_EVENTS[event],"orderId":order["id"],
            "body":"OS-"+str(order["id"]).zfill(6)+" • Abra o aplicativo para consultar."},ensure_ascii=False)
        def send(row):
            return deliver_push(row,key,subject,payload)
        with ThreadPoolExecutor(max_workers=8) as pool:
            expired=[digest for digest in pool.map(send,rows) if digest is not None]
        if expired:
            conn=get_connection()
            with conn.cursor() as cursor:
                cursor.executemany("DELETE FROM notificacoes_dispositivos WHERE endpoint_hash=%s",[(d,) for d in expired])
            conn.commit()
    except Exception as exc:
        log.warning("Notificação OS indisponível: %s",type(exc).__name__)
    finally:
        if conn: conn.close()
