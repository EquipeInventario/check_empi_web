from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime, date
from decimal import Decimal
import json
import os
import traceback

import pymysql


# ============================================================
# API SQL - CHECK MÁQUINAS
# Rota sugerida na Vercel: /api/api_sql
# Arquivo sugerido: api/api_sql/index.py
# ============================================================

DB_SCHEMA = os.environ.get("MYSQL_DATABASE", "check_maquinas")


TABLES = {
    "maquinas": {
        "schema": "check_maquinas",
        "table": "maquinas",
        "pk": "id",
        "columns": [
            "id",
            "id_maquina",
            "codigo",
            "descricao",
            "setor",
            "id_categoria",
            "tipo_maquina",
            "id_tipo_emp",
            "energia",
            "capacidade_toneladas",
            "tipo_garfo",
            "adaptada_bobina",
            "id_filial",
            "horimetro_atual",
            "ultimo_reg_horimetro",
            "horimetro_manutencao",
            "ultima_manutencao",
            "intervalo_preventiva_horas",
            "prox_manutencao_hora",
            "ativo",
            "possui_gdi",
            "id_perfil_emp",
            "tipo_torre",
            "carga_atual",
        ],
        "bool_columns": ["adaptada_bobina", "possui_gdi"],
        "json_columns": [],
    },
    "usuarios_web_check": {
        "schema": "check_maquinas",
        "table": "usuarios_web_check",
        "pk": "id",
        "columns": [
            "id",
            "nome",
            "usuario",
            "senha",
            "perfil",
            "ativo",
            "criado_em",
            "id_filial",
            "filial",
            "cidade",
            "estado",
        ],
        "bool_columns": ["ativo"],
        "json_columns": [],
    },
    "check_empi": {
        "schema": "check_maquinas",
        "table": "check_empi",
        "pk": "id",
        "columns": [
            "id",
            "empilhadeira",
            "operador",
            "turno",
            "data_abertura",
            "data_finalizacao",
            "horimetro_inicial",
            "horimetro_final",
            "status_check",
            "resultado_check",
            "observacao_geral",
            "seg_cinto",
            "seg_cinto_obs",
            "seg_buzina",
            "seg_buzina_obs",
            "seg_alarme_re",
            "seg_alarme_re_obs",
            "seg_giroflex",
            "seg_giroflex_obs",
            "seg_luzes",
            "seg_luzes_obs",
            "seg_extintor",
            "seg_extintor_obs",
            "seg_espelhos",
            "seg_espelhos_obs",
            "seg_freio_estacionamento",
            "seg_freio_estacionamento_obs",
            "mec_vazamento_oleo",
            "mec_vazamento_oleo_obs",
            "mec_vazamento_hidraulico",
            "mec_vazamento_hidraulico_obs",
            "mec_pneus",
            "mec_pneus_obs",
            "mec_garfos",
            "mec_garfos_obs",
            "mec_correntes",
            "mec_correntes_obs",
            "mec_torre",
            "mec_torre_obs",
            "mec_oleo_hidraulico",
            "mec_oleo_hidraulico_obs",
            "mec_bateria_glp",
            "mec_bateria_glp_obs",
            "ope_direcao",
            "ope_direcao_obs",
            "ope_freio_servico",
            "ope_freio_servico_obs",
            "ope_elevacao_garfos",
            "ope_elevacao_garfos_obs",
            "ope_inclinacao_torre",
            "ope_inclinacao_torre_obs",
            "ope_frente",
            "ope_frente_obs",
            "ope_re",
            "ope_re_obs",
            "ope_painel",
            "ope_painel_obs",
            "ope_horimetro",
            "ope_horimetro_obs",
            "criado_em",
            "atualizado_em",
            "mec_estrutura_lataria",
            "mec_estrutura_lataria_obs",
            "mec_oleo_transmissao",
            "mec_oleo_transmissao_obs",
            "mec_sistema_arrefecimento",
            "mec_sistema_arrefecimento_obs",
            "mec_filtro_ar",
            "mec_filtro_ar_obs",
            "id_filial",
            "carga_atual",
            "ultima_carga_realizada",
        ],
        "bool_columns": [],
        "json_columns": [],
    },
    "check_empi_pendencias": {
        "schema": "check_maquinas",
        "table": "check_empi_pendencias",
        "pk": "id",
        "columns": [
            "id",
            "id_check",
            "empilhadeira",
            "categoria",
            "item",
            "observacao",
            "status_pendencia",
            "resolvido",
            "resolvido_por",
            "resolvido_em",
            "criado_em",
            "caminho_arquivo",
            "url_publica",
            "anexos",
            "obs_resolucao",
            "id_filial",
        ],
        "bool_columns": ["resolvido"],
        "json_columns": ["anexos"],
    },
    "check_empi_anexos": {
        "schema": "check_maquinas",
        "table": "check_empi_anexos",
        "pk": "id",
        "columns": [
            "id",
            "id_check",
            "empilhadeira",
            "categoria",
            "item",
            "caminho_arquivo",
            "url_publica",
            "tamanho_bytes",
            "criado_por",
            "criado_em",
            "storage_origem",
            "container_azure",
            "blob_azure",
            "url_azure",
            "migrado_azure",
            "migrado_em",
        ],
        "bool_columns": ["migrado_azure"],
        "json_columns": [],
    },
}

ANEXOS_SELECT = [
    "id",
    "id_check",
    "empilhadeira",
    "categoria",
    "item",
    "caminho_arquivo",
    "url_publica",
    "tamanho_bytes",
    "criado_por",
    "criado_em",
]


# ============================================================
# RESPOSTA / CORS / JSON
# ============================================================

def set_cors_headers(h):
    h.send_header("Access-Control-Allow-Origin", "*")
    h.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
    h.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-API-Token, x-checkempi-token")


def serializar(valor):
    if isinstance(valor, Decimal):
        return float(valor)
    if isinstance(valor, (datetime, date)):
        return valor.isoformat()
    if isinstance(valor, bytes):
        return valor.decode("utf-8", errors="ignore")
    if isinstance(valor, list):
        return [serializar(v) for v in valor]
    if isinstance(valor, dict):
        return {k: serializar(v) for k, v in valor.items()}
    return valor


def responder(h, status_code, payload):
    body = json.dumps(serializar(payload), ensure_ascii=False).encode("utf-8")
    h.send_response(status_code)
    h.send_header("Content-Type", "application/json; charset=utf-8")
    set_cors_headers(h)
    h.end_headers()
    h.wfile.write(body)


def ler_json_body(h):
    tamanho = int(h.headers.get("Content-Length", 0) or 0)
    if tamanho <= 0:
        return {}

    raw = h.rfile.read(tamanho).decode("utf-8")
    if not raw.strip():
        return {}

    return json.loads(raw)


def query_param(query, nome, default=""):
    valor = query.get(nome)
    if not valor:
        return default
    return valor[0]


def query_lista(query, nome):
    valores = query.get(nome)
    if not valores:
        return []
    if len(valores) == 1 and "," in valores[0]:
        return [v.strip() for v in valores[0].split(",") if v.strip()]
    return valores


# ============================================================
# SEGURANÇA
# ============================================================

def validar_token(h):
    token_esperado = (
        os.environ.get("CHECK_API_TOKEN")
        or os.environ.get("CHECKEMPI_API_TOKEN")
        or os.environ.get("API_TOKEN")
        or ""
    ).strip()

    # Durante testes, se não tiver token configurado, libera.
    # Em produção, configure CHECK_API_TOKEN no Vercel.
    if not token_esperado:
        return True

    authorization = h.headers.get("Authorization", "")
    x_api_token = h.headers.get("X-API-Token", "")
    x_checkempi_token = h.headers.get("x-checkempi-token", "")

    token_recebido = ""

    if authorization.startswith("Bearer "):
        token_recebido = authorization.replace("Bearer ", "", 1).strip()
    elif x_api_token:
        token_recebido = x_api_token.strip()
    elif x_checkempi_token:
        token_recebido = x_checkempi_token.strip()

    return token_recebido == token_esperado


# ============================================================
# MYSQL
# ============================================================

def conectar():
    host = os.environ.get("MYSQL_HOST")
    port = int(os.environ.get("MYSQL_PORT", "3306"))
    user = os.environ.get("MYSQL_USER")
    password = os.environ.get("MYSQL_PASSWORD")
    database = os.environ.get("MYSQL_DATABASE", "check_maquinas")

    faltando = []
    if not host:
        faltando.append("MYSQL_HOST")
    if not user:
        faltando.append("MYSQL_USER")
    if not password:
        faltando.append("MYSQL_PASSWORD")
    if not database:
        faltando.append("MYSQL_DATABASE")

    if faltando:
        raise RuntimeError("Variáveis MySQL ausentes: " + ", ".join(faltando))

    return pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=10,
        read_timeout=30,
        write_timeout=30,
        autocommit=False,
    )


def agora_mysql():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def possui_filial(id_filial):
    return str(id_filial or "").strip() != ""


def cfg_tabela(nome):
    cfg = TABLES.get(nome)
    if not cfg:
        raise ValueError(f"Tabela não permitida: {nome}")
    return cfg


def tabela_sql(nome):
    cfg = cfg_tabela(nome)
    return f"`{cfg['schema']}`.`{cfg['table']}`"


def coluna_sql(nome_tabela, coluna):
    cfg = cfg_tabela(nome_tabela)
    if coluna not in cfg["columns"]:
        raise ValueError(f"Coluna não permitida em {nome_tabela}: {coluna}")
    return f"`{coluna}`"


def normalizar_valor_para_banco(nome_tabela, coluna, valor):
    cfg = cfg_tabela(nome_tabela)

    if coluna in cfg.get("bool_columns", []):
        if isinstance(valor, bool):
            return 1 if valor else 0
        if valor is None:
            return None
        texto = str(valor).strip().lower()
        if texto in ["true", "1", "s", "sim", "yes"]:
            return 1
        if texto in ["false", "0", "n", "nao", "não", "no"]:
            return 0
        return valor

    if coluna in cfg.get("json_columns", []):
        if valor is None:
            return None
        if isinstance(valor, str):
            return valor
        return json.dumps(valor, ensure_ascii=False)

    return valor


def normalizar_linha_saida(nome_tabela, linha):
    if not linha:
        return linha

    cfg = cfg_tabela(nome_tabela)
    bool_columns = set(cfg.get("bool_columns", []))
    json_columns = set(cfg.get("json_columns", []))

    saida = dict(linha)

    for coluna in bool_columns:
        if coluna in saida and saida[coluna] is not None:
            saida[coluna] = bool(saida[coluna])

    for coluna in json_columns:
        if coluna in saida and isinstance(saida[coluna], str):
            try:
                saida[coluna] = json.loads(saida[coluna])
            except Exception:
                pass

    return saida


def filtrar_dados(nome_tabela, dados, permitir_id=False):
    cfg = cfg_tabela(nome_tabela)
    colunas = set(cfg["columns"])
    pk = cfg["pk"]
    filtrado = {}

    for chave, valor in (dados or {}).items():
        if chave not in colunas:
            continue
        if not permitir_id and chave == pk:
            continue
        filtrado[chave] = normalizar_valor_para_banco(nome_tabela, chave, valor)

    return filtrado


def montar_where(nome_tabela, filtros):
    partes = []
    params = []

    for coluna, valor in (filtros or {}).items():
        if valor is None or valor == "":
            continue

        col = coluna_sql(nome_tabela, coluna)

        if isinstance(valor, list):
            if not valor:
                partes.append("1 = 0")
                continue
            placeholders = ", ".join(["%s"] * len(valor))
            partes.append(f"{col} IN ({placeholders})")
            params.extend(valor)
        else:
            partes.append(f"{col} = %s")
            params.append(valor)

    if not partes:
        return "", []

    return " WHERE " + " AND ".join(partes), params


def selecionar(nome_tabela, filtros=None, order_by=None, ascending=True, limit=None, colunas=None):
    cfg = cfg_tabela(nome_tabela)
    tabela = tabela_sql(nome_tabela)

    if colunas:
        select_cols = []
        for c in colunas:
            if c not in cfg["columns"]:
                raise ValueError(f"Coluna não permitida no select: {c}")
            select_cols.append(f"`{c}`")
        select_sql = ", ".join(select_cols)
    else:
        select_sql = "*"

    where_sql, params = montar_where(nome_tabela, filtros or {})
    sql = f"SELECT {select_sql} FROM {tabela}{where_sql}"

    if order_by:
        sql += f" ORDER BY {coluna_sql(nome_tabela, order_by)} {'ASC' if ascending else 'DESC'}"

    if limit:
        try:
            limit_int = int(limit)
        except Exception:
            limit_int = 100
        limit_int = max(1, min(limit_int, 2000))
        sql += f" LIMIT {limit_int}"

    with conectar() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

    return [normalizar_linha_saida(nome_tabela, r) for r in rows]


def selecionar_um(nome_tabela, filtros=None, order_by=None, ascending=True):
    rows = selecionar(nome_tabela, filtros=filtros, order_by=order_by, ascending=ascending, limit=1)
    return rows[0] if rows else None


def inserir(nome_tabela, dados, conn=None):
    dados = dict(dados or {})

    # Defaults leves para manter comportamento parecido com Supabase/app.
    if nome_tabela == "check_empi":
        dados.setdefault("data_abertura", agora_mysql())
        dados.setdefault("criado_em", agora_mysql())
    elif nome_tabela in ["check_empi_pendencias", "check_empi_anexos", "usuarios_web_check"]:
        dados.setdefault("criado_em", agora_mysql())

    dados_filtrados = filtrar_dados(nome_tabela, dados)
    if not dados_filtrados:
        raise ValueError("Nenhum campo válido enviado para insert.")

    tabela = tabela_sql(nome_tabela)
    colunas = list(dados_filtrados.keys())
    valores = [dados_filtrados[c] for c in colunas]
    colunas_sql = ", ".join([f"`{c}`" for c in colunas])
    placeholders = ", ".join(["%s"] * len(colunas))
    sql = f"INSERT INTO {tabela} ({colunas_sql}) VALUES ({placeholders})"

    close_conn = False
    if conn is None:
        conn = conectar()
        close_conn = True

    try:
        with conn.cursor() as cur:
            cur.execute(sql, valores)
            novo_id = cur.lastrowid

        if close_conn:
            conn.commit()
            return selecionar_um(nome_tabela, {"id": novo_id}) if novo_id else {"id": novo_id}

        registro = dict(dados_filtrados)
        if novo_id:
            registro["id"] = novo_id
        return normalizar_linha_saida(nome_tabela, registro)
    except Exception:
        if close_conn:
            conn.rollback()
        raise
    finally:
        if close_conn:
            conn.close()


def inserir_varios(nome_tabela, lista_dados, conn=None):
    if not isinstance(lista_dados, list):
        raise ValueError("Para inserir vários registros, envie uma lista em 'dados'.")

    resultados = []
    close_conn = False
    if conn is None:
        conn = conectar()
        close_conn = True

    try:
        for dados in lista_dados:
            resultados.append(inserir(nome_tabela, dados, conn=conn))

        if close_conn:
            conn.commit()

        return resultados
    except Exception:
        if close_conn:
            conn.rollback()
        raise
    finally:
        if close_conn:
            conn.close()


def atualizar(nome_tabela, dados, filtros, conn=None):
    dados_filtrados = filtrar_dados(nome_tabela, dados)
    if not dados_filtrados:
        raise ValueError("Nenhum campo válido enviado para update.")

    where_sql, where_params = montar_where(nome_tabela, filtros or {})
    if not where_sql:
        raise ValueError("Update bloqueado: informe pelo menos um filtro.")

    tabela = tabela_sql(nome_tabela)
    set_sql = ", ".join([f"`{c}` = %s" for c in dados_filtrados.keys()])
    params = list(dados_filtrados.values()) + where_params
    sql = f"UPDATE {tabela} SET {set_sql}{where_sql}"

    close_conn = False
    if conn is None:
        conn = conectar()
        close_conn = True

    try:
        with conn.cursor() as cur:
            linhas = cur.execute(sql, params)
        if close_conn:
            conn.commit()
        return {"linhas_afetadas": linhas}
    except Exception:
        if close_conn:
            conn.rollback()
        raise
    finally:
        if close_conn:
            conn.close()


def deletar(nome_tabela, filtros):
    where_sql, params = montar_where(nome_tabela, filtros or {})
    if not where_sql:
        raise ValueError("Delete bloqueado: informe pelo menos um filtro.")

    sql = f"DELETE FROM {tabela_sql(nome_tabela)}{where_sql}"

    with conectar() as conn:
        try:
            with conn.cursor() as cur:
                linhas = cur.execute(sql, params)
            conn.commit()
            return {"linhas_afetadas": linhas}
        except Exception:
            conn.rollback()
            raise


# ============================================================
# CONSULTAS NO PADRÃO DOS APPS
# ============================================================

def buscar_filiais():
    # Base externa usada para alimentar/identificar filial.
    sql = """
        SELECT *
        FROM `indicadores_matriz`.`filiais`
        ORDER BY `filial` ASC
    """
    with conectar() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            return cur.fetchall()


def buscar_maquinas(id_filial=""):
    filtros = {}
    if possui_filial(id_filial):
        filtros["id_filial"] = id_filial
    return selecionar("maquinas", filtros=filtros, order_by="codigo", ascending=True)


def buscar_checks(id_filial="", status_check=""):
    filtros = {}
    if possui_filial(id_filial):
        filtros["id_filial"] = id_filial
    if str(status_check or "").strip():
        filtros["status_check"] = status_check
    return selecionar("check_empi", filtros=filtros, order_by="data_abertura", ascending=False)


def buscar_pendencias(id_filial=""):
    filtros = {}
    if possui_filial(id_filial):
        filtros["id_filial"] = id_filial
    return selecionar("check_empi_pendencias", filtros=filtros, order_by="criado_em", ascending=False)


def buscar_pendencias_abertas(id_filial="", limit=None):
    sql = """
        SELECT *
        FROM `check_maquinas`.`check_empi_pendencias`
        WHERE (`status_pendencia` IN ('ABERTA', 'EM_ANALISE'))
          AND (`resolvido` = 0 OR `resolvido` IS NULL)
    """
    params = []
    if possui_filial(id_filial):
        sql += " AND `id_filial` = %s"
        params.append(id_filial)
    sql += " ORDER BY `criado_em` DESC"
    if limit:
        sql += " LIMIT %s"
        params.append(int(limit))

    with conectar() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
    return [normalizar_linha_saida("check_empi_pendencias", r) for r in rows]


def buscar_pendencias_por_checks(ids_checks):
    if not ids_checks:
        return []
    return selecionar("check_empi_pendencias", filtros={"id_check": ids_checks}, order_by="criado_em", ascending=False)


def buscar_check_por_id(id_check, id_filial=""):
    filtros = {"id": id_check}
    if possui_filial(id_filial):
        filtros["id_filial"] = id_filial
    return selecionar_um("check_empi", filtros)


def buscar_pendencia_por_id(id_pendencia, id_filial=""):
    filtros = {"id": id_pendencia}
    if possui_filial(id_filial):
        filtros["id_filial"] = id_filial
    return selecionar_um("check_empi_pendencias", filtros)


def buscar_pendencias_do_check(id_check, id_filial=""):
    filtros = {"id_check": id_check}
    if possui_filial(id_filial):
        filtros["id_filial"] = id_filial
    return selecionar("check_empi_pendencias", filtros=filtros, order_by="criado_em", ascending=False)


def buscar_pendencias_da_maquina(codigo_maquina, id_filial=""):
    filtros = {"empilhadeira": codigo_maquina}
    if possui_filial(id_filial):
        filtros["id_filial"] = id_filial
    return selecionar("check_empi_pendencias", filtros=filtros, order_by="criado_em", ascending=False)


def buscar_maquina_por_codigo(codigo_maquina, id_filial=""):
    filtros = {"codigo": codigo_maquina}
    if possui_filial(id_filial):
        filtros["id_filial"] = id_filial
    return selecionar_um("maquinas", filtros)


def buscar_anexos_do_check(id_check):
    return selecionar("check_empi_anexos", filtros={"id_check": id_check}, order_by="criado_em", ascending=False, colunas=ANEXOS_SELECT)


def buscar_anexos_por_empilhadeira(empilhadeira):
    return selecionar("check_empi_anexos", filtros={"empilhadeira": empilhadeira}, order_by="criado_em", ascending=False, colunas=ANEXOS_SELECT)


def carregar_base_operacional(id_filial=""):
    maquinas = buscar_maquinas(id_filial=id_filial)
    checks = buscar_checks(id_filial=id_filial)
    pendencias = buscar_pendencias(id_filial=id_filial)

    pendencias_por_check = []
    if possui_filial(id_filial):
        ids_checks = [c.get("id") for c in checks if c.get("id") is not None]
        pendencias_por_check = buscar_pendencias_por_checks(ids_checks)

    unificadas = []
    ids = set()
    for p in [*pendencias, *pendencias_por_check]:
        pid = str(p.get("id"))
        if pid in ids:
            continue
        ids.add(pid)
        unificadas.append(p)

    def data_key(item):
        valor = item.get("criado_em")
        if isinstance(valor, datetime):
            return valor
        try:
            return datetime.fromisoformat(str(valor))
        except Exception:
            return datetime.min

    unificadas.sort(key=data_key, reverse=True)

    return {
        "maquinas": maquinas,
        "checks": checks,
        "pendencias": unificadas,
    }


def carregar_detalhes_manutencao(id_pendencia=None, pendencia_base=None, id_filial=""):
    pendencia = dict(pendencia_base or {})
    if id_pendencia is None:
        id_pendencia = pendencia.get("id")

    if id_pendencia:
        pendencia_banco = buscar_pendencia_por_id(id_pendencia, id_filial=id_filial)
        if pendencia_banco:
            pendencia = pendencia_banco

    id_check = pendencia.get("id_check")
    codigo = str(pendencia.get("empilhadeira") or "")

    check = buscar_check_por_id(id_check, id_filial=id_filial) if id_check else None
    pendencias_check = buscar_pendencias_do_check(id_check, id_filial=id_filial) if id_check else []
    anexos_check = buscar_anexos_do_check(id_check) if id_check else []
    pendencias_maquina = buscar_pendencias_da_maquina(codigo, id_filial=id_filial) if codigo else []
    maquina = buscar_maquina_por_codigo(codigo, id_filial=id_filial) if codigo else None

    return {
        "pendencia": pendencia,
        "check": check,
        "pendenciasDoCheck": pendencias_check,
        "anexosDoCheck": anexos_check,
        "pendenciasDaMaquina": pendencias_maquina,
        "maquina": maquina,
    }


# ============================================================
# AÇÕES ESPECÍFICAS DOS APPS
# ============================================================

def autenticar_usuario_web(usuario, senha):
    return selecionar_um("usuarios_web_check", {"usuario": usuario, "senha": senha})


def colocar_pendencia_em_analise(id_pendencia):
    return atualizar("check_empi_pendencias", {"status_pendencia": "EM_ANALISE"}, {"id": id_pendencia})


def resolver_pendencia(id_pendencia, responsavel, resolvido_em=None, observacao_resolucao=None):
    return atualizar(
        "check_empi_pendencias",
        {
            "status_pendencia": "RESOLVIDA",
            "resolvido": True,
            "resolvido_por": responsavel,
            "resolvido_em": resolvido_em or agora_mysql(),
            "obs_resolucao": observacao_resolucao,
        },
        {"id": id_pendencia},
    )


def liberar_maquina(codigo_maquina, id_filial=""):
    filtros = {"codigo": codigo_maquina}
    if possui_filial(id_filial):
        filtros["id_filial"] = id_filial
    return atualizar("maquinas", {"ativo": "Liberado"}, filtros)


def atualizar_controle_preventiva_maquina(
    codigo_maquina,
    id_filial,
    horimetro_atual,
    horimetro_manutencao,
    intervalo_preventiva_horas,
    proxima_manutencao_hora,
    ultimo_registro_horimetro=None,
    ultima_manutencao=None,
):
    filtros = {"codigo": codigo_maquina}
    if possui_filial(id_filial):
        filtros["id_filial"] = id_filial

    return atualizar(
        "maquinas",
        {
            "horimetro_atual": horimetro_atual,
            "ultimo_reg_horimetro": ultimo_registro_horimetro or agora_mysql(),
            "horimetro_manutencao": horimetro_manutencao,
            "ultima_manutencao": ultima_manutencao or agora_mysql(),
            "intervalo_preventiva_horas": intervalo_preventiva_horas,
            "prox_manutencao_hora": proxima_manutencao_hora,
        },
        filtros,
    )


def finalizar_turno(id_check, codigo_maquina, id_filial, horimetro_final):
    agora = agora_mysql()

    with conectar() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT `id`
                    FROM `check_maquinas`.`check_empi_pendencias`
                    WHERE `empilhadeira` = %s
                      AND `id_filial` = %s
                      AND `status_pendencia` IN ('ABERTA', 'EM_ANALISE')
                    LIMIT 1
                    """,
                    [codigo_maquina, id_filial],
                )
                possui_pendencia = cur.fetchone() is not None

            atualizar(
                "check_empi",
                {
                    "horimetro_final": horimetro_final,
                    "status_check": "FINALIZADO",
                    "data_finalizacao": agora,
                    "atualizado_em": agora,
                },
                {"id": id_check},
                conn=conn,
            )

            atualizar(
                "maquinas",
                {
                    "ativo": "Manutenção" if possui_pendencia else "Liberado",
                    "horimetro_atual": horimetro_final,
                    "ultimo_reg_horimetro": agora,
                },
                {"codigo": codigo_maquina, "id_filial": id_filial},
                conn=conn,
            )

            conn.commit()
            return {
                "check_finalizado": True,
                "maquina_liberada": not possui_pendencia,
                "possui_pendencia_manutencao": possui_pendencia,
            }
        except Exception:
            conn.rollback()
            raise


def salvar_check(dados_check):
    if dados_check is None:
        dados_check = {}

    if not isinstance(dados_check, dict):
        raise ValueError("Dados do check invalidos.")

    if not dados_check:
        raise ValueError("Dados do check nao informados.")

    agora = agora_mysql()

    with conectar() as conn:
        try:
            check = inserir("check_empi", dados_check, conn=conn)
            id_check = check.get("id")

            codigo = dados_check.get("empilhadeira")
            id_filial = dados_check.get("id_filial")
            horimetro = dados_check.get("horimetro_inicial")

            if codigo and id_filial and horimetro is not None:
                atualizar(
                    "maquinas",
                    {
                        "ativo": "Em uso",
                        "horimetro_atual": horimetro,
                        "ultimo_reg_horimetro": agora,
                    },
                    {"codigo": codigo, "id_filial": id_filial},
                    conn=conn,
                )

            conn.commit()
            return {
                "check": check,
                "id_check": id_check,
                "pendencias": [],
            }
        except Exception:
            conn.rollback()
            raise


def salvar_check_com_pendencias(dados_check, pendencias=None):
    """
    Ação transacional opcional para o app mobile.
    Insere check_empi, insere pendências vinculadas ao id_check e marca a máquina como inativa.
    As fotos/anexos continuam no endpoint de imagem + inserirAnexoCheck.
    """
    if dados_check is None:
        dados_check = {}

    if not isinstance(dados_check, dict):
        raise ValueError("Dados do check invalidos.")

    if not dados_check:
        raise ValueError("Dados do check nao informados.")

    if pendencias is None:
        pendencias = []

    if not isinstance(pendencias, list):
        raise ValueError("Lista de pendencias invalida.")

    agora = agora_mysql()

    with conectar() as conn:
        try:
            check = inserir("check_empi", dados_check, conn=conn)
            id_check = check.get("id")

            pendencias_salvas = []
            for p in pendencias:
                item = dict(p)
                item["id_check"] = id_check
                item.setdefault("status_pendencia", "ABERTA")
                item.setdefault("criado_em", agora)
                pendencias_salvas.append(inserir("check_empi_pendencias", item, conn=conn))

            codigo = dados_check.get("empilhadeira")
            id_filial = dados_check.get("id_filial")
            horimetro = dados_check.get("horimetro_inicial")

            if codigo and id_filial and horimetro is not None:
                atualizar(
                    "maquinas",
                    {
                        "ativo": "Em uso",
                        "horimetro_atual": horimetro,
                        "ultimo_reg_horimetro": agora,
                    },
                    {"codigo": codigo, "id_filial": id_filial},
                    conn=conn,
                )

            conn.commit()
            return {
                "check": check,
                "id_check": id_check,
                "pendencias": pendencias_salvas,
            }
        except Exception:
            conn.rollback()
            raise


def atualizar_pendencia_anexos(id_pendencia, anexos):
    return atualizar("check_empi_pendencias", {"anexos": anexos}, {"id": id_pendencia})


# ============================================================
# HANDLER VERCEL
# ============================================================

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        set_cors_headers(self)
        self.end_headers()

    def do_GET(self):
        if not validar_token(self):
            return responder(self, 401, {"sucesso": False, "erro": "Token inválido ou ausente."})

        try:
            query = parse_qs(urlparse(self.path).query)
            acao = query_param(query, "acao", "ping")

            if acao in ["ping", "testeConexao"]:
                return responder(self, 200, {"sucesso": True, "dados": self._teste_conexao()})

            if acao == "buscarFiliais":
                return responder(self, 200, {"sucesso": True, "dados": buscar_filiais()})

            if acao == "buscarMaquinas":
                return responder(self, 200, {"sucesso": True, "dados": buscar_maquinas(query_param(query, "idFilial", ""))})

            if acao == "buscarChecks":
                return responder(self, 200, {"sucesso": True, "dados": buscar_checks(query_param(query, "idFilial", ""), query_param(query, "statusCheck", ""))})

            if acao == "buscarPendencias":
                return responder(self, 200, {"sucesso": True, "dados": buscar_pendencias(query_param(query, "idFilial", ""))})

            if acao == "buscarPendenciasAbertas":
                return responder(self, 200, {"sucesso": True, "dados": buscar_pendencias_abertas(query_param(query, "idFilial", ""), query_param(query, "limit", ""))})

            if acao == "buscarPendenciasPorChecks":
                return responder(self, 200, {"sucesso": True, "dados": buscar_pendencias_por_checks(query_lista(query, "idsChecks"))})

            if acao == "carregarBaseOperacional":
                return responder(self, 200, {"sucesso": True, "dados": carregar_base_operacional(query_param(query, "idFilial", ""))})

            if acao == "buscarPendenciasDoCheck":
                return responder(self, 200, {"sucesso": True, "dados": buscar_pendencias_do_check(query_param(query, "idCheck"), query_param(query, "idFilial", ""))})

            if acao == "buscarPendenciaPorId":
                return responder(self, 200, {"sucesso": True, "dados": buscar_pendencia_por_id(query_param(query, "idPendencia"), query_param(query, "idFilial", ""))})

            if acao == "buscarCheckPorId":
                return responder(self, 200, {"sucesso": True, "dados": buscar_check_por_id(query_param(query, "idCheck"), query_param(query, "idFilial", ""))})

            if acao == "buscarPendenciasDaMaquina":
                return responder(self, 200, {"sucesso": True, "dados": buscar_pendencias_da_maquina(query_param(query, "codigoMaquina"), query_param(query, "idFilial", ""))})

            if acao == "buscarMaquinaPorCodigo":
                return responder(self, 200, {"sucesso": True, "dados": buscar_maquina_por_codigo(query_param(query, "codigoMaquina"), query_param(query, "idFilial", ""))})

            if acao == "buscarAnexosDoCheck":
                return responder(self, 200, {"sucesso": True, "dados": buscar_anexos_do_check(query_param(query, "idCheck"))})

            if acao == "buscarAnexosPorEmpilhadeira":
                return responder(self, 200, {"sucesso": True, "dados": buscar_anexos_por_empilhadeira(query_param(query, "empilhadeira"))})

            if acao == "carregarDetalhesManutencao":
                return responder(self, 200, {"sucesso": True, "dados": carregar_detalhes_manutencao(id_pendencia=query_param(query, "idPendencia", None), id_filial=query_param(query, "idFilial", ""))})

            if acao == "select":
                tabela = query_param(query, "tabela")
                filtros = {}
                if query_param(query, "id", ""):
                    filtros["id"] = query_param(query, "id")
                if query_param(query, "idFilial", ""):
                    filtros["id_filial"] = query_param(query, "idFilial")
                order_by = query_param(query, "orderBy", "") or None
                asc = query_param(query, "ascending", "true").lower() != "false"
                limit = query_param(query, "limit", "100")
                return responder(self, 200, {"sucesso": True, "dados": selecionar(tabela, filtros=filtros, order_by=order_by, ascending=asc, limit=limit)})

            return responder(self, 400, {"sucesso": False, "erro": f"Ação GET não reconhecida: {acao}"})

        except Exception as e:
            return self._erro(e)

    def do_POST(self):
        if not validar_token(self):
            return responder(self, 401, {"sucesso": False, "erro": "Token inválido ou ausente."})

        try:
            query = parse_qs(urlparse(self.path).query)
            body = ler_json_body(self)
            acao = body.get("acao") or query_param(query, "acao", "")

            if acao == "autenticarUsuarioWeb":
                usuario = autenticar_usuario_web(body.get("usuario", ""), body.get("senha", ""))
                return responder(self, 200, {"sucesso": usuario is not None, "dados": usuario})

            if acao == "insert":
                return responder(self, 200, {"sucesso": True, "dados": inserir(body.get("tabela"), body.get("dados", {}))})

            if acao == "bulkInsert":
                return responder(self, 200, {"sucesso": True, "dados": inserir_varios(body.get("tabela"), body.get("dados", []))})

            if acao == "inserirMaquina":
                return responder(self, 200, {"sucesso": True, "dados": inserir("maquinas", body.get("dados", body))})

            if acao == "inserirCheck":
                return responder(self, 200, {"sucesso": True, "dados": inserir("check_empi", body.get("dados", body))})

            if acao == "inserirPendencia":
                return responder(self, 200, {"sucesso": True, "dados": inserir("check_empi_pendencias", body.get("dados", body))})

            if acao == "inserirPendencias":
                return responder(self, 200, {"sucesso": True, "dados": inserir_varios("check_empi_pendencias", body.get("dados", body.get("pendencias", [])))})

            if acao == "inserirAnexoCheck":
                return responder(self, 200, {"sucesso": True, "dados": inserir("check_empi_anexos", body.get("dados", body))})

            if acao == "salvarCheck":
                dados_check = body.get("check") or body.get("dados") or {}

                return responder(self, 200, {
                    "sucesso": True,
                    "dados": salvar_check(dados_check),
                })

            if acao == "salvarCheckComPendencias":
                dados_check = body.get("check") or body.get("dados") or {}
                pendencias = body.get("pendencias") or []

                return responder(self, 200, {
                    "sucesso": True,
                    "dados": salvar_check_com_pendencias(dados_check, pendencias),
                })

            if acao == "carregarBaseOperacional":
                return responder(self, 200, {"sucesso": True, "dados": carregar_base_operacional(body.get("idFilial", ""))})

            if acao == "carregarDetalhesManutencao":
                return responder(self, 200, {
                    "sucesso": True,
                    "dados": carregar_detalhes_manutencao(
                        id_pendencia=body.get("idPendencia"),
                        pendencia_base=body.get("pendenciaBase"),
                        id_filial=body.get("idFilial", ""),
                    ),
                })

            return responder(self, 400, {"sucesso": False, "erro": f"Ação POST não reconhecida: {acao}"})

        except Exception as e:
            return self._erro(e)

    def do_PUT(self):
        return self._handle_update()

    def do_PATCH(self):
        return self._handle_update()

    def do_DELETE(self):
        if not validar_token(self):
            return responder(self, 401, {"sucesso": False, "erro": "Token inválido ou ausente."})

        try:
            query = parse_qs(urlparse(self.path).query)
            body = ler_json_body(self)
            tabela = body.get("tabela") or query_param(query, "tabela")
            filtros = body.get("filtros", {})
            id_registro = body.get("id") or query_param(query, "id", "")
            if id_registro and not filtros:
                filtros = {"id": id_registro}
            return responder(self, 200, {"sucesso": True, "dados": deletar(tabela, filtros)})
        except Exception as e:
            return self._erro(e)

    def _handle_update(self):
        if not validar_token(self):
            return responder(self, 401, {"sucesso": False, "erro": "Token inválido ou ausente."})

        try:
            query = parse_qs(urlparse(self.path).query)
            body = ler_json_body(self)
            acao = body.get("acao") or query_param(query, "acao", "")

            if acao == "update":
                filtros = body.get("filtros", {})
                if body.get("id") is not None and not filtros:
                    filtros = {"id": body.get("id")}
                return responder(self, 200, {"sucesso": True, "dados": atualizar(body.get("tabela"), body.get("dados", {}), filtros)})

            if acao == "colocarPendenciaEmAnalise":
                return responder(self, 200, {"sucesso": True, "dados": colocar_pendencia_em_analise(body.get("idPendencia"))})

            if acao == "resolverPendencia":
                return responder(self, 200, {"sucesso": True, "dados": resolver_pendencia(body.get("idPendencia"), body.get("responsavel", ""), body.get("resolvidoEm"), body.get("observacaoResolucao"))})

            if acao == "liberarMaquina":
                return responder(self, 200, {"sucesso": True, "dados": liberar_maquina(body.get("codigoMaquina", ""), body.get("idFilial", ""))})

            if acao == "atualizarControlePreventivaMaquina":
                return responder(self, 200, {"sucesso": True, "dados": atualizar_controle_preventiva_maquina(
                    codigo_maquina=body.get("codigoMaquina", ""),
                    id_filial=body.get("idFilial", ""),
                    horimetro_atual=body.get("horimetroAtual"),
                    horimetro_manutencao=body.get("horimetroManutencao"),
                    intervalo_preventiva_horas=body.get("intervaloPreventivaHoras"),
                    proxima_manutencao_hora=body.get("proximaManutencaoHora"),
                    ultimo_registro_horimetro=body.get("ultimoRegistroHorimetro"),
                    ultima_manutencao=body.get("ultimaManutencao"),
                )})

            if acao == "finalizarTurno":
                return responder(self, 200, {"sucesso": True, "dados": finalizar_turno(
                    id_check=body.get("idCheck"),
                    codigo_maquina=body.get("codigoMaquina", ""),
                    id_filial=body.get("idFilial"),
                    horimetro_final=body.get("horimetroFinal"),
                )})

            if acao == "atualizarPendenciaAnexos":
                return responder(self, 200, {"sucesso": True, "dados": atualizar_pendencia_anexos(body.get("idPendencia"), body.get("anexos", []))})

            return responder(self, 400, {"sucesso": False, "erro": f"Ação UPDATE não reconhecida: {acao}"})

        except Exception as e:
            return self._erro(e)

    def _teste_conexao(self):
        with conectar() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        1 AS conectado,
                        DATABASE() AS banco_atual,
                        NOW() AS data_hora_servidor
                """)
                return cur.fetchone()

    def _erro(self, e):
        detalhe = str(e)
        if os.environ.get("DEBUG_API", "").lower() in ["1", "true", "sim"]:
            detalhe = traceback.format_exc()
        return responder(self, 500, {"sucesso": False, "erro": "Erro ao processar requisição.", "detalhe": detalhe})
