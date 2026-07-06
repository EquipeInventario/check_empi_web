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
            "ultima_carga_realizada",
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
            "criticidade",
            "prazo_resolucao",
            "responsavel_manutencao",
            "bloqueia_operacao",
        ],
        "bool_columns": ["resolvido", "bloqueia_operacao"],
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
    "manutencao_servicos": {
        "schema": "check_maquinas",
        "table": "manutencao_servicos",
        "pk": "id",
        "columns": [
            "id",
            "id_filial",
            "id_maquina",
            "codigo_maquina",
            "id_pendencia",
            "id_check",
            "tipo_servico",
            "data_servico",
            "horimetro_servico",
            "descricao_servico",
            "condicoes_seguranca",
            "responsavel_execucao",
            "responsavel_liberacao",
            "resultado_liberacao",
            "observacao_liberacao",
            "tempo_parada_minutos",
            "status_servico",
            "checklist_liberacao_json",
            "plano_acao_json",
            "criado_por",
            "criado_em",
            "atualizado_em",
        ],
        "bool_columns": [],
        "json_columns": ["checklist_liberacao_json", "plano_acao_json"],
    },
    "manutencao_pecas": {
        "schema": "check_maquinas",
        "table": "manutencao_pecas",
        "pk": "id",
        "columns": [
            "id",
            "codigo_peca",
            "descricao",
            "categoria",
            "unidade",
            "fornecedor",
            "observacao",
            "ativo",
            "criado_em",
            "atualizado_em",
        ],
        "bool_columns": ["ativo"],
        "json_columns": [],
    },
    "manutencao_maquina_pecas": {
        "schema": "check_maquinas",
        "table": "manutencao_maquina_pecas",
        "pk": "id",
        "columns": [
            "id",
            "id_maquina",
            "codigo_maquina",
            "id_peca",
            "quantidade",
            "vida_util_horas",
            "vida_util_dias",
            "data_ultima_troca",
            "horimetro_ultima_troca",
            "proxima_troca_horimetro",
            "proxima_troca_data",
            "alerta_antecedencia_horas",
            "alerta_antecedencia_dias",
            "status",
            "observacao",
            "criado_em",
            "atualizado_em",
        ],
        "bool_columns": [],
        "json_columns": [],
    },
    "manutencao_trocas_pecas": {
        "schema": "check_maquinas",
        "table": "manutencao_trocas_pecas",
        "pk": "id",
        "columns": [
            "id",
            "id_maquina_peca",
            "id_servico",
            "codigo_maquina",
            "id_peca",
            "data_troca",
            "horimetro_troca",
            "quantidade",
            "responsavel",
            "observacao",
            "criado_em",
        ],
        "bool_columns": [],
        "json_columns": [],
    },
    "nr12_apreciacoes": {
        "schema": "check_maquinas",
        "table": "nr12_apreciacoes",
        "pk": "id",
        "columns": [
            "id",
            "id_filial",
            "id_maquina",
            "codigo_maquina",
            "data_apreciacao",
            "responsavel_tecnico",
            "empresa_responsavel",
            "numero_art",
            "data_art",
            "status",
            "observacao",
            "criado_por",
            "criado_em",
            "atualizado_em",
        ],
        "bool_columns": [],
        "json_columns": [],
    },
    "nr12_acoes": {
        "schema": "check_maquinas",
        "table": "nr12_acoes",
        "pk": "id",
        "columns": [
            "id",
            "id_apreciacao",
            "id_maquina",
            "codigo_maquina",
            "risco_identificado",
            "adequacao_necessaria",
            "prioridade",
            "prazo",
            "responsavel",
            "status",
            "data_conclusao",
            "bloqueia_operacao",
            "observacao",
            "criado_em",
            "atualizado_em",
        ],
        "bool_columns": ["bloqueia_operacao"],
        "json_columns": [],
    },
    "manutencao_procedimentos_emergencia": {
        "schema": "check_maquinas",
        "table": "manutencao_procedimentos_emergencia",
        "pk": "id",
        "columns": [
            "id",
            "id_filial",
            "cenario",
            "tipo_maquina",
            "descricao_risco",
            "procedimento",
            "quem_acionar",
            "isolamento_area",
            "equipamentos_necessarios",
            "responsavel_revisao",
            "data_revisao",
            "status",
            "observacao",
            "criado_em",
            "atualizado_em",
        ],
        "bool_columns": [],
        "json_columns": [],
    },
    "manutencao_anexos": {
        "schema": "check_maquinas",
        "table": "manutencao_anexos",
        "pk": "id",
        "columns": [
            "id",
            "origem_tabela",
            "origem_id",
            "tipo_anexo",
            "nome_arquivo",
            "caminho_arquivo",
            "url_publica",
            "storage_origem",
            "container_azure",
            "blob_azure",
            "url_azure",
            "criado_por",
            "criado_em",
        ],
        "bool_columns": [],
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
    "storage_origem",
    "container_azure",
    "blob_azure",
    "url_azure",
    "migrado_azure",
    "migrado_em",
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
    elif nome_tabela in [
        "check_empi_pendencias",
        "check_empi_anexos",
        "usuarios_web_check",
        "manutencao_servicos",
        "manutencao_pecas",
        "manutencao_maquina_pecas",
        "manutencao_trocas_pecas",
        "nr12_apreciacoes",
        "nr12_acoes",
        "manutencao_procedimentos_emergencia",
        "manutencao_anexos",
    ]:
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




def _valor_texto(valor):
    return str(valor or "").strip()


def _valor_data(valor):
    if valor in [None, ""]:
        return None
    if isinstance(valor, datetime):
        return valor
    if isinstance(valor, date):
        return datetime(valor.year, valor.month, valor.day)
    texto = str(valor).strip().replace("Z", "")
    try:
        return datetime.fromisoformat(texto)
    except Exception:
        pass
    for formato in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y"]:
        try:
            return datetime.strptime(texto, formato)
        except Exception:
            continue
    return None


def _somar_dias(valor_data, dias):
    data_base = _valor_data(valor_data)
    try:
        dias_int = int(dias)
    except Exception:
        dias_int = 0
    if not data_base or dias_int <= 0:
        return None
    from datetime import timedelta
    return (data_base + timedelta(days=dias_int)).date().isoformat()


def _normalizar_status_fechado(status):
    texto = _valor_texto(status).upper().replace("_", " ")
    return texto in [
        "RESOLVIDA",
        "RESOLVIDO",
        "SOLUCIONADA",
        "SOLUCIONADO",
        "FINALIZADA",
        "FINALIZADO",
        "FECHADA",
        "FECHADO",
        "CONCLUIDA",
        "CONCLUÍDA",
        "CONCLUIDO",
        "CONCLUÍDO",
        "CANCELADA",
        "CANCELADO",
    ]


def buscar_servicos_manutencao(
    id_filial="",
    codigo_maquina="",
    id_pendencia="",
    id_check="",
    tipo_servico="",
    status_servico="",
    limit=500,
):
    filtros = {}
    if possui_filial(id_filial):
        filtros["id_filial"] = id_filial
    if _valor_texto(codigo_maquina):
        filtros["codigo_maquina"] = _valor_texto(codigo_maquina)
    if _valor_texto(id_pendencia):
        filtros["id_pendencia"] = id_pendencia
    if _valor_texto(id_check):
        filtros["id_check"] = id_check
    if _valor_texto(tipo_servico):
        filtros["tipo_servico"] = tipo_servico
    if _valor_texto(status_servico):
        filtros["status_servico"] = status_servico
    return selecionar(
        "manutencao_servicos",
        filtros=filtros,
        order_by="data_servico",
        ascending=False,
        limit=limit or 500,
    )


def salvar_servico_manutencao(payload):
    payload = dict(payload or {})
    servico = dict(payload.get("servico") or payload.get("dados") or payload)
    resolver_pend = bool(payload.get("resolverPendencia") or payload.get("resolver_pendencia"))
    atualizar_preventiva = bool(payload.get("atualizarPreventiva") or payload.get("atualizar_preventiva"))

    id_servico = servico.pop("id", None)
    servico.setdefault("status_servico", "FINALIZADO")
    if not servico.get("data_servico"):
        servico["data_servico"] = agora_mysql()
    servico["atualizado_em"] = agora_mysql()

    if id_servico:
        atualizar("manutencao_servicos", servico, {"id": id_servico})
        salvo = selecionar_um("manutencao_servicos", {"id": id_servico})
    else:
        salvo = inserir("manutencao_servicos", servico)
        id_servico = salvo.get("id")

    codigo = _valor_texto(salvo.get("codigo_maquina") if salvo else servico.get("codigo_maquina"))
    id_filial = salvo.get("id_filial") if salvo else servico.get("id_filial")
    id_pendencia = salvo.get("id_pendencia") if salvo else servico.get("id_pendencia")
    responsavel = _valor_texto(
        (salvo or {}).get("responsavel_liberacao")
        or (salvo or {}).get("responsavel_execucao")
        or servico.get("responsavel_liberacao")
        or servico.get("responsavel_execucao")
    )
    resultado = _valor_texto((salvo or {}).get("resultado_liberacao") or servico.get("resultado_liberacao")).upper()

    if resolver_pend and id_pendencia and responsavel:
        resolver_pendencia(
            id_pendencia,
            responsavel,
            agora_mysql(),
            (salvo or {}).get("observacao_liberacao") or servico.get("observacao_liberacao"),
        )

    if resultado == "LIBERADO" and codigo:
        pendencias = buscar_pendencias_da_maquina(codigo, id_filial)
        abertas = [p for p in pendencias if not p.get("resolvido") and not _normalizar_status_fechado(p.get("status_pendencia"))]
        if not abertas:
            liberar_maquina(codigo, id_filial)

    if atualizar_preventiva and codigo:
        horimetro = (salvo or {}).get("horimetro_servico") or servico.get("horimetro_servico")
        if horimetro is not None:
            maquina = buscar_maquina_por_codigo(codigo, id_filial)
            intervalo = (maquina or {}).get("intervalo_preventiva_horas")
            try:
                prox = float(horimetro) + float(intervalo or 0)
            except Exception:
                prox = (maquina or {}).get("prox_manutencao_hora")
            atualizar(
                "maquinas",
                {
                    "horimetro_atual": horimetro,
                    "ultimo_reg_horimetro": agora_mysql(),
                    "horimetro_manutencao": horimetro,
                    "ultima_manutencao": (salvo or {}).get("data_servico") or agora_mysql(),
                    "prox_manutencao_hora": prox,
                },
                {"codigo": codigo, **({"id_filial": id_filial} if possui_filial(id_filial) else {})},
            )

    return selecionar_um("manutencao_servicos", {"id": id_servico})


def buscar_pecas_manutencao(busca="", ativo="", categoria="", limit=1000):
    sql = "SELECT * FROM `check_maquinas`.`manutencao_pecas` WHERE 1=1"
    params = []

    if _valor_texto(busca):
        termo = f"%{_valor_texto(busca)}%"
        sql += " AND (`codigo_peca` LIKE %s OR `descricao` LIKE %s OR `categoria` LIKE %s OR `fornecedor` LIKE %s)"
        params.extend([termo, termo, termo, termo])

    if _valor_texto(ativo):
        texto = _valor_texto(ativo).lower()
        if texto in ["true", "1", "s", "sim", "ativo"]:
            sql += " AND `ativo` = 1"
        elif texto in ["false", "0", "n", "nao", "não", "inativo"]:
            sql += " AND (`ativo` = 0 OR `ativo` IS NULL)"

    if _valor_texto(categoria):
        sql += " AND `categoria` = %s"
        params.append(categoria)

    sql += " ORDER BY `descricao` ASC LIMIT %s"
    params.append(max(1, min(int(limit or 1000), 2000)))

    with conectar() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
    return [normalizar_linha_saida("manutencao_pecas", r) for r in rows]


def salvar_peca_manutencao(payload):
    dados = dict(payload.get("peca") or payload.get("dados") or payload or {})
    id_peca = dados.pop("id", None)
    dados.setdefault("ativo", True)
    dados["atualizado_em"] = agora_mysql()
    if id_peca:
        atualizar("manutencao_pecas", dados, {"id": id_peca})
        return selecionar_um("manutencao_pecas", {"id": id_peca})
    return inserir("manutencao_pecas", dados)


def _linha_peca_maquina_com_status(linha, horimetro_atual=None):
    saida = serializar(linha or {})
    status_calculado = _valor_texto(saida.get("status") or "EM_DIA")
    alertas = []

    try:
        atual = float(horimetro_atual) if horimetro_atual not in [None, ""] else None
        prox_h = float(saida.get("proxima_troca_horimetro")) if saida.get("proxima_troca_horimetro") not in [None, ""] else None
        antecedencia_h = int(saida.get("alerta_antecedencia_horas") or 0)
        if atual is not None and prox_h is not None:
            restante = prox_h - atual
            saida["horas_restantes_troca"] = restante
            if restante <= 0:
                status_calculado = "VENCIDA_HORIMETRO"
                alertas.append("Troca vencida por horímetro")
            elif restante <= antecedencia_h:
                status_calculado = "PROXIMA_TROCA"
                alertas.append("Troca próxima por horímetro")
    except Exception:
        pass

    prox_data = _valor_data(saida.get("proxima_troca_data"))
    if prox_data:
        hoje = datetime.now()
        dias_restantes = (prox_data.date() - hoje.date()).days
        saida["dias_restantes_troca"] = dias_restantes
        try:
            antecedencia_d = int(saida.get("alerta_antecedencia_dias") or 0)
        except Exception:
            antecedencia_d = 0
        if dias_restantes <= 0:
            status_calculado = "VENCIDA_DATA"
            alertas.append("Troca vencida por data")
        elif dias_restantes <= antecedencia_d and status_calculado == _valor_texto(saida.get("status") or "EM_DIA"):
            status_calculado = "PROXIMA_TROCA"
            alertas.append("Troca próxima por data")

    saida["status_calculado"] = status_calculado
    saida["alertas"] = alertas
    return saida


def buscar_pecas_da_maquina(codigo_maquina="", id_maquina="", id_peca="", somente_alertas=False):
    sql = """
        SELECT
            mp.*,
            p.codigo_peca,
            p.descricao AS peca_descricao,
            p.categoria AS peca_categoria,
            p.unidade AS peca_unidade,
            p.fornecedor AS peca_fornecedor,
            m.horimetro_atual AS maquina_horimetro_atual,
            m.descricao AS maquina_descricao,
            m.tipo_maquina AS maquina_tipo
        FROM `check_maquinas`.`manutencao_maquina_pecas` mp
        LEFT JOIN `check_maquinas`.`manutencao_pecas` p ON p.id = mp.id_peca
        LEFT JOIN `check_maquinas`.`maquinas` m ON m.codigo = mp.codigo_maquina
        WHERE 1=1
    """
    params = []
    if _valor_texto(codigo_maquina):
        sql += " AND mp.codigo_maquina = %s"
        params.append(_valor_texto(codigo_maquina))
    if _valor_texto(id_maquina):
        sql += " AND mp.id_maquina = %s"
        params.append(id_maquina)
    if _valor_texto(id_peca):
        sql += " AND mp.id_peca = %s"
        params.append(id_peca)
    sql += " ORDER BY p.descricao ASC, mp.id ASC"

    with conectar() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

    saida = [_linha_peca_maquina_com_status(r, r.get("maquina_horimetro_atual")) for r in rows]
    if somente_alertas:
        saida = [r for r in saida if r.get("alertas")]
    return saida


def salvar_peca_da_maquina(payload):
    dados = dict(payload.get("maquinaPeca") or payload.get("maquina_peca") or payload.get("dados") or payload or {})
    id_registro = dados.pop("id", None)

    if not dados.get("proxima_troca_horimetro") and dados.get("horimetro_ultima_troca") not in [None, ""] and dados.get("vida_util_horas") not in [None, ""]:
        try:
            dados["proxima_troca_horimetro"] = float(dados["horimetro_ultima_troca"]) + int(dados["vida_util_horas"])
        except Exception:
            pass

    if not dados.get("proxima_troca_data") and dados.get("data_ultima_troca") and dados.get("vida_util_dias"):
        dados["proxima_troca_data"] = _somar_dias(dados.get("data_ultima_troca"), dados.get("vida_util_dias"))

    dados["atualizado_em"] = agora_mysql()
    if id_registro:
        atualizar("manutencao_maquina_pecas", dados, {"id": id_registro})
        return buscar_pecas_da_maquina(id_peca=dados.get("id_peca", "")) if not dados.get("codigo_maquina") else selecionar_um("manutencao_maquina_pecas", {"id": id_registro})
    return inserir("manutencao_maquina_pecas", dados)


def buscar_trocas_pecas(codigo_maquina="", id_maquina_peca="", id_peca="", id_servico="", limit=500):
    sql = """
        SELECT
            t.*,
            p.codigo_peca,
            p.descricao AS peca_descricao,
            p.categoria AS peca_categoria,
            s.tipo_servico,
            s.data_servico,
            s.descricao_servico
        FROM `check_maquinas`.`manutencao_trocas_pecas` t
        LEFT JOIN `check_maquinas`.`manutencao_pecas` p ON p.id = t.id_peca
        LEFT JOIN `check_maquinas`.`manutencao_servicos` s ON s.id = t.id_servico
        WHERE 1=1
    """
    params = []
    if _valor_texto(codigo_maquina):
        sql += " AND t.codigo_maquina = %s"
        params.append(codigo_maquina)
    if _valor_texto(id_maquina_peca):
        sql += " AND t.id_maquina_peca = %s"
        params.append(id_maquina_peca)
    if _valor_texto(id_peca):
        sql += " AND t.id_peca = %s"
        params.append(id_peca)
    if _valor_texto(id_servico):
        sql += " AND t.id_servico = %s"
        params.append(id_servico)
    sql += " ORDER BY t.data_troca DESC LIMIT %s"
    params.append(max(1, min(int(limit or 500), 2000)))

    with conectar() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()


def registrar_troca_peca(payload):
    dados = dict(payload.get("troca") or payload.get("dados") or payload or {})
    dados.setdefault("data_troca", agora_mysql())

    id_maquina_peca = dados.get("id_maquina_peca")
    if not id_maquina_peca:
        raise ValueError("Informe id_maquina_peca para registrar a troca.")

    maquina_peca = selecionar_um("manutencao_maquina_pecas", {"id": id_maquina_peca})
    if not maquina_peca:
        raise ValueError("Peça vinculada à máquina não encontrada.")

    dados.setdefault("codigo_maquina", maquina_peca.get("codigo_maquina"))
    dados.setdefault("id_peca", maquina_peca.get("id_peca"))
    troca = inserir("manutencao_trocas_pecas", dados)

    atualizacao = {
        "data_ultima_troca": dados.get("data_troca"),
        "horimetro_ultima_troca": dados.get("horimetro_troca"),
        "status": "EM_DIA",
        "atualizado_em": agora_mysql(),
    }

    if dados.get("horimetro_troca") not in [None, ""] and maquina_peca.get("vida_util_horas") not in [None, ""]:
        try:
            atualizacao["proxima_troca_horimetro"] = float(dados.get("horimetro_troca")) + int(maquina_peca.get("vida_util_horas"))
        except Exception:
            pass

    if maquina_peca.get("vida_util_dias") not in [None, ""]:
        proxima_data = _somar_dias(dados.get("data_troca"), maquina_peca.get("vida_util_dias"))
        if proxima_data:
            atualizacao["proxima_troca_data"] = proxima_data

    atualizar("manutencao_maquina_pecas", atualizacao, {"id": id_maquina_peca})

    return {
        "troca": troca,
        "maquinaPeca": selecionar_um("manutencao_maquina_pecas", {"id": id_maquina_peca}),
    }


def buscar_apreciacoes_nr12(id_filial="", codigo_maquina="", status="", limit=500):
    filtros = {}
    if possui_filial(id_filial):
        filtros["id_filial"] = id_filial
    if _valor_texto(codigo_maquina):
        filtros["codigo_maquina"] = codigo_maquina
    if _valor_texto(status):
        filtros["status"] = status
    return selecionar("nr12_apreciacoes", filtros=filtros, order_by="criado_em", ascending=False, limit=limit or 500)


def buscar_acoes_nr12(id_apreciacao="", id_filial="", codigo_maquina="", status="", somente_atrasadas=False, limit=1000):
    sql = """
        SELECT a.*
        FROM `check_maquinas`.`nr12_acoes` a
        LEFT JOIN `check_maquinas`.`nr12_apreciacoes` ap ON ap.id = a.id_apreciacao
        WHERE 1=1
    """
    params = []
    if _valor_texto(id_apreciacao):
        sql += " AND a.id_apreciacao = %s"
        params.append(id_apreciacao)
    if possui_filial(id_filial):
        sql += " AND ap.id_filial = %s"
        params.append(id_filial)
    if _valor_texto(codigo_maquina):
        sql += " AND a.codigo_maquina = %s"
        params.append(codigo_maquina)
    if _valor_texto(status):
        sql += " AND a.status = %s"
        params.append(status)
    if somente_atrasadas:
        sql += " AND a.prazo < CURDATE() AND a.status NOT IN ('CONCLUIDO', 'CONCLUÍDO', 'CONCLUIDA', 'CONCLUÍDA', 'CANCELADO', 'CANCELADA')"
    sql += " ORDER BY a.prazo ASC, a.id DESC LIMIT %s"
    params.append(max(1, min(int(limit or 1000), 2000)))

    with conectar() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
    return [normalizar_linha_saida("nr12_acoes", r) for r in rows]


def carregar_apreciacao_nr12(id_apreciacao):
    if id_apreciacao in [None, ""]:
        raise ValueError("Informe o ID da apreciação NR-12.")
    apreciacao = selecionar_um("nr12_apreciacoes", {"id": id_apreciacao})
    if not apreciacao:
        return None
    return {
        "apreciacao": apreciacao,
        "acoes": buscar_acoes_nr12(id_apreciacao=id_apreciacao),
        "anexos": buscar_anexos_manutencao("nr12_apreciacoes", id_apreciacao),
    }


def salvar_apreciacao_nr12(payload):
    payload = dict(payload or {})
    dados = dict(payload.get("apreciacao") or payload.get("dados") or payload or {})
    acoes = payload.get("acoes")
    id_apreciacao = dados.pop("id", None)

    tem_art = _valor_texto(dados.get("numero_art")) and _valor_texto(dados.get("data_art"))
    if _valor_texto(dados.get("status")).upper() in ["CONCLUIDA", "CONCLUÍDA", "ATENDIDA", "CONCLUIDA_COM_ART"]:
        dados["status"] = "CONCLUIDA_COM_ART" if tem_art else "CONCLUIDA_SEM_ART"
    dados["atualizado_em"] = agora_mysql()

    if id_apreciacao:
        atualizar("nr12_apreciacoes", dados, {"id": id_apreciacao})
    else:
        criada = inserir("nr12_apreciacoes", dados)
        id_apreciacao = criada.get("id")

    if isinstance(acoes, list):
        for acao in acoes:
            salvar_acao_nr12({**dict(acao or {}), "id_apreciacao": id_apreciacao})

    return carregar_apreciacao_nr12(id_apreciacao)


def salvar_acao_nr12(payload):
    dados = dict(payload.get("acaoNr12") or payload.get("acao") or payload.get("dados") or payload or {})
    id_acao = dados.pop("id", None)
    dados["atualizado_em"] = agora_mysql()
    if id_acao:
        atualizar("nr12_acoes", dados, {"id": id_acao})
        return selecionar_um("nr12_acoes", {"id": id_acao})
    return inserir("nr12_acoes", dados)


def buscar_procedimentos_emergencia(id_filial="", tipo_maquina="", status="ATIVO", limit=1000):
    filtros = {}
    if possui_filial(id_filial):
        filtros["id_filial"] = id_filial
    if _valor_texto(tipo_maquina):
        filtros["tipo_maquina"] = tipo_maquina
    if _valor_texto(status):
        filtros["status"] = status
    return selecionar("manutencao_procedimentos_emergencia", filtros=filtros, order_by="cenario", ascending=True, limit=limit or 1000)


def salvar_procedimento_emergencia(payload):
    dados = dict(payload.get("procedimento") or payload.get("dados") or payload or {})
    id_registro = dados.pop("id", None)
    dados["atualizado_em"] = agora_mysql()
    if id_registro:
        atualizar("manutencao_procedimentos_emergencia", dados, {"id": id_registro})
        return selecionar_um("manutencao_procedimentos_emergencia", {"id": id_registro})
    return inserir("manutencao_procedimentos_emergencia", dados)


def buscar_anexos_manutencao(origem_tabela="", origem_id="", tipo_anexo="", limit=500):
    filtros = {}
    if _valor_texto(origem_tabela):
        filtros["origem_tabela"] = origem_tabela
    if _valor_texto(origem_id):
        filtros["origem_id"] = origem_id
    if _valor_texto(tipo_anexo):
        filtros["tipo_anexo"] = tipo_anexo
    return selecionar("manutencao_anexos", filtros=filtros, order_by="criado_em", ascending=False, limit=limit or 500)


def salvar_anexo_manutencao(payload):
    dados = dict(payload.get("anexo") or payload.get("dados") or payload or {})
    id_anexo = dados.pop("id", None)
    if id_anexo:
        atualizar("manutencao_anexos", dados, {"id": id_anexo})
        return selecionar_um("manutencao_anexos", {"id": id_anexo})
    return inserir("manutencao_anexos", dados)


def carregar_plano_manutencao_maquina(codigo_maquina, id_filial=""):
    codigo = _valor_texto(codigo_maquina)
    if not codigo:
        raise ValueError("Informe o código da máquina/equipamento.")

    maquina = buscar_maquina_por_codigo(codigo, id_filial=id_filial)
    checks = []
    if codigo:
        sql_checks = """
            SELECT *
            FROM `check_maquinas`.`check_empi`
            WHERE `empilhadeira` = %s
        """
        params = [codigo]
        if possui_filial(id_filial):
            sql_checks += " AND `id_filial` = %s"
            params.append(id_filial)
        sql_checks += " ORDER BY `data_abertura` DESC LIMIT 100"
        with conectar() as conn:
            with conn.cursor() as cur:
                cur.execute(sql_checks, params)
                checks = [normalizar_linha_saida("check_empi", r) for r in cur.fetchall()]

    apreciacoes = buscar_apreciacoes_nr12(id_filial=id_filial, codigo_maquina=codigo, limit=50)
    ids_apreciacoes = [a.get("id") for a in apreciacoes if a.get("id")]
    acoes = []
    for id_ap in ids_apreciacoes:
        acoes.extend(buscar_acoes_nr12(id_apreciacao=id_ap, limit=500))

    pecas = buscar_pecas_da_maquina(codigo_maquina=codigo)
    servicos = buscar_servicos_manutencao(
        id_filial=id_filial,
        codigo_maquina=codigo,
        limit=200,
    )
    anexos_manutencao = []
    if maquina:
        anexos_manutencao.extend(
            buscar_anexos_manutencao("maquinas", maquina.get("id", ""))
        )
    for servico in servicos:
        if servico.get("id"):
            anexos_manutencao.extend(
                buscar_anexos_manutencao("manutencao_servicos", servico.get("id"))
            )
    for apreciacao in apreciacoes:
        if apreciacao.get("id"):
            anexos_manutencao.extend(
                buscar_anexos_manutencao("nr12_apreciacoes", apreciacao.get("id"))
            )
    for acao in acoes:
        if acao.get("id"):
            anexos_manutencao.extend(
                buscar_anexos_manutencao("nr12_acoes", acao.get("id"))
            )

    return {
        "maquina": maquina,
        "checks": checks,
        "pendencias": buscar_pendencias_da_maquina(codigo, id_filial=id_filial),
        "servicos": servicos,
        "pecas": pecas,
        "trocasPecas": buscar_trocas_pecas(codigo_maquina=codigo, limit=200),
        "apreciacoesNr12": apreciacoes,
        "acoesNr12": acoes,
        "procedimentosEmergencia": buscar_procedimentos_emergencia(
            id_filial=id_filial,
            tipo_maquina=(maquina or {}).get("tipo_maquina", ""),
            status="ATIVO",
        ),
        "anexosManutencao": anexos_manutencao,
    }


def buscar_alertas_plano_manutencao(id_filial=""):
    maquinas = buscar_maquinas(id_filial=id_filial)
    pecas_alerta = []
    for maquina in maquinas:
        codigo = maquina.get("codigo")
        if not codigo:
            continue
        pecas_alerta.extend(buscar_pecas_da_maquina(codigo_maquina=codigo, somente_alertas=True))

    acoes_atrasadas = buscar_acoes_nr12(id_filial=id_filial, somente_atrasadas=True, limit=1000)
    apreciacoes = buscar_apreciacoes_nr12(id_filial=id_filial, limit=1000)
    apreciacoes_sem_art = [a for a in apreciacoes if not _valor_texto(a.get("numero_art"))]

    return {
        "pecasAlerta": pecas_alerta,
        "acoesNr12Atrasadas": acoes_atrasadas,
        "apreciacoesSemArt": apreciacoes_sem_art,
        "totalPecasAlerta": len(pecas_alerta),
        "totalAcoesNr12Atrasadas": len(acoes_atrasadas),
        "totalApreciacoesSemArt": len(apreciacoes_sem_art),
    }

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


            if acao == "carregarPlanoManutencaoMaquina":
                return responder(self, 200, {"sucesso": True, "dados": carregar_plano_manutencao_maquina(
                    query_param(query, "codigoMaquina"),
                    query_param(query, "idFilial", ""),
                )})

            if acao == "buscarServicosManutencao":
                return responder(self, 200, {"sucesso": True, "dados": buscar_servicos_manutencao(
                    id_filial=query_param(query, "idFilial", ""),
                    codigo_maquina=query_param(query, "codigoMaquina", ""),
                    id_pendencia=query_param(query, "idPendencia", ""),
                    id_check=query_param(query, "idCheck", ""),
                    tipo_servico=query_param(query, "tipoServico", ""),
                    status_servico=query_param(query, "statusServico", ""),
                    limit=query_param(query, "limit", "500"),
                )})

            if acao == "buscarPecasManutencao":
                return responder(self, 200, {"sucesso": True, "dados": buscar_pecas_manutencao(
                    busca=query_param(query, "busca", ""),
                    ativo=query_param(query, "ativo", ""),
                    categoria=query_param(query, "categoria", ""),
                    limit=query_param(query, "limit", "1000"),
                )})

            if acao == "buscarPecasDaMaquina":
                return responder(self, 200, {"sucesso": True, "dados": buscar_pecas_da_maquina(
                    codigo_maquina=query_param(query, "codigoMaquina", ""),
                    id_maquina=query_param(query, "idMaquina", ""),
                    id_peca=query_param(query, "idPeca", ""),
                    somente_alertas=query_param(query, "somenteAlertas", "false").lower() in ["1", "true", "sim"],
                )})

            if acao == "buscarTrocasPecas":
                return responder(self, 200, {"sucesso": True, "dados": buscar_trocas_pecas(
                    codigo_maquina=query_param(query, "codigoMaquina", ""),
                    id_maquina_peca=query_param(query, "idMaquinaPeca", ""),
                    id_peca=query_param(query, "idPeca", ""),
                    id_servico=query_param(query, "idServico", ""),
                    limit=query_param(query, "limit", "500"),
                )})

            if acao == "buscarApreciacoesNr12":
                return responder(self, 200, {"sucesso": True, "dados": buscar_apreciacoes_nr12(
                    id_filial=query_param(query, "idFilial", ""),
                    codigo_maquina=query_param(query, "codigoMaquina", ""),
                    status=query_param(query, "status", ""),
                    limit=query_param(query, "limit", "500"),
                )})

            if acao == "carregarApreciacaoNr12":
                return responder(self, 200, {"sucesso": True, "dados": carregar_apreciacao_nr12(
                    query_param(query, "idApreciacao", None)
                )})

            if acao == "buscarAcoesNr12":
                return responder(self, 200, {"sucesso": True, "dados": buscar_acoes_nr12(
                    id_apreciacao=query_param(query, "idApreciacao", ""),
                    id_filial=query_param(query, "idFilial", ""),
                    codigo_maquina=query_param(query, "codigoMaquina", ""),
                    status=query_param(query, "status", ""),
                    somente_atrasadas=query_param(query, "somenteAtrasadas", "false").lower() in ["1", "true", "sim"],
                    limit=query_param(query, "limit", "1000"),
                )})

            if acao == "buscarProcedimentosEmergencia":
                return responder(self, 200, {"sucesso": True, "dados": buscar_procedimentos_emergencia(
                    id_filial=query_param(query, "idFilial", ""),
                    tipo_maquina=query_param(query, "tipoMaquina", ""),
                    status=query_param(query, "status", "ATIVO"),
                    limit=query_param(query, "limit", "1000"),
                )})

            if acao == "buscarAnexosManutencao":
                return responder(self, 200, {"sucesso": True, "dados": buscar_anexos_manutencao(
                    origem_tabela=query_param(query, "origemTabela", ""),
                    origem_id=query_param(query, "origemId", ""),
                    tipo_anexo=query_param(query, "tipoAnexo", ""),
                    limit=query_param(query, "limit", "500"),
                )})

            if acao == "buscarAlertasPlanoManutencao":
                return responder(self, 200, {"sucesso": True, "dados": buscar_alertas_plano_manutencao(
                    query_param(query, "idFilial", ""),
                )})

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


            if acao == "salvarServicoManutencao":
                return responder(self, 200, {
                    "sucesso": True,
                    "dados": salvar_servico_manutencao(body.get("dados", body)),
                })

            if acao == "salvarPecaManutencao":
                return responder(self, 200, {
                    "sucesso": True,
                    "dados": salvar_peca_manutencao(body.get("dados", body)),
                })

            if acao == "salvarPecaDaMaquina":
                return responder(self, 200, {
                    "sucesso": True,
                    "dados": salvar_peca_da_maquina(body.get("dados", body)),
                })

            if acao == "registrarTrocaPeca":
                return responder(self, 200, {
                    "sucesso": True,
                    "dados": registrar_troca_peca(body.get("dados", body)),
                })

            if acao == "salvarApreciacaoNr12":
                return responder(self, 200, {
                    "sucesso": True,
                    "dados": salvar_apreciacao_nr12(body.get("dados", body)),
                })

            if acao == "salvarAcaoNr12":
                return responder(self, 200, {
                    "sucesso": True,
                    "dados": salvar_acao_nr12(body.get("dados", body)),
                })

            if acao == "salvarProcedimentoEmergencia":
                return responder(self, 200, {
                    "sucesso": True,
                    "dados": salvar_procedimento_emergencia(body.get("dados", body)),
                })

            if acao == "salvarAnexoManutencao":
                return responder(self, 200, {
                    "sucesso": True,
                    "dados": salvar_anexo_manutencao(body.get("dados", body)),
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
