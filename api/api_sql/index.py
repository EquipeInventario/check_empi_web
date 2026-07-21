from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime, date, timezone, timedelta
from zoneinfo import ZoneInfo
from calendar import monthrange
from decimal import Decimal
import json
import os
import re
import traceback

import pymysql
from pymysql.err import OperationalError


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
            "ultima_preventiva",
            "prox_preventiva",
        ],
        "bool_columns": ["adaptada_bobina", "possui_gdi"],
        "json_columns": [],
    },
    "preventivas": {
        "schema": "check_maquinas",
        "table": "preventivas",
        "pk": "id",
        "columns": [
            "id",
            "id_maquina",
            "codigo_maquina",
            "data_ultima_prev",
            "dias_prox_prev",
            "data_prox_prev",
            "descricao",
            "id_pecas",
            "pecas",
            "status",
            "responsavel",
            "observacao",
        ],
        "bool_columns": [],
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
    "check_paleteira": {
        "schema": "check_maquinas",
        "table": "check_paleteira",
        "pk": "id",
        "columns": [
            "id",
            "id_maquina",
            "codigo_maquina",
            "operador",
            "turno",
            "data_abertura",
            "data_finalizacao",
            "status_check",
            "resultado_check",
            "observacao_geral",
            "seg_garfos_estrutura",
            "seg_garfos_estrutura_obs",
            "seg_identificacao_capacidade",
            "seg_identificacao_capacidade_obs",
            "mec_rodas",
            "mec_rodas_obs",
            "mec_timao",
            "mec_timao_obs",
            "mec_vazamento_hidraulico",
            "mec_vazamento_hidraulico_obs",
            "ope_elevacao",
            "ope_elevacao_obs",
            "ope_descida",
            "ope_descida_obs",
            "ope_movimentacao",
            "ope_movimentacao_obs",
            "id_filial",
            "criado_em",
            "atualizado_em",
        ],
        "bool_columns": [],
        "json_columns": [],
    },
    "check_transpaleteira": {
        "schema": "check_maquinas",
        "table": "check_transpaleteira",
        "pk": "id",
        "columns": [
            "id",
            "id_maquina",
            "codigo_maquina",
            "operador",
            "turno",
            "data_abertura",
            "data_finalizacao",
            "horimetro_inicial",
            "horimetro_final",
            "status_check",
            "resultado_check",
            "observacao_geral",
            "seg_garfos_estrutura",
            "seg_garfos_estrutura_obs",
            "seg_buzina",
            "seg_buzina_obs",
            "seg_botao_emergencia",
            "seg_botao_emergencia_obs",
            "seg_antiesmagamento",
            "seg_antiesmagamento_obs",
            "mec_rodas",
            "mec_rodas_obs",
            "mec_bateria_conectores",
            "mec_bateria_conectores_obs",
            "ope_timao_comandos",
            "ope_timao_comandos_obs",
            "ope_freio",
            "ope_freio_obs",
            "ope_elevacao_descida",
            "ope_elevacao_descida_obs",
            "ope_painel_indicadores",
            "ope_painel_indicadores_obs",
            "id_filial",
            "carga_inicial",
            "carga_final",
            "ultima_carga_realizada",
            "criado_em",
            "atualizado_em",
        ],
        "bool_columns": [],
        "json_columns": [],
    },
    "check_limpeza": {
        "schema": "check_maquinas",
        "table": "check_limpeza",
        "pk": "id",
        "columns": [
            "id",
            "id_maquina",
            "codigo_maquina",
            "operador",
            "turno",
            "data_abertura",
            "data_finalizacao",
            "horimetro_inicial",
            "horimetro_final",
            "status_check",
            "resultado_check",
            "observacao_geral",
            "seg_freio",
            "seg_freio_obs",
            "seg_sinalizacao_alarme",
            "seg_sinalizacao_alarme_obs",
            "mec_escovas_discos",
            "mec_escovas_discos_obs",
            "mec_rodo_succao",
            "mec_rodo_succao_obs",
            "mec_mangueiras_vazamentos",
            "mec_mangueiras_vazamentos_obs",
            "mec_tanques",
            "mec_tanques_obs",
            "mec_bateria_conectores",
            "mec_bateria_conectores_obs",
            "ope_aspiracao",
            "ope_aspiracao_obs",
            "ope_tracao_direcao",
            "ope_tracao_direcao_obs",
            "ope_comandos_painel",
            "ope_comandos_painel_obs",
            "id_filial",
            "carga_inicial",
            "carga_final",
            "ultima_carga_realizada",
            "criado_em",
            "atualizado_em",
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
            "origem_check",
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
            "entrada_oficina",
            "tempo_manutencao",
            "saida_oficina",
            "horimetro_servico",
            "descricao_servico",
            "condicoes_seguranca",
            "responsavel_execucao",
            "responsavel_liberacao",
            "resultado_liberacao",
            "observacao_liberacao",
            "tempo_parada_minutos",
            "status_servico",
            "plano_acao_json",
            "criado_por",
            "criado_em",
            "atualizado_em",
        ],
        "bool_columns": [],
        "json_columns": ["plano_acao_json"],
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
            "tipo_maquina",
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
            "vida_util_dias",
            "data_ultima_troca",
            "horimetro_ultima_troca",
            "proxima_troca_data",
            "alerta_antecedencia_dias",
            "status",
            "observacao",
            "criado_em",
            "atualizado_em",
            "id_filial",
            "id_check_mec",
            "motivo_troca",
        ],
        "bool_columns": [],
        "json_columns": [],
    },
    "check_mecanica": {
        "schema": "check_maquinas",
        "table": "check_mecanica",
        "pk": "id",
        "columns": [
            "id",
            "id_servico",
            "status_check",
            "resultado_check",
            "observacao_geral",
            "exec_servico_executado",
            "exec_servico_executado_obs",
            "org_equipamento_limpo",
            "org_equipamento_limpo_obs",
            "seg_sem_vazamentos",
            "seg_sem_vazamentos_obs",
            "seg_freio_testado",
            "seg_freio_testado_obs",
            "ope_direcao_movimentacao",
            "ope_direcao_movimentacao_obs",
            "ope_comandos_principais",
            "ope_comandos_principais_obs",
            "seg_dispositivos_seguranca",
            "seg_dispositivos_seguranca_obs",
            "seg_protecoes_tampas",
            "seg_protecoes_tampas_obs",
            "seg_condicoes_liberacao",
            "seg_condicoes_liberacao_obs",
            "ris_risco_residual",
            "ris_risco_residual_obs",
            "lib_condicao_segura",
            "lib_condicao_segura_obs",
            "emp_torre_testada",
            "emp_torre_testada_obs",
            "emp_correntes_verificadas",
            "emp_correntes_verificadas_obs",
            "emp_garfos_verificados",
            "emp_garfos_verificados_obs",
            "emp_elevacao_descida_testadas",
            "emp_elevacao_descida_testadas_obs",
            "emp_inclinacao_testada",
            "emp_inclinacao_testada_obs",
            "emp_alarme_re_testado",
            "emp_alarme_re_testado_obs",
            "emp_giroflex_sinalizacao_testados",
            "emp_giroflex_sinalizacao_testados_obs",
            "emp_cinto_seguranca_verificado",
            "emp_cinto_seguranca_verificado_obs",
            "emp_espelhos_extintor_verificados",
            "emp_espelhos_extintor_verificados_obs",
            "pal_timao_testado",
            "pal_timao_testado_obs",
            "pal_rodas_carga_verificadas",
            "pal_rodas_carga_verificadas_obs",
            "pal_rodas_direcionais_verificadas",
            "pal_rodas_direcionais_verificadas_obs",
            "pal_sistema_elevacao_testado",
            "pal_sistema_elevacao_testado_obs",
            "pal_sistema_descida_testado",
            "pal_sistema_descida_testado_obs",
            "pal_botao_emergencia_testado",
            "pal_botao_emergencia_testado_obs",
            "pal_cabo_conector_bateria_verificados",
            "pal_cabo_conector_bateria_verificados_obs",
            "criado_em",
            "atualizado_em",
        ],
        "bool_columns": [],
        "json_columns": [],
    },
    "check_mecanica_lavadora": {
        "schema": "check_maquinas",
        "table": "check_mecanica_lavadora",
        "pk": "id",
        "columns": [
            "id",
            "id_servico",
            "status_check",
            "resultado_check",
            "observacao_geral",
            "exec_servico_executado",
            "exec_servico_executado_obs",
            "org_equipamento_limpo",
            "org_equipamento_limpo_obs",
            "seg_sem_vazamentos",
            "seg_sem_vazamentos_obs",
            "seg_freio_testado",
            "seg_freio_testado_obs",
            "ope_direcao_movimentacao",
            "ope_direcao_movimentacao_obs",
            "ope_comandos_principais",
            "ope_comandos_principais_obs",
            "seg_dispositivos_seguranca",
            "seg_dispositivos_seguranca_obs",
            "seg_protecoes_tampas",
            "seg_protecoes_tampas_obs",
            "seg_condicoes_liberacao",
            "seg_condicoes_liberacao_obs",
            "ris_risco_residual",
            "ris_risco_residual_obs",
            "lib_condicao_segura",
            "lib_condicao_segura_obs",
            "lav_escovas_discos_verificados",
            "lav_escovas_discos_verificados_obs",
            "lav_rodo_succao_verificado",
            "lav_rodo_succao_verificado_obs",
            "lav_sistema_aspiracao_testado",
            "lav_sistema_aspiracao_testado_obs",
            "lav_tanque_agua_limpa_verificado",
            "lav_tanque_agua_limpa_verificado_obs",
            "lav_tanque_recuperacao_verificado",
            "lav_tanque_recuperacao_verificado_obs",
            "lav_mangueiras_conexoes_verificadas",
            "lav_mangueiras_conexoes_verificadas_obs",
            "lav_sistema_dosagem_verificado",
            "lav_sistema_dosagem_verificado_obs",
            "lav_bateria_cabos_conectores_verificados",
            "lav_bateria_cabos_conectores_verificados_obs",
            "lav_carregador_bateria_verificado",
            "lav_carregador_bateria_verificado_obs",
            "lav_rodas_pneus_verificados",
            "lav_rodas_pneus_verificados_obs",
            "lav_tracao_freio_testados",
            "lav_tracao_freio_testados_obs",
            "lav_sinalizacao_alarme_re_testados",
            "lav_sinalizacao_alarme_re_testados_obs",
            "lav_elevacao_escova_rodo_testada",
            "lav_elevacao_escova_rodo_testada_obs",
            "criado_em",
            "atualizado_em",
        ],
        "bool_columns": [],
        "json_columns": [],
    },
    "check_mecanica_paleteira": {
        "schema": "check_maquinas",
        "table": "check_mecanica_paleteira",
        "pk": "id",
        "columns": [
            "id",
            "id_servico",
            "status_check",
            "resultado_check",
            "observacao_geral",
            "exec_servico_executado",
            "exec_servico_executado_obs",
            "org_equipamento_limpo",
            "org_equipamento_limpo_obs",
            "seg_sem_vazamentos",
            "seg_sem_vazamentos_obs",
            "seg_condicoes_liberacao",
            "seg_condicoes_liberacao_obs",
            "ris_risco_residual",
            "ris_risco_residual_obs",
            "lib_condicao_segura",
            "lib_condicao_segura_obs",
            "pal_timao_testado",
            "pal_timao_testado_obs",
            "pal_garfos_estrutura_verificados",
            "pal_garfos_estrutura_verificados_obs",
            "pal_rodas_carga_verificadas",
            "pal_rodas_carga_verificadas_obs",
            "pal_rodas_direcionais_verificadas",
            "pal_rodas_direcionais_verificadas_obs",
            "pal_sistema_elevacao_testado",
            "pal_sistema_elevacao_testado_obs",
            "pal_sistema_descida_testado",
            "pal_sistema_descida_testado_obs",
            "pal_bomba_hidraulica_verificada",
            "pal_bomba_hidraulica_verificada_obs",
            "pal_valvula_descida_verificada",
            "pal_valvula_descida_verificada_obs",
            "pal_identificacao_capacidade_legivel",
            "pal_identificacao_capacidade_legivel_obs",
            "criado_em",
            "atualizado_em",
        ],
        "bool_columns": [],
        "json_columns": [],
    },
    "check_mecanica_transpaleteira": {
        "schema": "check_maquinas",
        "table": "check_mecanica_transpaleteira",
        "pk": "id",
        "columns": [
            "id",
            "id_servico",
            "status_check",
            "resultado_check",
            "observacao_geral",
            "exec_servico_executado",
            "exec_servico_executado_obs",
            "org_equipamento_limpo",
            "org_equipamento_limpo_obs",
            "seg_sem_vazamentos",
            "seg_sem_vazamentos_obs",
            "seg_freio_testado",
            "seg_freio_testado_obs",
            "ope_direcao_movimentacao",
            "ope_direcao_movimentacao_obs",
            "ope_comandos_principais",
            "ope_comandos_principais_obs",
            "seg_dispositivos_seguranca",
            "seg_dispositivos_seguranca_obs",
            "seg_protecoes_tampas",
            "seg_protecoes_tampas_obs",
            "seg_condicoes_liberacao",
            "seg_condicoes_liberacao_obs",
            "ris_risco_residual",
            "ris_risco_residual_obs",
            "lib_condicao_segura",
            "lib_condicao_segura_obs",
            "tra_timao_comandos_testados",
            "tra_timao_comandos_testados_obs",
            "tra_botao_emergencia_testado",
            "tra_botao_emergencia_testado_obs",
            "tra_botao_antiesmagamento_testado",
            "tra_botao_antiesmagamento_testado_obs",
            "tra_buzina_testada",
            "tra_buzina_testada_obs",
            "tra_freio_servico_estacionamento_testado",
            "tra_freio_servico_estacionamento_testado_obs",
            "tra_rodas_carga_verificadas",
            "tra_rodas_carga_verificadas_obs",
            "tra_roda_tracao_verificada",
            "tra_roda_tracao_verificada_obs",
            "tra_garfos_estrutura_verificados",
            "tra_garfos_estrutura_verificados_obs",
            "tra_sistema_elevacao_testado",
            "tra_sistema_elevacao_testado_obs",
            "tra_sistema_descida_testado",
            "tra_sistema_descida_testado_obs",
            "tra_bateria_cabos_conectores_verificados",
            "tra_bateria_cabos_conectores_verificados_obs",
            "tra_carregador_bateria_verificado",
            "tra_carregador_bateria_verificado_obs",
            "tra_indicador_carga_painel_testado",
            "tra_indicador_carga_painel_testado_obs",
            "criado_em",
            "atualizado_em",
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
    "origem_check",
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


try:
    FUSO_OPERACIONAL = ZoneInfo("America/Sao_Paulo")
except Exception:
    # Fallback seguro para o fuso atual de Brasília caso o ambiente
    # serverless não possua a base IANA de fusos instalada.
    FUSO_OPERACIONAL = timezone(timedelta(hours=-3))


def agora_local():
    """Retorna o horário operacional de São Paulo sem tzinfo para MySQL DATETIME."""
    return datetime.now(FUSO_OPERACIONAL).replace(tzinfo=None)


def agora_mysql():
    return agora_local().strftime("%Y-%m-%d %H:%M:%S")


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


def normalizar_data_mysql(valor):
    if valor in [None, ""]:
        return valor
    if isinstance(valor, (datetime, date)):
        if isinstance(valor, date) and not isinstance(valor, datetime):
            return valor.strftime("%Y-%m-%d")
        return valor.strftime("%Y-%m-%d %H:%M:%S")

    texto = str(valor).strip()
    if not texto:
        return texto

    # A interface usa o padrão brasileiro e a API converte antes do MySQL.
    br_data_hora = re.match(
        r"^(\d{2})/(\d{2})/(\d{4})\s+(\d{2}):(\d{2})(?::(\d{2}))?$",
        texto,
    )
    if br_data_hora:
        dia, mes, ano, hora, minuto, segundo = br_data_hora.groups()
        segundo = segundo or "00"
        data_validada = datetime(
            int(ano), int(mes), int(dia), int(hora), int(minuto), int(segundo)
        )
        return data_validada.strftime("%Y-%m-%d %H:%M:%S")

    br_data = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", texto)
    if br_data:
        dia, mes, ano = br_data.groups()
        data_validada = date(int(ano), int(mes), int(dia))
        return data_validada.strftime("%Y-%m-%d")

    texto = texto.replace("T", " ")
    if texto.endswith("Z"):
        texto = texto[:-1]
    if "." in texto:
        texto = texto.split(".", 1)[0]
    # YYYY-MM-DD HH:MM -> YYYY-MM-DD HH:MM:SS
    if re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$", texto):
        return texto + ":00"
    return texto


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

    if coluna.startswith("data_") or coluna.endswith("_em") or coluna in [
        "ultima_manutencao",
        "ultimo_reg_horimetro",
        "entrada_oficina",
        "saida_oficina",
        "ultima_preventiva",
        "prox_preventiva",
        "ultima_carga_realizada",
    ]:
        return normalizar_data_mysql(valor)

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
    if nome_tabela in [
        "check_empi",
        "check_paleteira",
        "check_transpaleteira",
        "check_limpeza",
    ]:
        dados.setdefault("data_abertura", agora_mysql())
        dados.setdefault("criado_em", agora_mysql())
    elif nome_tabela in [
        "check_empi_pendencias",
        "check_empi_anexos",
        "usuarios_web_check",
        "manutencao_servicos",
        "manutencao_pecas",
        "manutencao_maquina_pecas",
        "check_mecanica",
        "check_mecanica_lavadora",
        "check_mecanica_paleteira",
        "check_mecanica_transpaleteira",
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



# ============================================================
# CHECKLISTS DO OPERADOR - MÁQUINAS AUXILIARES
# ============================================================

CHECKS_OPERADOR_AUXILIARES = {
    "PLT_MANUAL": "check_paleteira",
    "PLT_ELETRICA": "check_transpaleteira",
    "LIMPEZA": "check_limpeza",
}


def _normalizar_texto_auxiliar(valor):
    texto = str(valor or "").strip().upper()
    substituicoes = {
        "Á": "A", "À": "A", "Â": "A", "Ã": "A",
        "É": "E", "Ê": "E",
        "Í": "I",
        "Ó": "O", "Ô": "O", "Õ": "O",
        "Ú": "U",
        "Ç": "C",
    }
    for origem, destino in substituicoes.items():
        texto = texto.replace(origem, destino)
    return texto.replace("_", "-").replace(" ", "-")


def identificar_tipo_check_operador(
    tipo_checklist="",
    codigo_maquina="",
    tipo_maquina="",
):
    """
    Resolve qual checklist diário deve ser usado.

    REGRA:
    - codigo_maquina é somente o número/código de frota e NÃO participa
      da classificação.
    - quando tipo_checklist vier explícito do app, ele é respeitado;
    - caso contrário, a classificação é feita somente por tipo_maquina.

    Mapeamento:
      EMPILHADEIRA   -> fluxo legado check_empi (não entra aqui)
      TRANSPALETEIRA -> PLT_ELETRICA / check_transpaleteira
      PALETEIRA      -> PLT_MANUAL / check_paleteira
      AUXILIAR       -> LIMPEZA / check_limpeza
    """
    tipo_explicitado = _normalizar_texto_auxiliar(tipo_checklist)
    tipo_cadastro = _normalizar_texto_auxiliar(tipo_maquina)

    # Tipo explícito enviado pela aplicação.
    if tipo_explicitado in {
        "PLT-MANUAL",
        "PALETEIRA",
        "PALETEIRA-MANUAL",
    }:
        return "PLT_MANUAL"

    if tipo_explicitado in {
        "PLT-ELETRICA",
        "PLT-ELETRICA",
        "TRANSPALETEIRA",
        "TRANSPALETEIRA-ELETRICA",
        "PALETEIRA-ELETRICA",
    }:
        return "PLT_ELETRICA"

    if tipo_explicitado in {
        "LIMP",
        "AUXILIAR",
        "LIMPEZA",
        "LAVADORA",
        "MAQUINA-DE-LIMPEZA",
    }:
        return "LIMPEZA"

    # Fallback permitido: somente o campo tipo_maquina do cadastro.
    if tipo_cadastro == "PALETEIRA":
        return "PLT_MANUAL"

    if tipo_cadastro == "TRANSPALETEIRA":
        return "PLT_ELETRICA"

    if tipo_cadastro == "AUXILIAR":
        return "LIMPEZA"

    return ""


def _tabela_check_operador_auxiliar(
    tipo_checklist="",
    codigo_maquina="",
    tipo_maquina="",
):
    tipo = identificar_tipo_check_operador(
        tipo_checklist=tipo_checklist,
        codigo_maquina=codigo_maquina,
        tipo_maquina=tipo_maquina,
    )
    tabela = CHECKS_OPERADOR_AUXILIARES.get(tipo)
    if not tabela:
        raise ValueError(
            "Tipo de checklist auxiliar não reconhecido. "
            "Use PLT-MANUAL, PLT-ELETRICA ou LIMP."
        )
    return tipo, tabela


def buscar_checks_operador_auxiliar(
    tipo_checklist="",
    codigo_maquina="",
    tipo_maquina="",
    id_filial="",
    status_check="",
    operador="",
    limit=500,
):
    tipo, tabela = _tabela_check_operador_auxiliar(
        tipo_checklist=tipo_checklist,
        codigo_maquina=codigo_maquina,
        tipo_maquina=tipo_maquina,
    )

    filtros = {}
    if codigo_maquina:
        filtros["codigo_maquina"] = codigo_maquina
    if possui_filial(id_filial):
        filtros["id_filial"] = id_filial
    if str(status_check or "").strip():
        filtros["status_check"] = status_check
    if str(operador or "").strip():
        filtros["operador"] = operador

    rows = selecionar(
        tabela,
        filtros=filtros,
        order_by="data_abertura",
        ascending=False,
        limit=limit,
    )

    for row in rows:
        row["tipo_checklist"] = tipo
        row["tabela_checklist"] = tabela

    return rows


def buscar_check_operador_auxiliar_por_id(
    id_check,
    tipo_checklist="",
    codigo_maquina="",
    tipo_maquina="",
    id_filial="",
):
    tipo, tabela = _tabela_check_operador_auxiliar(
        tipo_checklist=tipo_checklist,
        codigo_maquina=codigo_maquina,
        tipo_maquina=tipo_maquina,
    )

    filtros = {"id": id_check}
    if possui_filial(id_filial):
        filtros["id_filial"] = id_filial

    row = selecionar_um(tabela, filtros=filtros)
    if row:
        row["tipo_checklist"] = tipo
        row["tabela_checklist"] = tabela
    return row


def salvar_check_operador_auxiliar(
    tipo_checklist,
    dados_check,
    tipo_maquina="",
):
    """
    Salva o checklist diário na tabela correspondente.

    Não interfere no fluxo existente de check_empi.
    A máquina é marcada como "Em uso" quando encontrada no cadastro.
    """
    dados = dict(dados_check or {})
    codigo = (
        dados.get("codigo_maquina")
        or dados.get("codigoMaquina")
        or ""
    )

    tipo, tabela = _tabela_check_operador_auxiliar(
        tipo_checklist=tipo_checklist,
        codigo_maquina=codigo,
        tipo_maquina=tipo_maquina,
    )

    if not str(codigo or "").strip():
        raise ValueError("Informe codigo_maquina para salvar o checklist.")
    if not str(dados.get("operador") or "").strip():
        raise ValueError("Informe operador para salvar o checklist.")

    # Compatibilidade com payload camelCase.
    dados["codigo_maquina"] = codigo
    dados.pop("codigoMaquina", None)

    if "idMaquina" in dados and "id_maquina" not in dados:
        dados["id_maquina"] = dados.pop("idMaquina")
    if "idFilial" in dados and "id_filial" not in dados:
        dados["id_filial"] = dados.pop("idFilial")
    if "statusCheck" in dados and "status_check" not in dados:
        dados["status_check"] = dados.pop("statusCheck")
    if "resultadoCheck" in dados and "resultado_check" not in dados:
        dados["resultado_check"] = dados.pop("resultadoCheck")
    if "observacaoGeral" in dados and "observacao_geral" not in dados:
        dados["observacao_geral"] = dados.pop("observacaoGeral")
    if "horimetroInicial" in dados and "horimetro_inicial" not in dados:
        dados["horimetro_inicial"] = dados.pop("horimetroInicial")
    if "cargaInicial" in dados and "carga_inicial" not in dados:
        dados["carga_inicial"] = dados.pop("cargaInicial")

    dados.setdefault("status_check", "ABERTO")

    agora = agora_mysql()

    with conectar() as conn:
        try:
            check = inserir(tabela, dados, conn=conn)

            id_filial = dados.get("id_filial")
            maquina = None
            with conn.cursor() as cur:
                sql = """
                    SELECT *
                    FROM `check_maquinas`.`maquinas`
                    WHERE CONVERT(`codigo` USING utf8mb4) COLLATE utf8mb4_unicode_ci
                        = CONVERT(%s USING utf8mb4) COLLATE utf8mb4_unicode_ci
                """
                params = [codigo]
                if possui_filial(id_filial):
                    sql += " AND `id_filial` = %s"
                    params.append(id_filial)
                sql += " ORDER BY `id` DESC LIMIT 1"
                cur.execute(sql, params)
                maquina = cur.fetchone()

            if maquina:
                dados_maquina = {
                    "ativo": "Em uso",
                }

                horimetro = dados.get("horimetro_inicial")
                if horimetro not in [None, ""]:
                    dados_maquina["horimetro_atual"] = horimetro
                    dados_maquina["ultimo_reg_horimetro"] = agora

                carga = dados.get("carga_inicial")
                if carga not in [None, ""]:
                    dados_maquina["carga_atual"] = carga

                filtros_maquina = {"codigo": maquina.get("codigo")}
                if possui_filial(maquina.get("id_filial")):
                    filtros_maquina["id_filial"] = maquina.get("id_filial")

                atualizar(
                    "maquinas",
                    dados_maquina,
                    filtros_maquina,
                    conn=conn,
                )

            conn.commit()

            return {
                "tipo_checklist": tipo,
                "tabela_checklist": tabela,
                "check": check,
                "id_check": check.get("id"),
            }
        except Exception:
            conn.rollback()
            raise


def finalizar_check_operador_auxiliar(
    tipo_checklist,
    id_check,
    codigo_maquina,
    id_filial="",
    tipo_maquina="",
    horimetro_final=None,
    carga_final=None,
    ultima_carga_realizada=None,
):
    """
    Finaliza um checklist auxiliar.

    Diferente do check_empi, horímetro NÃO é obrigatório:
    - PLT-MANUAL não usa horímetro;
    - PLT-ELETRICA e LIMP podem usar quando o equipamento possuir.
    """
    tipo, tabela = _tabela_check_operador_auxiliar(
        tipo_checklist=tipo_checklist,
        codigo_maquina=codigo_maquina,
        tipo_maquina=tipo_maquina,
    )

    if id_check in [None, ""]:
        raise ValueError("Informe idCheck para finalizar o checklist.")
    if not str(codigo_maquina or "").strip():
        raise ValueError("Informe codigoMaquina para finalizar o checklist.")

    agora = agora_mysql()

    dados_check = {
        "status_check": "FINALIZADO",
        "data_finalizacao": agora,
        "atualizado_em": agora,
    }

    cfg = cfg_tabela(tabela)
    colunas = set(cfg["columns"])

    if "horimetro_final" in colunas and horimetro_final not in [None, ""]:
        dados_check["horimetro_final"] = horimetro_final
    if "carga_final" in colunas and carga_final not in [None, ""]:
        dados_check["carga_final"] = carga_final
    if (
        "ultima_carga_realizada" in colunas
        and ultima_carga_realizada not in [None, ""]
    ):
        dados_check["ultima_carga_realizada"] = ultima_carga_realizada

    with conectar() as conn:
        try:
            filtros_check = {"id": id_check}
            if possui_filial(id_filial):
                filtros_check["id_filial"] = id_filial

            atualizado = atualizar(
                tabela,
                dados_check,
                filtros_check,
                conn=conn,
            )

            # A existência de qualquer pendência aberta para o código da máquina
            # continua impedindo liberação automática, independentemente do tipo.
            with conn.cursor() as cur:
                sql_pend = """
                    SELECT `id`
                    FROM `check_maquinas`.`check_empi_pendencias`
                    WHERE CONVERT(`empilhadeira` USING utf8mb4)
                              COLLATE utf8mb4_unicode_ci
                          = CONVERT(%s USING utf8mb4)
                              COLLATE utf8mb4_unicode_ci
                      AND `status_pendencia` IN ('ABERTA', 'EM_ANALISE')
                      AND (`resolvido` = 0 OR `resolvido` IS NULL)
                """
                params_pend = [codigo_maquina]
                if possui_filial(id_filial):
                    sql_pend += " AND `id_filial` = %s"
                    params_pend.append(id_filial)
                sql_pend += " LIMIT 1"
                cur.execute(sql_pend, params_pend)
                possui_pendencia = cur.fetchone() is not None

            dados_maquina = {
                "ativo": "Manutenção" if possui_pendencia else "Liberado",
            }
            if horimetro_final not in [None, ""]:
                dados_maquina["horimetro_atual"] = horimetro_final
                dados_maquina["ultimo_reg_horimetro"] = agora
            if carga_final not in [None, ""]:
                dados_maquina["carga_atual"] = carga_final
            if ultima_carga_realizada not in [None, ""]:
                dados_maquina["ultima_carga_realizada"] = normalizar_data_mysql(
                    ultima_carga_realizada
                )

            filtros_maquina = {"codigo": codigo_maquina}
            if possui_filial(id_filial):
                filtros_maquina["id_filial"] = id_filial

            resultado_maquina = atualizar(
                "maquinas",
                dados_maquina,
                filtros_maquina,
                conn=conn,
            )

            conn.commit()

            return {
                "tipo_checklist": tipo,
                "tabela_checklist": tabela,
                "check_finalizado": True,
                "check": atualizado,
                "maquina": resultado_maquina,
                "maquina_liberada": not possui_pendencia,
                "possui_pendencia_manutencao": possui_pendencia,
            }
        except Exception:
            conn.rollback()
            raise


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
    # Rota legada: sempre se refere ao checklist de empilhadeira.
    return selecionar(
        "check_empi_anexos",
        filtros={
            "id_check": id_check,
            "origem_check": "check_empi",
        },
        order_by="criado_em",
        ascending=False,
        colunas=ANEXOS_SELECT,
    )


def buscar_anexos_por_empilhadeira(empilhadeira):
    # Rota legada: preserva somente anexos originados de check_empi.
    return selecionar(
        "check_empi_anexos",
        filtros={
            "empilhadeira": empilhadeira,
            "origem_check": "check_empi",
        },
        order_by="criado_em",
        ascending=False,
        colunas=ANEXOS_SELECT,
    )


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
# ANEXOS GERAIS DOS CHECKLISTS DO OPERADOR
#
# Usa exclusivamente a tabela existente check_empi_anexos.
# A coluna origem_check diferencia a tabela de checklist:
#   check_empi
#   check_paleteira
#   check_transpaleteira
#   check_limpeza
# ============================================================

ORIGENS_CHECK_OPERADOR = {
    "check_empi",
    "check_paleteira",
    "check_transpaleteira",
    "check_limpeza",
}


def buscar_anexos_operador(origem_tabela, origem_id):
    origem = _valor_texto(origem_tabela)
    if origem not in ORIGENS_CHECK_OPERADOR:
        raise ValueError("origemTabela inválida para buscar anexos.")
    if origem_id in [None, ""]:
        raise ValueError("Informe origemId para buscar os anexos.")

    return selecionar(
        "check_empi_anexos",
        filtros={
            "origem_check": origem,
            "id_check": origem_id,
        },
        order_by="criado_em",
        ascending=True,
        limit=2000,
        colunas=ANEXOS_SELECT,
    )


def inserir_anexo_operador(dados):
    """
    Insere mídia de qualquer checklist do operador em check_empi_anexos.

    Aceita tanto o payload novo:
      origem_check, id_check, empilhadeira

    quanto o payload da versão intermediária anterior:
      origem_tabela, origem_id, codigo_maquina

    Isso evita quebra durante a transição entre versões do app.
    """
    entrada = dict(dados or {})

    origem = _valor_texto(
        entrada.get("origem_check")
        or entrada.get("origem_tabela")
    )
    id_check = (
        entrada.get("id_check")
        if entrada.get("id_check") not in [None, ""]
        else entrada.get("origem_id")
    )
    codigo = _valor_texto(
        entrada.get("empilhadeira")
        or entrada.get("codigo_maquina")
    )

    if origem not in ORIGENS_CHECK_OPERADOR:
        raise ValueError("origem_check inválida para anexo de checklist.")
    if id_check in [None, ""]:
        raise ValueError("Informe id_check para o anexo.")
    if not codigo:
        raise ValueError("Informe o código/número de frota da máquina.")

    registro = {
        "id_check": id_check,
        "origem_check": origem,
        "empilhadeira": codigo,
        "categoria": entrada.get("categoria") or "CHECKLIST",
        "item": entrada.get("item") or "MIDIA_GERAL",
        "caminho_arquivo": entrada.get("caminho_arquivo"),
        "url_publica": entrada.get("url_publica"),
        "tamanho_bytes": entrada.get("tamanho_bytes"),
        "criado_por": entrada.get("criado_por"),
        "criado_em": entrada.get("criado_em") or agora_mysql(),
        "storage_origem": entrada.get("storage_origem"),
        "container_azure": entrada.get("container_azure"),
        "blob_azure": entrada.get("blob_azure"),
        "url_azure": entrada.get("url_azure"),
    }

    # Como o upload novo já vai direto ao Azure, marca o registro como
    # armazenado/migrado quando houver referência Azure.
    if registro.get("url_azure") or registro.get("blob_azure"):
        registro["migrado_azure"] = 1
        registro["migrado_em"] = agora_mysql()

    # Remove apenas chaves totalmente ausentes; mantém zero em tamanho_bytes.
    registro = {
        chave: valor
        for chave, valor in registro.items()
        if valor is not None
    }

    return inserir("check_empi_anexos", registro)


def inserir_anexo_check_empi(dados):
    """Compatibilidade com o fluxo legado de anexos da empilhadeira."""
    registro = dict(dados or {})
    registro["origem_check"] = "check_empi"
    return inserir("check_empi_anexos", registro)


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
    ultima_preventiva=None,
    proxima_preventiva=None,
):
    """Atualiza o calendário mensal da preventiva da máquina.

    O horímetro continua sendo armazenado no cadastro e nos serviços apenas
    como informação operacional. O vencimento da preventiva passa a depender
    exclusivamente de ultima_preventiva e prox_preventiva.
    """
    codigo = _valor_texto(codigo_maquina)
    if not codigo:
        raise ValueError("Informe codigoMaquina para atualizar a preventiva.")

    ultima = _valor_data(ultima_preventiva)
    proxima = _valor_data(proxima_preventiva)

    if ultima and not proxima:
        proxima_iso = _somar_meses(ultima, 1)
        proxima = _valor_data(proxima_iso)

    if not ultima and not proxima:
        raise ValueError("Informe ultimaPreventiva ou proximaPreventiva.")

    if ultima and proxima and proxima.date() <= ultima.date():
        raise ValueError("A próxima preventiva deve ser posterior à última preventiva.")

    dados = {}
    if ultima:
        dados["ultima_preventiva"] = ultima.date().isoformat()
    if proxima:
        dados["prox_preventiva"] = proxima.date().isoformat()

    filtros = {"codigo": codigo}
    if possui_filial(id_filial):
        filtros["id_filial"] = id_filial

    resultado = atualizar("maquinas", dados, filtros)

    maquina = _buscar_maquina_para_preventiva(codigo, id_filial=id_filial)
    dias = _dias_ate_preventiva(proxima)
    status = "VENCIDA" if dias is not None and dias < 0 else "PROGRAMADA"
    salvar_historico_preventiva({
        "id_maquina": (maquina or {}).get("id_maquina") or (maquina or {}).get("id"),
        "codigo_maquina": codigo,
        "data_ultima_prev": ultima.date().isoformat() if ultima else (maquina or {}).get("ultima_preventiva"),
        "data_prox_prev": proxima.date().isoformat() if proxima else (maquina or {}).get("prox_preventiva"),
        "dias_prox_prev": dias,
        "descricao": "Programação preventiva mensal",
        "status": status,
    })

    return resultado


def finalizar_turno(
    id_check,
    codigo_maquina,
    id_filial,
    horimetro_final,
    carga_final=None,
    ultima_carga_realizada=None,
):
    """Finaliza um check aberto do app mobile sem quebrar o fluxo antigo.

    Esta ação é usada diretamente pelo app do operador. Por isso ela precisa
    ser conservadora: primeiro fecha o check_empi com os campos essenciais e
    depois atualiza a máquina. Os campos de bateria/carga são opcionais e não
    podem impedir a finalização do turno caso alguma base ainda esteja sem
    esses campos.
    """
    if id_check in [None, ""]:
        raise ValueError("Informe idCheck para finalizar o turno.")
    if not _valor_texto(codigo_maquina):
        raise ValueError("Informe codigoMaquina para finalizar o turno.")
    if id_filial in [None, ""]:
        raise ValueError("Informe idFilial para finalizar o turno.")
    if horimetro_final in [None, ""]:
        raise ValueError("Informe horimetroFinal para finalizar o turno.")

    agora = agora_mysql()

    with conectar() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT `id`, `horimetro_inicial`
                    FROM `check_maquinas`.`check_empi`
                    WHERE `id` = %s
                    LIMIT 1
                    """,
                    [id_check],
                )
                check = cur.fetchone()
                if not check:
                    raise ValueError(f"Check não encontrado para finalização: {id_check}")

                cur.execute(
                    """
                    SELECT `id`
                    FROM `check_maquinas`.`check_empi_pendencias`
                    WHERE `empilhadeira` = %s
                      AND `id_filial` = %s
                      AND `status_pendencia` IN ('ABERTA', 'EM_ANALISE')
                      AND (`resolvido` = 0 OR `resolvido` IS NULL)
                    LIMIT 1
                    """,
                    [codigo_maquina, id_filial],
                )
                possui_pendencia = cur.fetchone() is not None

            # Mantém o fechamento do check igual ao fluxo original do mobile.
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

            dados_maquina_base = {
                "ativo": "Manutenção" if possui_pendencia else "Liberado",
                "horimetro_atual": horimetro_final,
                "ultimo_reg_horimetro": agora,
            }
            dados_maquina = dict(dados_maquina_base)

            if carga_final not in [None, ""]:
                dados_maquina["carga_atual"] = carga_final
            if ultima_carga_realizada not in [None, ""]:
                dados_maquina["ultima_carga_realizada"] = normalizar_data_mysql(
                    ultima_carga_realizada
                )

            try:
                atualizar(
                    "maquinas",
                    dados_maquina,
                    {"codigo": codigo_maquina, "id_filial": id_filial},
                    conn=conn,
                )
            except OperationalError as exc:
                # Se alguma base ainda não tiver os campos novos de carga,
                # não bloqueia a finalização do turno. Reaplica somente o
                # fechamento operacional da máquina.
                mensagem = str(exc).lower()
                if "carga_atual" in mensagem or "ultima_carga_realizada" in mensagem or "unknown column" in mensagem:
                    atualizar(
                        "maquinas",
                        dados_maquina_base,
                        {"codigo": codigo_maquina, "id_filial": id_filial},
                        conn=conn,
                    )
                else:
                    raise

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
                        "ativo": "Em Uso/Precisa Manutenção" if pendencias_salvas else "Em uso",
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




# ============================================================
# HISTÓRICO DE PREVENTIVAS
# ============================================================

_PREVENTIVA_STATUS_FECHADOS = {
    "CONCLUIDA",
    "CONCLUÍDA",
    "FINALIZADA",
    "FINALIZADO",
    "CORRIGIDA",
    "CORRIGIDO",
    "CANCELADA",
    "CANCELADO",
}


def _texto_preventiva(valor, limite=45):
    texto = _valor_texto(valor)
    if not texto:
        return None
    return texto[:limite]


def _status_preventiva(valor, padrao="PROGRAMADA"):
    texto = _valor_texto(valor or padrao).upper().replace(" ", "_")
    aliases = {
        "EM_MANUTENÇÃO": "EM_MANUTENCAO",
        "EM MANUTENÇÃO": "EM_MANUTENCAO",
        "EM MANUTENCAO": "EM_MANUTENCAO",
        "CONCLUÍDA": "CONCLUIDA",
        "FINALIZADA": "CONCLUIDA",
        "FINALIZADO": "CONCLUIDA",
        "CORRIGIDA": "CONCLUIDA",
        "CORRIGIDO": "CONCLUIDA",
    }
    return aliases.get(texto, texto or padrao)


def _dias_ate_preventiva(valor_data):
    data_prev = _valor_data(valor_data)
    if not data_prev:
        return None
    return (data_prev.date() - agora_local().date()).days


def _buscar_maquina_para_preventiva(codigo_maquina, id_filial="", conn=None):
    codigo = _valor_texto(codigo_maquina)
    if not codigo:
        return None

    sql = """
        SELECT *
        FROM `check_maquinas`.`maquinas`
        WHERE `codigo` = %s
    """
    params = [codigo]
    if possui_filial(id_filial):
        sql += " AND `id_filial` = %s"
        params.append(id_filial)
    sql += " ORDER BY `id` DESC LIMIT 1"

    close_conn = False
    if conn is None:
        conn = conectar()
        close_conn = True
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
        return normalizar_linha_saida("maquinas", row) if row else None
    finally:
        if close_conn:
            conn.close()


def _preventivas_id_auto_increment(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT `EXTRA`
            FROM `information_schema`.`COLUMNS`
            WHERE `TABLE_SCHEMA` = 'check_maquinas'
              AND `TABLE_NAME` = 'preventivas'
              AND `COLUMN_NAME` = 'id'
            LIMIT 1
            """
        )
        row = cur.fetchone() or {}
    return "auto_increment" in _valor_texto(row.get("EXTRA")).lower()


def _buscar_preventiva_por_id(id_registro, conn=None):
    if id_registro in [None, ""]:
        return None
    close_conn = False
    if conn is None:
        conn = conectar()
        close_conn = True
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM `check_maquinas`.`preventivas` WHERE `id` = %s LIMIT 1",
                [id_registro],
            )
            row = cur.fetchone()
        return normalizar_linha_saida("preventivas", row) if row else None
    finally:
        if close_conn:
            conn.close()


def _buscar_preventiva_aberta(codigo_maquina, id_maquina=None, conn=None):
    codigo = _valor_texto(codigo_maquina)
    if not codigo and id_maquina in [None, ""]:
        return None

    filtros = []
    params = []
    if codigo:
        filtros.append("`codigo_maquina` = %s")
        params.append(codigo)
    if id_maquina not in [None, ""]:
        filtros.append("`id_maquina` = %s")
        params.append(id_maquina)

    sql = f"""
        SELECT *
        FROM `check_maquinas`.`preventivas`
        WHERE {' AND '.join(filtros)}
          AND UPPER(REPLACE(COALESCE(`status`, ''), ' ', '_')) NOT IN (
              'CONCLUIDA', 'CONCLUÍDA', 'FINALIZADA', 'FINALIZADO',
              'CORRIGIDA', 'CORRIGIDO', 'CANCELADA', 'CANCELADO'
          )
        ORDER BY COALESCE(`data_prox_prev`, `data_ultima_prev`) DESC, `id` DESC
        LIMIT 1
    """

    close_conn = False
    if conn is None:
        conn = conectar()
        close_conn = True
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
        return normalizar_linha_saida("preventivas", row) if row else None
    finally:
        if close_conn:
            conn.close()


def _inserir_preventiva(dados, conn=None):
    close_conn = False
    if conn is None:
        conn = conectar()
        close_conn = True

    try:
        dados_filtrados = filtrar_dados("preventivas", dados, permitir_id=True)
        if not dados_filtrados:
            raise ValueError("Nenhum campo válido enviado para o histórico de preventivas.")

        if dados_filtrados.get("id") in [None, ""]:
            dados_filtrados.pop("id", None)
            if not _preventivas_id_auto_increment(conn):
                # Compatibilidade com a tabela criada com PK sem AUTO_INCREMENT.
                # Em um próximo ajuste, o ideal é alterar id para AUTO_INCREMENT.
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT COALESCE(MAX(`id`), 0) + 1 AS `proximo_id` FROM `check_maquinas`.`preventivas`"
                    )
                    row = cur.fetchone() or {}
                dados_filtrados["id"] = int(row.get("proximo_id") or 1)

        colunas = list(dados_filtrados.keys())
        valores = [dados_filtrados[c] for c in colunas]
        colunas_sql = ", ".join([f"`{c}`" for c in colunas])
        placeholders = ", ".join(["%s"] * len(colunas))
        sql = f"INSERT INTO `check_maquinas`.`preventivas` ({colunas_sql}) VALUES ({placeholders})"

        with conn.cursor() as cur:
            cur.execute(sql, valores)
            novo_id = dados_filtrados.get("id") or cur.lastrowid

        if close_conn:
            conn.commit()
        return _buscar_preventiva_por_id(novo_id, conn=conn)
    except Exception:
        if close_conn:
            conn.rollback()
        raise
    finally:
        if close_conn:
            conn.close()


def salvar_historico_preventiva(payload, conn=None, atualizar_aberta=True):
    dados = dict(
        (payload or {}).get("preventiva")
        or (payload or {}).get("dados")
        or payload
        or {}
    )
    id_registro = dados.pop("id", None)

    codigo = _valor_texto(dados.get("codigo_maquina") or dados.get("codigoMaquina"))
    id_filial = dados.pop("id_filial", None) or dados.pop("idFilial", None) or ""
    id_maquina = dados.get("id_maquina") or dados.get("idMaquina")

    maquina = _buscar_maquina_para_preventiva(codigo, id_filial=id_filial, conn=conn) if codigo else None
    if maquina:
        codigo = codigo or _valor_texto(maquina.get("codigo"))
        id_maquina = id_maquina or maquina.get("id_maquina") or maquina.get("id")

    if not codigo:
        raise ValueError("Informe codigo_maquina para salvar o histórico da preventiva.")

    ultima = _valor_data(dados.get("data_ultima_prev") or dados.get("ultimaPreventiva"))
    proxima = _valor_data(dados.get("data_prox_prev") or dados.get("proximaPreventiva"))
    if ultima and not proxima:
        proxima = _valor_data(_somar_meses(ultima, 1))

    status = _status_preventiva(dados.get("status"))
    dias = dados.get("dias_prox_prev")
    if dias in [None, ""]:
        dias = _dias_ate_preventiva(proxima)
    else:
        try:
            dias = int(dias)
        except Exception:
            dias = _dias_ate_preventiva(proxima)

    registro = {
        "id_maquina": id_maquina,
        "codigo_maquina": _texto_preventiva(codigo),
        "data_ultima_prev": ultima.date().isoformat() if ultima else None,
        "dias_prox_prev": dias,
        "data_prox_prev": proxima.date().isoformat() if proxima else None,
        "descricao": _texto_preventiva(dados.get("descricao")),
        "id_pecas": dados.get("id_pecas") or dados.get("idPecas"),
        "pecas": _texto_preventiva(dados.get("pecas")),
        "status": _texto_preventiva(status),
        "responsavel": _texto_preventiva(dados.get("responsavel")),
        "observacao": _texto_preventiva(dados.get("observacao")),
    }
    registro = {k: v for k, v in registro.items() if v is not None}

    close_conn = False
    if conn is None:
        conn = conectar()
        close_conn = True

    try:
        existente = _buscar_preventiva_por_id(id_registro, conn=conn) if id_registro else None
        if not existente and atualizar_aberta:
            existente = _buscar_preventiva_aberta(codigo, id_maquina=id_maquina, conn=conn)

        if existente:
            atualizar("preventivas", registro, {"id": existente.get("id")}, conn=conn)
            salvo = _buscar_preventiva_por_id(existente.get("id"), conn=conn)
        else:
            salvo = _inserir_preventiva(registro, conn=conn)

        if close_conn:
            conn.commit()
        return salvo
    except Exception:
        if close_conn:
            conn.rollback()
        raise
    finally:
        if close_conn:
            conn.close()


def buscar_historico_preventivas(
    codigo_maquina="",
    id_maquina="",
    id_filial="",
    status="",
    data_inicio="",
    data_fim="",
    limit=1000,
):
    """Busca os ciclos preventivos relacionados ao período informado.

    Um ciclo pertence ao período quando a preventiva foi realizada no mês
    (data_ultima_prev) ou quando a próxima preventiva foi programada para o
    mês (data_prox_prev). A tabela preventivas não possui id_filial, por isso
    a filial é resolvida de forma determinística pela máquina correspondente.
    """
    params = []
    filtro_filial_join = ""
    if possui_filial(id_filial):
        # A filial precisa participar da escolha da máquina no próprio JOIN.
        # Caso contrário, um código repetido em outra filial com ID maior
        # poderia esconder o registro correto da filial solicitada.
        filtro_filial_join = " AND m2.`id_filial` = %s"
        params.append(id_filial)

    sql = f"""
        SELECT
            p.*,
            m.`id_filial`,
            m.`descricao` AS `maquina_descricao`,
            m.`tipo_maquina` AS `maquina_tipo`
        FROM `check_maquinas`.`preventivas` p
        LEFT JOIN `check_maquinas`.`maquinas` m
          ON m.`id` = (
              SELECT MAX(m2.`id`)
              FROM `check_maquinas`.`maquinas` m2
              WHERE CONVERT(m2.`codigo` USING utf8mb4) COLLATE utf8mb4_unicode_ci
                    = CONVERT(p.`codigo_maquina` USING utf8mb4) COLLATE utf8mb4_unicode_ci
                AND (
                    p.`id_maquina` IS NULL
                    OR p.`id_maquina` = 0
                    OR m2.`id_maquina` = p.`id_maquina`
                    OR m2.`id` = p.`id_maquina`
                )
                {filtro_filial_join}
          )
        WHERE 1=1
    """

    if _valor_texto(codigo_maquina):
        sql += " AND p.`codigo_maquina` = %s"
        params.append(_valor_texto(codigo_maquina))
    if _valor_texto(id_maquina):
        sql += " AND p.`id_maquina` = %s"
        params.append(id_maquina)
    if possui_filial(id_filial):
        # Garante que históricos sem uma máquina correspondente na filial não
        # sejam misturados ao cronograma solicitado.
        sql += " AND m.`id_filial` IS NOT NULL"
    if _valor_texto(status):
        sql += " AND UPPER(REPLACE(COALESCE(p.`status`, ''), ' ', '_')) = %s"
        params.append(_status_preventiva(status))

    inicio = _valor_data(data_inicio)
    fim = _valor_data(data_fim)
    if inicio and fim:
        inicio_sql = inicio.date().isoformat()
        fim_sql = fim.date().isoformat()
        sql += """
            AND (
                (p.`data_ultima_prev` BETWEEN %s AND %s)
                OR (p.`data_prox_prev` BETWEEN %s AND %s)
            )
        """
        params.extend([inicio_sql, fim_sql, inicio_sql, fim_sql])
    elif inicio:
        inicio_sql = inicio.date().isoformat()
        sql += " AND (p.`data_ultima_prev` >= %s OR p.`data_prox_prev` >= %s)"
        params.extend([inicio_sql, inicio_sql])
    elif fim:
        fim_sql = fim.date().isoformat()
        sql += " AND (p.`data_ultima_prev` <= %s OR p.`data_prox_prev` <= %s)"
        params.extend([fim_sql, fim_sql])

    try:
        limit_int = int(limit or 1000)
    except Exception:
        limit_int = 1000
    limit_int = max(1, min(limit_int, 5000))
    sql += f"""
        ORDER BY GREATEST(
            COALESCE(p.`data_ultima_prev`, '1000-01-01'),
            COALESCE(p.`data_prox_prev`, '1000-01-01')
        ) DESC, p.`id` DESC
        LIMIT {limit_int}
    """

    with conectar() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

    saida = []
    ids_adicionados = set()
    for row in rows:
        # Proteção adicional contra duplicidade de JOIN ou de resposta.
        registro_id = row.get("id")
        chave = f"id:{registro_id}" if registro_id not in [None, ""] else (
            f"{row.get('codigo_maquina')}|{row.get('data_ultima_prev')}|"
            f"{row.get('data_prox_prev')}|{row.get('status')}"
        )
        if chave in ids_adicionados:
            continue
        ids_adicionados.add(chave)

        item = normalizar_linha_saida("preventivas", row)
        dias_calculados = _dias_ate_preventiva(item.get("data_prox_prev"))
        # dias_prox_prev gravado na tabela é somente uma fotografia do dia em
        # que o ciclo foi salvo. Alertas são sempre recalculados pela data.
        item["dias_prox_prev_calculado"] = dias_calculados

        if dias_calculados is None:
            status_prazo = "SEM_PROGRAMACAO"
        elif dias_calculados < 0:
            status_prazo = "VENCIDA"
        elif dias_calculados == 0:
            status_prazo = "VENCE_HOJE"
        elif dias_calculados <= 5:
            status_prazo = "PROXIMA"
        else:
            status_prazo = "EM_DIA"

        item["status_prazo"] = status_prazo
        item["status_calculado"] = _status_preventiva(item.get("status"))
        item["alerta_5_dias"] = (
            dias_calculados is not None and 0 <= dias_calculados <= 5
        )
        item["preventiva_vencida"] = (
            dias_calculados is not None and dias_calculados < 0
        )
        if inicio and fim:
            item["ultima_no_periodo"] = bool(
                _valor_data(item.get("data_ultima_prev"))
                and inicio.date()
                <= _valor_data(item.get("data_ultima_prev")).date()
                <= fim.date()
            )
            item["proxima_no_periodo"] = bool(
                _valor_data(item.get("data_prox_prev"))
                and inicio.date()
                <= _valor_data(item.get("data_prox_prev")).date()
                <= fim.date()
            )
        saida.append(item)
    return saida


def anexar_peca_historico_preventiva(codigo_maquina, id_maquina, id_peca, nome_peca, observacao=""):
    codigo = _valor_texto(codigo_maquina)
    if not codigo:
        return None

    with conectar() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT *
                    FROM `check_maquinas`.`preventivas`
                    WHERE (`codigo_maquina` = %s OR `id_maquina` = %s)
                    ORDER BY
                        COALESCE(`data_ultima_prev`, `data_prox_prev`) DESC,
                        CASE
                            WHEN UPPER(REPLACE(COALESCE(`status`, ''), ' ', '_')) IN ('EM_MANUTENCAO', 'EM_ANDAMENTO') THEN 0
                            WHEN UPPER(REPLACE(COALESCE(`status`, ''), ' ', '_')) IN ('CONCLUIDA', 'FINALIZADA', 'FINALIZADO') THEN 1
                            ELSE 2
                        END,
                        `id` DESC
                    LIMIT 1
                    """,
                    [codigo, id_maquina],
                )
                registro = cur.fetchone()

            if not registro:
                return None

            nomes = [p.strip() for p in _valor_texto(registro.get("pecas")).split(",") if p.strip()]
            nome = _valor_texto(nome_peca)
            if nome and nome not in nomes:
                nomes.append(nome)

            dados = {
                "pecas": _texto_preventiva(", ".join(nomes)),
            }
            if registro.get("id_pecas") in [None, ""] and id_peca not in [None, ""]:
                dados["id_pecas"] = id_peca
            if observacao and not _valor_texto(registro.get("observacao")):
                dados["observacao"] = _texto_preventiva(observacao)

            atualizar("preventivas", dados, {"id": registro.get("id")}, conn=conn)
            conn.commit()
            return _buscar_preventiva_por_id(registro.get("id"), conn=conn)
        except Exception:
            conn.rollback()
            raise


def _status_oficina_aberto(status):
    texto = _valor_texto(status).upper().replace(" ", "_")
    return texto in ["EM_ANDAMENTO", "EM_MANUTENCAO", "EM_MANUTENÇÃO", "ABERTO"]


def _resultado_nao_liberado(resultado):
    texto = _valor_texto(resultado).upper().replace(" ", "_")
    return texto in [
        "NAO_LIBERADO",
        "NÃO_LIBERADO",
        "REPROVADO",
        "PENDENTE",
        "EM_ANDAMENTO",
    ]


def _resultado_liberado(resultado):
    texto = _valor_texto(resultado).upper().replace(" ", "_")
    return texto in [
        "LIBERADO",
        "LIBERADO_COM_RESTRICAO",
        "LIBERADO_COM_RESTRIÇÃO",
    ]


def _calcular_tempo_oficina(entrada, saida):
    inicio = _valor_data(entrada)
    fim = _valor_data(saida)
    if not inicio or not fim:
        return None, None

    segundos = max(0.0, (fim - inicio).total_seconds())
    minutos = int(round(segundos / 60.0))
    dias = round(segundos / 86400.0, 2)
    return minutos, dias


def _aplicar_controle_oficina(dados, existente=None):
    """Prepara entrada/saída e duração sem exigir atualização contínua no banco."""
    dados = dict(dados or {})
    base = dict(existente or {})
    efetivo = dict(base)
    efetivo.update({k: v for k, v in dados.items() if v is not None})

    status = _valor_texto(efetivo.get("status_servico")).upper().replace(" ", "_")
    resultado = _valor_texto(efetivo.get("resultado_liberacao"))

    entrada = efetivo.get("entrada_oficina")
    saida = efetivo.get("saida_oficina")

    if _status_oficina_aberto(status):
        if not entrada:
            entrada = agora_mysql()
            dados["entrada_oficina"] = entrada
        dados["saida_oficina"] = None
        dados["tempo_parada_minutos"] = None
        dados["tempo_manutencao"] = None
        return dados

    deve_encerrar = bool(entrada) and (
        status in ["FINALIZADO", "CONCLUIDO", "CONCLUÍDO", "FECHADO"]
        or _resultado_liberado(resultado)
    )

    if _resultado_nao_liberado(resultado):
        dados["status_servico"] = "EM_ANDAMENTO"
        if not entrada:
            entrada = agora_mysql()
            dados["entrada_oficina"] = entrada
        dados["saida_oficina"] = None
        dados["tempo_parada_minutos"] = None
        dados["tempo_manutencao"] = None
        return dados

    if deve_encerrar:
        if not saida:
            saida = agora_mysql()
            dados["saida_oficina"] = saida
        minutos, dias = _calcular_tempo_oficina(entrada, saida)
        if minutos is not None:
            dados["tempo_parada_minutos"] = minutos
            dados["tempo_manutencao"] = dias

    return dados


def _enriquecer_tempo_oficina(servico):
    if not servico:
        return servico
    item = dict(servico)
    entrada = item.get("entrada_oficina")
    saida = item.get("saida_oficina")
    aberto = bool(entrada) and not bool(saida) and _status_oficina_aberto(item.get("status_servico"))
    fim = agora_local() if aberto else _valor_data(saida)
    minutos, dias = _calcular_tempo_oficina(entrada, fim)
    item["oficina_aberta"] = aberto
    if minutos is not None:
        item["tempo_parada_minutos_calculado"] = minutos
        item["tempo_manutencao_calculado"] = dias
    return item


def buscar_servico_oficina_aberto(codigo_maquina, id_filial=""):
    codigo = _valor_texto(codigo_maquina)
    if not codigo:
        return None

    sql = """
        SELECT *
        FROM `check_maquinas`.`manutencao_servicos`
        WHERE `codigo_maquina` = %s
          AND `entrada_oficina` IS NOT NULL
          AND `saida_oficina` IS NULL
          AND `status_servico` IN ('EM_ANDAMENTO', 'EM MANUTENCAO', 'EM MANUTENÇÃO', 'ABERTO')
    """
    params = [codigo]
    if possui_filial(id_filial):
        sql += " AND `id_filial` = %s"
        params.append(id_filial)
    sql += " ORDER BY `entrada_oficina` DESC, `id` DESC LIMIT 1"

    with conectar() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()

    if not row:
        return None
    return _enriquecer_tempo_oficina(normalizar_linha_saida("manutencao_servicos", row))


def iniciar_manutencao_oficina(payload):
    payload = dict(payload or {})
    servico = dict(payload.get("servico") or payload.get("dados") or payload)
    codigo = _valor_texto(servico.get("codigo_maquina") or payload.get("codigoMaquina"))
    id_filial = servico.get("id_filial") or payload.get("idFilial")

    existente = buscar_servico_oficina_aberto(codigo, id_filial)
    if existente:
        return existente

    servico["codigo_maquina"] = codigo
    if id_filial not in [None, ""]:
        servico["id_filial"] = id_filial
    servico["status_servico"] = "EM_ANDAMENTO"
    servico["entrada_oficina"] = servico.get("entrada_oficina") or agora_mysql()
    servico["saida_oficina"] = None
    servico["tempo_manutencao"] = None
    servico["tempo_parada_minutos"] = None

    return salvar_servico_manutencao({"servico": servico})


def finalizar_manutencao_oficina(payload):
    payload = dict(payload or {})
    servico = dict(payload.get("servico") or payload.get("dados") or payload)
    id_servico = servico.get("id") or payload.get("idServico")

    existente = selecionar_um("manutencao_servicos", {"id": id_servico}) if id_servico else None
    if not existente:
        codigo = _valor_texto(servico.get("codigo_maquina") or payload.get("codigoMaquina"))
        id_filial = servico.get("id_filial") or payload.get("idFilial")
        existente = buscar_servico_oficina_aberto(codigo, id_filial)

    if not existente:
        raise ValueError("Nenhum serviço de oficina em andamento foi encontrado.")

    dados = dict(existente)
    dados.update(servico)
    dados["id"] = existente.get("id")
    if not _valor_texto(servico.get("status_servico")):
        dados["status_servico"] = "FINALIZADO"

    if not _valor_texto(dados.get("resultado_liberacao")):
        raise ValueError("Informe o resultado da liberação para finalizar a oficina.")

    if _resultado_liberado(dados.get("resultado_liberacao")):
        if not _valor_texto(servico.get("saida_oficina")):
            raise ValueError(
                "Informe saida_oficina com a data e hora real da liberação. "
                "O backend não gera mais automaticamente esse horário."
            )

        entrada_validacao = _valor_data(
            servico.get("entrada_oficina") or existente.get("entrada_oficina")
        )
        saida_validacao = _valor_data(servico.get("saida_oficina"))
        if entrada_validacao and saida_validacao and saida_validacao < entrada_validacao:
            raise ValueError(
                "A saída da oficina não pode ser anterior à entrada da oficina."
            )

    return salvar_servico_manutencao({
        "servico": dados,
        "checklistMecanica": payload.get("checklistMecanica") or payload.get("checklist_mecanica") or [],
        "resolverPendencia": payload.get("resolverPendencia") or payload.get("resolver_pendencia") or False,
        "atualizarPreventiva": payload.get("atualizarPreventiva") or payload.get("atualizar_preventiva") or False,
    })


def _somar_meses(valor_data, meses=1):
    data_base = _valor_data(valor_data)
    try:
        meses_int = int(meses)
    except Exception:
        meses_int = 1

    if not data_base:
        return None

    indice_mes = data_base.year * 12 + (data_base.month - 1) + meses_int
    ano = indice_mes // 12
    mes = indice_mes % 12 + 1
    dia = min(data_base.day, monthrange(ano, mes)[1])
    return date(ano, mes, dia).isoformat()


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


def _normalizar_operador_saida(operador, matricula_busca=""):
    if not operador:
        return None

    saida = serializar(dict(operador))

    if not _valor_texto(saida.get("matricula")):
        for campo in ["matricula_operador", "codigo", "cod_operador", "registro"]:
            if _valor_texto(saida.get(campo)):
                saida["matricula"] = _valor_texto(saida.get(campo))
                break
    if not _valor_texto(saida.get("matricula")):
        saida["matricula"] = _valor_texto(matricula_busca)

    if not _valor_texto(saida.get("nome")):
        for campo in ["operador", "nome_operador", "colaborador", "funcionario", "nome_funcionario"]:
            if _valor_texto(saida.get(campo)):
                saida["nome"] = _valor_texto(saida.get(campo))
                break

    apto = _valor_texto(saida.get("apto"))
    if not apto:
        ativo = _valor_texto(saida.get("ativo")).lower()
        situacao = _valor_texto(saida.get("situacao")).lower()
        status = _valor_texto(saida.get("status")).lower()
        if ativo in ["1", "s", "sim", "true", "ativo"] or situacao in ["ativo", "apto", "liberado"] or status in ["ativo", "apto", "liberado"]:
            apto = "S"
        elif ativo in ["0", "n", "nao", "não", "false", "inativo"] or situacao in ["inativo", "inapto", "bloqueado"] or status in ["inativo", "inapto", "bloqueado"]:
            apto = "N"
    else:
        apto_norm = apto.strip().lower()
        if apto_norm in ["sim", "s", "1", "true", "apto", "liberado"]:
            apto = "S"
        elif apto_norm in ["nao", "não", "n", "0", "false", "inapto", "bloqueado"]:
            apto = "N"
    if apto:
        saida["apto"] = apto

    id_filial = _valor_texto(saida.get("id_filial"))
    if id_filial:
        try:
            for filial in buscar_filiais():
                fid = _valor_texto(filial.get("id") or filial.get("id_filial"))
                if fid == id_filial:
                    for campo in ["filial", "cidade", "estado"]:
                        if not _valor_texto(saida.get(campo)) and campo in filial:
                            saida[campo] = filial.get(campo)
                    break
        except Exception:
            pass

    return saida


def buscar_operador_por_matricula(matricula):
    texto = _valor_texto(matricula)
    if not texto:
        return None

    tabelas = [
        ("check_maquinas", "operador"),
        ("check_maquinas", "operadores"),
        ("base_gestao_master", "operador"),
        ("base_gestao_master", "operadores"),
    ]
    campos_matricula = ["matricula", "matricula_operador", "registro", "codigo", "cod_operador"]

    with conectar() as conn:
        for schema, tabela in tabelas:
            for campo in campos_matricula:
                sql = f"""
                    SELECT *
                    FROM `{schema}`.`{tabela}`
                    WHERE CAST(`{campo}` AS CHAR) = %s
                    LIMIT 1
                """
                try:
                    with conn.cursor() as cur:
                        cur.execute(sql, [texto])
                        row = cur.fetchone()
                    if row:
                        return _normalizar_operador_saida(row, matricula_busca=texto)
                except Exception:
                    continue

    return None



# ============================================================
# OPERADORES - SINCRONIZAÇÃO RH / CONSULTA POR NOME
# ============================================================

def sincronizar_operadores_rh():
    """
    Sincroniza a tabela existente check_maquinas.operador com base_rh.head_count.

    Regras:
    - NÃO usa/preenche matrícula nesta etapa;
    - NÃO altera id_filial nesta etapa;
    - atualiza nome, filial, turno, cargo, situacao e apto;
    - apto = 'S' somente quando:
        situacao = 'efetivo'
        E cargo = 'OPERADOR DE EMPILHADEIRA'
    - caso situacao/cargo mudem no RH, apto passa automaticamente para 'N';
    - novos registros são inseridos somente se hoje forem operadores efetivos;
    - ligação temporária entre as tabelas é feita pelo nome normalizado.

    Observação:
    Enquanto não houver um identificador estável do RH armazenado na tabela
    operador, nomes homônimos continuam sendo uma limitação conhecida.
    """
    with conectar() as conn:
        try:
            with conn.cursor() as cur:
                # Atualiza quem já existe, inclusive mudança de turno,
                # situação, cargo ou filial.
                cur.execute(
                    """
                    UPDATE `check_maquinas`.`operador` o
                    INNER JOIN `base_rh`.`head_count` hc
                        ON
                            CONVERT(UPPER(TRIM(o.`nome`)) USING utf8mb4)
                                COLLATE utf8mb4_unicode_ci
                            =
                            CONVERT(
                                UPPER(TRIM(CAST(hc.`nome` AS CHAR)))
                                USING utf8mb4
                            ) COLLATE utf8mb4_unicode_ci
                    SET
                        o.`nome` = TRIM(CAST(hc.`nome` AS CHAR)),
                        o.`filial` = TRIM(CAST(hc.`filial` AS CHAR)),
                        o.`turno` = TRIM(CAST(hc.`turno` AS CHAR)),
                        o.`cargo` = TRIM(CAST(hc.`cargo` AS CHAR)),
                        o.`situacao` = TRIM(CAST(hc.`situacao` AS CHAR)),
                        o.`apto` = CASE
                            WHEN LOWER(TRIM(CAST(hc.`situacao` AS CHAR))) = 'efetivo'
                             AND UPPER(TRIM(CAST(hc.`cargo` AS CHAR))) =
                                 'OPERADOR DE EMPILHADEIRA'
                            THEN 'S'
                            ELSE 'N'
                        END
                    """
                )
                atualizados = cur.rowcount

                # Insere novos operadores elegíveis.
                # matricula e id_filial ficam sem preenchimento nesta etapa.
                cur.execute(
                    """
                    INSERT INTO `check_maquinas`.`operador` (
                        `nome`,
                        `filial`,
                        `apto`,
                        `turno`,
                        `cargo`,
                        `situacao`
                    )
                    SELECT
                        TRIM(CAST(hc.`nome` AS CHAR)),
                        TRIM(CAST(hc.`filial` AS CHAR)),
                        'S',
                        TRIM(CAST(hc.`turno` AS CHAR)),
                        TRIM(CAST(hc.`cargo` AS CHAR)),
                        TRIM(CAST(hc.`situacao` AS CHAR))
                    FROM `base_rh`.`head_count` hc
                    WHERE LOWER(TRIM(CAST(hc.`situacao` AS CHAR))) = 'efetivo'
                      AND UPPER(TRIM(CAST(hc.`cargo` AS CHAR))) =
                          'OPERADOR DE EMPILHADEIRA'
                      AND NOT EXISTS (
                          SELECT 1
                          FROM `check_maquinas`.`operador` o
                          WHERE
                              CONVERT(UPPER(TRIM(o.`nome`)) USING utf8mb4)
                                  COLLATE utf8mb4_unicode_ci
                              =
                              CONVERT(
                                  UPPER(TRIM(CAST(hc.`nome` AS CHAR)))
                                  USING utf8mb4
                              ) COLLATE utf8mb4_unicode_ci
                      )
                    """
                )
                inseridos = cur.rowcount

            conn.commit()
            return {
                "atualizados": int(atualizados or 0),
                "inseridos": int(inseridos or 0),
            }
        except Exception:
            conn.rollback()
            raise


def buscar_operadores(
    nome="",
    filial="",
    apenas_aptos=True,
    sincronizar=True,
    limit=500,
):
    """
    Lista operadores para uso no app/site.

    Por padrão retorna somente quem realmente pode aparecer para operação:
      apto = S
      situacao = efetivo
      cargo = OPERADOR DE EMPILHADEIRA

    A matrícula continua no retorno para compatibilidade, mesmo vazia.
    """
    if sincronizar:
        sincronizar_operadores_rh()

    try:
        limit_int = int(limit or 500)
    except Exception:
        limit_int = 500
    limit_int = max(1, min(limit_int, 2000))

    sql = """
        SELECT
            `id`,
            `matricula`,
            `nome`,
            `id_filial`,
            `filial`,
            `apto`,
            `turno`,
            `cargo`,
            `situacao`
        FROM `check_maquinas`.`operador`
        WHERE 1 = 1
    """
    params = []

    if apenas_aptos:
        sql += """
          AND UPPER(TRIM(COALESCE(`apto`, ''))) = 'S'
          AND LOWER(TRIM(COALESCE(`situacao`, ''))) = 'efetivo'
          AND UPPER(TRIM(COALESCE(`cargo`, ''))) = 'OPERADOR DE EMPILHADEIRA'
        """

    nome_texto = _valor_texto(nome)
    if nome_texto:
        sql += """
          AND CONVERT(UPPER(TRIM(`nome`)) USING utf8mb4)
              COLLATE utf8mb4_unicode_ci
              LIKE
              CONVERT(UPPER(%s) USING utf8mb4)
              COLLATE utf8mb4_unicode_ci
        """
        params.append(f"%{nome_texto}%")

    filial_texto = _valor_texto(filial)
    if filial_texto:
        sql += """
          AND CONVERT(UPPER(TRIM(`filial`)) USING utf8mb4)
              COLLATE utf8mb4_unicode_ci
              =
              CONVERT(UPPER(%s) USING utf8mb4)
              COLLATE utf8mb4_unicode_ci
        """
        params.append(filial_texto)

    sql += f" ORDER BY `nome` ASC LIMIT {limit_int}"

    with conectar() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

    return [serializar(dict(row)) for row in rows]


def buscar_operador_por_nome(nome, filial="", sincronizar=True):
    """
    Busca um operador pelo nome.

    Primeiro tenta correspondência exata. Caso não encontre e o texto seja
    parcial, retorna a lista de candidatos compatíveis para a interface poder
    permitir seleção segura.
    """
    nome_texto = _valor_texto(nome)
    if not nome_texto:
        return None

    if sincronizar:
        sincronizar_operadores_rh()

    sql = """
        SELECT
            `id`,
            `matricula`,
            `nome`,
            `id_filial`,
            `filial`,
            `apto`,
            `turno`,
            `cargo`,
            `situacao`
        FROM `check_maquinas`.`operador`
        WHERE UPPER(TRIM(COALESCE(`apto`, ''))) = 'S'
          AND LOWER(TRIM(COALESCE(`situacao`, ''))) = 'efetivo'
          AND UPPER(TRIM(COALESCE(`cargo`, ''))) = 'OPERADOR DE EMPILHADEIRA'
          AND CONVERT(UPPER(TRIM(`nome`)) USING utf8mb4)
              COLLATE utf8mb4_unicode_ci
              =
              CONVERT(UPPER(%s) USING utf8mb4)
              COLLATE utf8mb4_unicode_ci
    """
    params = [nome_texto]

    filial_texto = _valor_texto(filial)
    if filial_texto:
        sql += """
          AND CONVERT(UPPER(TRIM(`filial`)) USING utf8mb4)
              COLLATE utf8mb4_unicode_ci
              =
              CONVERT(UPPER(%s) USING utf8mb4)
              COLLATE utf8mb4_unicode_ci
        """
        params.append(filial_texto)

    sql += " ORDER BY `id` ASC LIMIT 2"

    with conectar() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            exatos = cur.fetchall()

    if len(exatos) == 1:
        return serializar(dict(exatos[0]))

    if len(exatos) > 1:
        return {
            "ambigua": True,
            "operadores": [serializar(dict(row)) for row in exatos],
        }

    candidatos = buscar_operadores(
        nome=nome_texto,
        filial=filial_texto,
        apenas_aptos=True,
        sincronizar=False,
        limit=50,
    )
    if not candidatos:
        return None

    if len(candidatos) == 1:
        return candidatos[0]

    return {
        "ambigua": True,
        "operadores": candidatos,
    }





# ============================================================
# CHECKLIST TÉCNICO DE LIBERAÇÃO POR TIPO DE EQUIPAMENTO
#
# EMPILHADEIRA              -> check_mecanica (legado atual)
# LAVADORA DE PISO          -> check_mecanica_lavadora
# PALETEIRA                  -> check_mecanica_paleteira
# TRANSPALETEIRA ELÉTRICA   -> check_mecanica_transpaleteira
# ============================================================

CHECKLIST_COMUM_COMPLETO = [
    ("Serviço executado conforme descrição técnica", "exec_servico_executado", "exec_servico_executado_obs", "Execução", True),
    ("Equipamento limpo e sem ferramentas ou peças soltas", "org_equipamento_limpo", "org_equipamento_limpo_obs", "Organização", True),
    ("Ausência de vazamentos aparentes após intervenção", "seg_sem_vazamentos", "seg_sem_vazamentos_obs", "Segurança", True),
    ("Freio testado", "seg_freio_testado", "seg_freio_testado_obs", "Segurança", True),
    ("Direção e movimentação testadas", "ope_direcao_movimentacao", "ope_direcao_movimentacao_obs", "Operação", True),
    ("Comandos principais testados", "ope_comandos_principais", "ope_comandos_principais_obs", "Operação", True),
    ("Dispositivos de segurança verificados", "seg_dispositivos_seguranca", "seg_dispositivos_seguranca_obs", "Segurança", True),
    ("Proteções e tampas recolocadas", "seg_protecoes_tampas", "seg_protecoes_tampas_obs", "Segurança", True),
    ("Condições de segurança avaliadas antes da liberação", "seg_condicoes_liberacao", "seg_condicoes_liberacao_obs", "Segurança", True),
    ("Risco residual informado ao responsável", "ris_risco_residual", "ris_risco_residual_obs", "Risco", False),
    ("Equipamento em condição segura para operação", "lib_condicao_segura", "lib_condicao_segura_obs", "Liberação", True),
]

CHECKLIST_COMUM_PALETEIRA = [
    ("Serviço executado conforme descrição técnica", "exec_servico_executado", "exec_servico_executado_obs", "Execução", True),
    ("Equipamento limpo e sem ferramentas ou peças soltas", "org_equipamento_limpo", "org_equipamento_limpo_obs", "Organização", True),
    ("Ausência de vazamentos aparentes após intervenção", "seg_sem_vazamentos", "seg_sem_vazamentos_obs", "Segurança", True),
    ("Condições de segurança avaliadas antes da liberação", "seg_condicoes_liberacao", "seg_condicoes_liberacao_obs", "Segurança", True),
    ("Risco residual informado ao responsável", "ris_risco_residual", "ris_risco_residual_obs", "Risco", False),
    ("Equipamento em condição segura para operação", "lib_condicao_segura", "lib_condicao_segura_obs", "Liberação", True),
]

CHECK_MECANICA_EMPILHADEIRA_CAMPOS = CHECKLIST_COMUM_COMPLETO + [
    ("Torre testada", "emp_torre_testada", "emp_torre_testada_obs", "Empilhadeira", True),
    ("Correntes verificadas", "emp_correntes_verificadas", "emp_correntes_verificadas_obs", "Empilhadeira", True),
    ("Garfos verificados", "emp_garfos_verificados", "emp_garfos_verificados_obs", "Empilhadeira", True),
    ("Elevação e descida testadas", "emp_elevacao_descida_testadas", "emp_elevacao_descida_testadas_obs", "Empilhadeira", True),
    ("Inclinação testada", "emp_inclinacao_testada", "emp_inclinacao_testada_obs", "Empilhadeira", False),
    ("Alarme de ré testado", "emp_alarme_re_testado", "emp_alarme_re_testado_obs", "Empilhadeira", False),
    ("Giroflex e sinalização testados", "emp_giroflex_sinalizacao_testados", "emp_giroflex_sinalizacao_testados_obs", "Empilhadeira", False),
    ("Cinto de segurança verificado", "emp_cinto_seguranca_verificado", "emp_cinto_seguranca_verificado_obs", "Empilhadeira", True),
    ("Espelhos e extintor verificados", "emp_espelhos_extintor_verificados", "emp_espelhos_extintor_verificados_obs", "Empilhadeira", False),
]

CHECK_MECANICA_LAVADORA_CAMPOS = CHECKLIST_COMUM_COMPLETO + [
    ("Escovas / discos verificados", "lav_escovas_discos_verificados", "lav_escovas_discos_verificados_obs", "Lavadora", True),
    ("Rodo e lâminas de sucção verificados", "lav_rodo_succao_verificado", "lav_rodo_succao_verificado_obs", "Lavadora", True),
    ("Sistema de aspiração testado", "lav_sistema_aspiracao_testado", "lav_sistema_aspiracao_testado_obs", "Lavadora", True),
    ("Tanque de água limpa verificado", "lav_tanque_agua_limpa_verificado", "lav_tanque_agua_limpa_verificado_obs", "Lavadora", False),
    ("Tanque de recuperação verificado", "lav_tanque_recuperacao_verificado", "lav_tanque_recuperacao_verificado_obs", "Lavadora", False),
    ("Mangueiras e conexões verificadas", "lav_mangueiras_conexoes_verificadas", "lav_mangueiras_conexoes_verificadas_obs", "Lavadora", False),
    ("Sistema de dosagem de produto verificado", "lav_sistema_dosagem_verificado", "lav_sistema_dosagem_verificado_obs", "Lavadora", False),
    ("Bateria, cabos e conectores verificados", "lav_bateria_cabos_conectores_verificados", "lav_bateria_cabos_conectores_verificados_obs", "Lavadora", True),
    ("Carregador de bateria verificado", "lav_carregador_bateria_verificado", "lav_carregador_bateria_verificado_obs", "Lavadora", False),
    ("Rodas / pneus verificados", "lav_rodas_pneus_verificados", "lav_rodas_pneus_verificados_obs", "Lavadora", True),
    ("Tração e freio testados", "lav_tracao_freio_testados", "lav_tracao_freio_testados_obs", "Lavadora", True),
    ("Sinalização e alarme de ré testados", "lav_sinalizacao_alarme_re_testados", "lav_sinalizacao_alarme_re_testados_obs", "Lavadora", False),
    ("Elevação de escova / rodo testada", "lav_elevacao_escova_rodo_testada", "lav_elevacao_escova_rodo_testada_obs", "Lavadora", False),
]

CHECK_MECANICA_PALETEIRA_CAMPOS = CHECKLIST_COMUM_PALETEIRA + [
    ("Timão testado", "pal_timao_testado", "pal_timao_testado_obs", "Paleteira", True),
    ("Garfos e estrutura verificados", "pal_garfos_estrutura_verificados", "pal_garfos_estrutura_verificados_obs", "Paleteira", True),
    ("Rodas de carga verificadas", "pal_rodas_carga_verificadas", "pal_rodas_carga_verificadas_obs", "Paleteira", True),
    ("Rodas direcionais verificadas", "pal_rodas_direcionais_verificadas", "pal_rodas_direcionais_verificadas_obs", "Paleteira", True),
    ("Sistema de elevação testado", "pal_sistema_elevacao_testado", "pal_sistema_elevacao_testado_obs", "Paleteira", True),
    ("Sistema de descida testado", "pal_sistema_descida_testado", "pal_sistema_descida_testado_obs", "Paleteira", True),
    ("Bomba hidráulica verificada", "pal_bomba_hidraulica_verificada", "pal_bomba_hidraulica_verificada_obs", "Paleteira", True),
    ("Válvula de descida verificada", "pal_valvula_descida_verificada", "pal_valvula_descida_verificada_obs", "Paleteira", True),
    ("Identificação e capacidade de carga legíveis", "pal_identificacao_capacidade_legivel", "pal_identificacao_capacidade_legivel_obs", "Paleteira", False),
]

CHECK_MECANICA_TRANSPALETEIRA_CAMPOS = CHECKLIST_COMUM_COMPLETO + [
    ("Timão e comandos de movimentação testados", "tra_timao_comandos_testados", "tra_timao_comandos_testados_obs", "Transpaleteira elétrica", True),
    ("Botão de emergência testado", "tra_botao_emergencia_testado", "tra_botao_emergencia_testado_obs", "Transpaleteira elétrica", True),
    ("Botão anti-esmagamento testado", "tra_botao_antiesmagamento_testado", "tra_botao_antiesmagamento_testado_obs", "Transpaleteira elétrica", True),
    ("Buzina testada", "tra_buzina_testada", "tra_buzina_testada_obs", "Transpaleteira elétrica", False),
    ("Freio de serviço / estacionamento testado", "tra_freio_servico_estacionamento_testado", "tra_freio_servico_estacionamento_testado_obs", "Transpaleteira elétrica", True),
    ("Rodas de carga verificadas", "tra_rodas_carga_verificadas", "tra_rodas_carga_verificadas_obs", "Transpaleteira elétrica", True),
    ("Roda de tração verificada", "tra_roda_tracao_verificada", "tra_roda_tracao_verificada_obs", "Transpaleteira elétrica", True),
    ("Garfos e estrutura verificados", "tra_garfos_estrutura_verificados", "tra_garfos_estrutura_verificados_obs", "Transpaleteira elétrica", True),
    ("Sistema de elevação testado", "tra_sistema_elevacao_testado", "tra_sistema_elevacao_testado_obs", "Transpaleteira elétrica", True),
    ("Sistema de descida testado", "tra_sistema_descida_testado", "tra_sistema_descida_testado_obs", "Transpaleteira elétrica", True),
    ("Bateria, cabos e conectores verificados", "tra_bateria_cabos_conectores_verificados", "tra_bateria_cabos_conectores_verificados_obs", "Transpaleteira elétrica", True),
    ("Carregador de bateria verificado", "tra_carregador_bateria_verificado", "tra_carregador_bateria_verificado_obs", "Transpaleteira elétrica", False),
    ("Indicador de carga / painel testado", "tra_indicador_carga_painel_testado", "tra_indicador_carga_painel_testado_obs", "Transpaleteira elétrica", False),
]

CHECKLIST_CONFIG = {
    "EMPILHADEIRA": {
        "tabela": "check_mecanica",
        "campos": CHECK_MECANICA_EMPILHADEIRA_CAMPOS,
    },
    "LAVADORA_PISO": {
        "tabela": "check_mecanica_lavadora",
        "campos": CHECK_MECANICA_LAVADORA_CAMPOS,
    },
    "PALETEIRA": {
        "tabela": "check_mecanica_paleteira",
        "campos": CHECK_MECANICA_PALETEIRA_CAMPOS,
    },
    "TRANSPALETEIRA_ELETRICA": {
        "tabela": "check_mecanica_transpaleteira",
        "campos": CHECK_MECANICA_TRANSPALETEIRA_CAMPOS,
    },
}


def _status_check_mecanica_banco(valor):
    texto = _valor_texto(valor).upper().replace("_", " ").strip()
    if texto in ["S", "SIM", "OK"]:
        return "S"
    if texto in ["N", "NAO", "NÃO", "NOK", "N/OK", "NAO OK", "NÃO OK"]:
        return "N"
    if texto in ["NA", "N/A"]:
        return "NA"
    return "P"


def _status_check_mecanica_saida(valor):
    texto = _valor_texto(valor).upper()
    if texto == "S":
        return "OK"
    if texto == "N":
        return "NOK"
    if texto == "NA":
        return "NA"
    return "PENDENTE"


def _normalizar_tipo_checklist_texto(*valores):
    texto = " ".join(_valor_texto(v) for v in valores if _valor_texto(v))
    normalizado = (
        texto.upper()
        .replace("Á", "A")
        .replace("À", "A")
        .replace("Â", "A")
        .replace("Ã", "A")
        .replace("É", "E")
        .replace("Ê", "E")
        .replace("Í", "I")
        .replace("Ó", "O")
        .replace("Ô", "O")
        .replace("Õ", "O")
        .replace("Ú", "U")
        .replace("Ç", "C")
    )
    if "LAVADORA" in normalizado or "LIMPEZA" in normalizado or "RIDE-ON" in normalizado or "RIDE ON" in normalizado:
        return "LAVADORA_PISO"
    # TRANSPALETEIRA contém PALETEIRA; deve vir antes.
    if "TRANSPALETEIRA" in normalizado:
        return "TRANSPALETEIRA_ELETRICA"
    if "PALETEIRA" in normalizado:
        return "PALETEIRA"
    return "EMPILHADEIRA"


def _maquina_do_servico_checklist(id_servico, servico=None):
    registro = dict(servico or {})
    if not registro and _valor_texto(id_servico):
        registro = selecionar_um("manutencao_servicos", {"id": id_servico}) or {}
    if not registro:
        return None, {}

    maquina = None
    id_maquina = registro.get("id_maquina")
    if _valor_texto(id_maquina):
        maquina = selecionar_um("maquinas", {"id": id_maquina})

    if not maquina:
        codigo = _valor_texto(registro.get("codigo_maquina"))
        filtros = {"codigo": codigo} if codigo else {}
        if filtros and possui_filial(registro.get("id_filial")):
            filtros["id_filial"] = registro.get("id_filial")
        maquina = selecionar_um("maquinas", filtros) if filtros else None

    return maquina, registro


def _tipo_checklist_do_servico(id_servico, servico=None):
    maquina, registro = _maquina_do_servico_checklist(id_servico, servico=servico)
    if maquina:
        return _normalizar_tipo_checklist_texto(
            maquina.get("tipo_maquina"),
            maquina.get("descricao"),
            maquina.get("codigo"),
        )
    return _normalizar_tipo_checklist_texto(
        registro.get("tipo_maquina"),
        registro.get("descricao_servico"),
        registro.get("codigo_maquina"),
    )


def _config_checklist(tipo_checklist):
    return CHECKLIST_CONFIG.get(tipo_checklist) or CHECKLIST_CONFIG["EMPILHADEIRA"]


def _mapas_checklist(tipo_checklist):
    campos = _config_checklist(tipo_checklist)["campos"]
    por_item = {
        nome.strip().casefold(): (campo, campo_obs, categoria, critico)
        for nome, campo, campo_obs, categoria, critico in campos
    }
    por_campo = {
        campo: (nome, campo_obs, categoria, critico)
        for nome, campo, campo_obs, categoria, critico in campos
    }
    return por_item, por_campo


def _montar_check_mecanica_linha(id_servico, itens, servico=None, tipo_checklist=None):
    if not _valor_texto(id_servico):
        raise ValueError("Informe id_servico para salvar o checklist da mecânica.")
    itens = list(itens or [])
    if not itens:
        raise ValueError("Informe os itens do checklist da mecânica.")

    tipo = tipo_checklist or _tipo_checklist_do_servico(id_servico, servico=servico)
    por_item, _ = _mapas_checklist(tipo)

    dados = {
        "id_servico": id_servico,
        "status_check": "FINALIZADO",
        "resultado_check": "APROVADO PARA LIBERAÇÃO",
        "observacao_geral": "",
        "atualizado_em": agora_mysql(),
    }

    tem_nok = False
    tem_pendente = False
    observacoes_gerais = []

    for item in itens:
        item = dict(item or {})
        nome_item = _valor_texto(item.get("item"))
        if not nome_item:
            continue
        mapping = por_item.get(nome_item.casefold())
        if not mapping:
            # Bloqueia perda silenciosa de itens caso o Flutter e a API
            # estejam com versões incompatíveis.
            raise ValueError(
                f"Item não reconhecido para o checklist {tipo}: {nome_item}"
            )
        campo, campo_obs, _categoria, _critico = mapping
        status = _status_check_mecanica_banco(item.get("status") or item.get("status_item"))
        obs = _valor_texto(item.get("observacao"))
        if status == "N" and not obs:
            raise ValueError(f"Informe observação para o item NÃO OK: {nome_item}")
        dados[campo] = status
        dados[campo_obs] = obs or None
        if status == "N":
            tem_nok = True
        if status == "P":
            tem_pendente = True
        if obs:
            observacoes_gerais.append(f"{nome_item}: {obs}")

    if tem_pendente:
        dados["status_check"] = "ABERTO"
        dados["resultado_check"] = "CHECKLIST PENDENTE"
    elif tem_nok:
        dados["status_check"] = "FINALIZADO"
        dados["resultado_check"] = "PENDÊNCIA NA LIBERAÇÃO"
    else:
        dados["status_check"] = "FINALIZADO"
        dados["resultado_check"] = "APROVADO PARA LIBERAÇÃO"

    if observacoes_gerais:
        dados["observacao_geral"] = " | ".join(observacoes_gerais)
    return tipo, dados


def buscar_check_mecanica(id_servico="", servico=None):
    if not _valor_texto(id_servico):
        return None

    tipo_esperado = _tipo_checklist_do_servico(id_servico, servico=servico)
    ordem = [tipo_esperado] + [t for t in CHECKLIST_CONFIG.keys() if t != tipo_esperado]

    for tipo in ordem:
        tabela = _config_checklist(tipo)["tabela"]
        row = selecionar_um(tabela, {"id_servico": id_servico})
        if row:
            item = dict(row)
            item["tipo_checklist"] = tipo
            item["tabela_checklist"] = tabela
            item["itens"] = _check_mecanica_para_lista(item)
            item["checklist_liberacao_json"] = item["itens"]
            return item
    return None


def buscar_checks_mecanica(codigo_maquina="", id_filial="", limit=200):
    codigo = _valor_texto(codigo_maquina)
    filtros_sql = []
    params = []
    if codigo:
        filtros_sql.append("`codigo_maquina` = %s")
        params.append(codigo)
    if possui_filial(id_filial):
        filtros_sql.append("`id_filial` = %s")
        params.append(id_filial)
    where = " WHERE " + " AND ".join(filtros_sql) if filtros_sql else ""

    try:
        limit_int = int(limit or 200)
    except Exception:
        limit_int = 200
    limit_int = max(1, min(limit_int, 2000))

    sql = f"""
        SELECT *
        FROM `check_maquinas`.`manutencao_servicos`
        {where}
        ORDER BY `data_servico` DESC, `criado_em` DESC
        LIMIT {limit_int}
    """
    with conectar() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            servicos = cur.fetchall()

    saida = []
    for servico in servicos:
        check = buscar_check_mecanica(servico.get("id"), servico=servico)
        if not check:
            continue
        item = dict(check)
        for campo in [
            "id_filial", "id_maquina", "codigo_maquina", "id_pendencia",
            "id_check", "tipo_servico", "data_servico", "entrada_oficina",
            "tempo_manutencao", "saida_oficina", "tempo_parada_minutos",
            "horimetro_servico", "descricao_servico", "responsavel_execucao",
            "responsavel_liberacao", "resultado_liberacao", "status_servico",
        ]:
            item[campo] = servico.get(campo)
        saida.append(item)
    return saida


def salvar_check_mecanica(id_servico, itens, servico=None, conn=None):
    tipo, dados = _montar_check_mecanica_linha(
        id_servico, itens, servico=servico
    )
    tabela = _config_checklist(tipo)["tabela"]

    existente = selecionar_um(tabela, {"id_servico": id_servico})
    if existente:
        atualizar(tabela, dados, {"id_servico": id_servico}, conn=conn)
    else:
        inserir(tabela, dados, conn=conn)

    retorno = selecionar_um(tabela, {"id_servico": id_servico})
    if retorno:
        retorno = dict(retorno)
        retorno["tipo_checklist"] = tipo
        retorno["tabela_checklist"] = tabela
        retorno["itens"] = _check_mecanica_para_lista(retorno)
        retorno["checklist_liberacao_json"] = retorno["itens"]
    return retorno


def _check_mecanica_para_lista(row):
    if not row:
        return []
    tipo = _valor_texto(row.get("tipo_checklist"))
    if not tipo:
        # Detecta pelo conjunto de colunas quando chamado com linha bruta.
        if any(str(k).startswith("lav_") for k in row.keys()):
            tipo = "LAVADORA_PISO"
        elif any(str(k).startswith("tra_") for k in row.keys()):
            tipo = "TRANSPALETEIRA_ELETRICA"
        elif "pal_garfos_estrutura_verificados" in row:
            tipo = "PALETEIRA"
        else:
            tipo = "EMPILHADEIRA"

    _, por_campo = _mapas_checklist(tipo)
    itens = []
    for campo, (nome, campo_obs, categoria, critico) in por_campo.items():
        status = _valor_texto(row.get(campo))
        if not status:
            continue
        itens.append({
            "categoria": categoria,
            "item": nome,
            "status": _status_check_mecanica_saida(status),
            "observacao": _valor_texto(row.get(campo_obs)),
            "critico": critico,
            "aplicacao": tipo,
        })
    return itens


def _enriquecer_servicos_com_check_mecanica(servicos):
    """
    Enriquece uma lista de serviços sem executar consultas N+1.

    Antes, para cada serviço eram feitas:
      - até 1 consulta em maquinas para descobrir o tipo;
      - até 4 consultas nas tabelas de checklist.

    No cronograma mensal isso podia gerar mais de 100 conexões/queries
    sequenciais e estourar o timeout de 30 segundos.

    Agora todos os checklists são carregados em lote, usando no máximo
    quatro grupos de consultas, independentemente da quantidade de serviços.
    """
    preparados = [_enriquecer_tempo_oficina(registro) for registro in (servicos or [])]

    ids_servicos = []
    vistos = set()
    for servico in preparados:
        sid = servico.get("id")
        if sid in [None, ""]:
            continue
        chave = str(sid)
        if chave in vistos:
            continue
        vistos.add(chave)
        ids_servicos.append(sid)

    if not ids_servicos:
        return preparados

    # Se por algum motivo existir um registro legado em check_mecanica e
    # também um registro novo dedicado para o mesmo serviço, a tabela
    # dedicada tem prioridade.
    prioridade_tipos = [
        "LAVADORA_PISO",
        "PALETEIRA",
        "TRANSPALETEIRA_ELETRICA",
        "EMPILHADEIRA",
    ]

    checks_por_servico = {}
    tamanho_lote = 500

    with conectar() as conn:
        with conn.cursor() as cur:
            for tipo in prioridade_tipos:
                tabela = _config_checklist(tipo)["tabela"]

                for inicio in range(0, len(ids_servicos), tamanho_lote):
                    lote = ids_servicos[inicio:inicio + tamanho_lote]
                    placeholders = ", ".join(["%s"] * len(lote))

                    sql = f"""
                        SELECT *
                        FROM `{cfg_tabela(tabela)['schema']}`.`{cfg_tabela(tabela)['table']}`
                        WHERE `id_servico` IN ({placeholders})
                    """
                    cur.execute(sql, lote)

                    for row in cur.fetchall():
                        sid = row.get("id_servico")
                        chave = str(sid)
                        if chave in checks_por_servico:
                            continue

                        item = normalizar_linha_saida(tabela, row)
                        item = dict(item)
                        item["tipo_checklist"] = tipo
                        item["tabela_checklist"] = tabela
                        item["itens"] = _check_mecanica_para_lista(item)
                        item["checklist_liberacao_json"] = item["itens"]
                        checks_por_servico[chave] = item

    saida = []
    for servico in preparados:
        item_servico = dict(servico)
        check = checks_por_servico.get(str(item_servico.get("id")))

        if check:
            item_servico["check_mecanica"] = check
            item_servico["tipo_checklist_mecanica"] = check.get("tipo_checklist")
            item_servico["checklist_liberacao_json"] = check.get(
                "checklist_liberacao_json",
                [],
            )

        saida.append(item_servico)

    return saida


def buscar_servicos_manutencao(
    id_filial="",
    codigo_maquina="",
    id_pendencia="",
    id_check="",
    tipo_servico="",
    status_servico="",
    data_inicio="",
    data_fim="",
    limit=500,
):
    condicoes = []
    params = []

    if possui_filial(id_filial):
        condicoes.append("`id_filial` = %s")
        params.append(id_filial)
    if _valor_texto(codigo_maquina):
        condicoes.append("`codigo_maquina` = %s")
        params.append(_valor_texto(codigo_maquina))
    if _valor_texto(id_pendencia):
        condicoes.append("`id_pendencia` = %s")
        params.append(id_pendencia)
    if _valor_texto(id_check):
        condicoes.append("`id_check` = %s")
        params.append(id_check)
    if _valor_texto(tipo_servico):
        condicoes.append("`tipo_servico` = %s")
        params.append(tipo_servico)
    if _valor_texto(status_servico):
        condicoes.append("`status_servico` = %s")
        params.append(status_servico)

    inicio = _valor_data(data_inicio)
    fim = _valor_data(data_fim)
    if inicio and fim:
        from datetime import timedelta
        inicio_sql = datetime(inicio.year, inicio.month, inicio.day)
        fim_exclusivo = datetime(fim.year, fim.month, fim.day) + timedelta(days=1)
        # Inclui registros cuja data principal pertence ao mês e também
        # serviços de oficina que começaram antes, mas permaneceram abertos
        # ou foram finalizados dentro do período selecionado.
        condicoes.append("""
            (
                (
                    COALESCE(`data_servico`, `entrada_oficina`, `saida_oficina`, `criado_em`) >= %s
                    AND COALESCE(`data_servico`, `entrada_oficina`, `saida_oficina`, `criado_em`) < %s
                )
                OR (
                    `entrada_oficina` IS NOT NULL
                    AND `entrada_oficina` < %s
                    AND (`saida_oficina` IS NULL OR `saida_oficina` >= %s)
                )
            )
        """)
        params.extend([inicio_sql, fim_exclusivo, fim_exclusivo, inicio_sql])
    elif inicio:
        condicoes.append(
            "COALESCE(`data_servico`, `entrada_oficina`, `saida_oficina`, `criado_em`) >= %s"
        )
        params.append(inicio)
    elif fim:
        condicoes.append(
            "COALESCE(`data_servico`, `entrada_oficina`, `saida_oficina`, `criado_em`) <= %s"
        )
        params.append(fim)

    try:
        limit_int = int(limit or 500)
    except Exception:
        limit_int = 500
    limit_int = max(1, min(limit_int, 5000))

    where_sql = " WHERE " + " AND ".join(condicoes) if condicoes else ""
    sql = f"""
        SELECT *
        FROM `check_maquinas`.`manutencao_servicos`
        {where_sql}
        ORDER BY COALESCE(`data_servico`, `entrada_oficina`, `saida_oficina`, `criado_em`) DESC,
                 `id` DESC
        LIMIT {limit_int}
    """

    with conectar() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

    servicos = [normalizar_linha_saida("manutencao_servicos", row) for row in rows]
    return _enriquecer_servicos_com_check_mecanica(servicos)


def salvar_servico_manutencao(payload):
    payload = dict(payload or {})
    servico = dict(payload.get("servico") or payload.get("dados") or payload)
    checklist_mecanica = (
        payload.get("checklistMecanica")
        or payload.get("checklist_mecanica")
        or servico.pop("checklist_mecanica", None)
        or servico.pop("checklist_liberacao_json", None)
        or []
    )
    resolver_pend = bool(payload.get("resolverPendencia") or payload.get("resolver_pendencia"))
    atualizar_preventiva = bool(payload.get("atualizarPreventiva") or payload.get("atualizar_preventiva"))

    id_servico = servico.pop("id", None)
    existente = selecionar_um("manutencao_servicos", {"id": id_servico}) if id_servico else None

    tipo_servico_efetivo = _valor_texto(
        servico.get("tipo_servico") or (existente or {}).get("tipo_servico")
    ).upper().replace(" ", "_")
    # A própria API reconhece a preventiva, mesmo que um cliente antigo não
    # envie explicitamente atualizarPreventiva.
    atualizar_preventiva = atualizar_preventiva or "PREVENTIV" in tipo_servico_efetivo

    if not _valor_texto(servico.get("status_servico")):
        servico["status_servico"] = (existente or {}).get("status_servico") or "FINALIZADO"

    if not servico.get("data_servico"):
        servico["data_servico"] = (existente or {}).get("data_servico") or agora_mysql()
    else:
        servico["data_servico"] = normalizar_data_mysql(servico.get("data_servico"))

    if servico.get("entrada_oficina") not in [None, ""]:
        servico["entrada_oficina"] = normalizar_data_mysql(servico.get("entrada_oficina"))
    if servico.get("saida_oficina") not in [None, ""]:
        servico["saida_oficina"] = normalizar_data_mysql(servico.get("saida_oficina"))

    servico = _aplicar_controle_oficina(servico, existente=existente)
    servico["atualizado_em"] = agora_mysql()

    if not _valor_texto(servico.get("codigo_maquina")):
        raise ValueError("Informe codigo_maquina para salvar o serviço de manutenção.")
    if not _valor_texto(servico.get("tipo_servico")):
        raise ValueError("Informe tipo_servico para salvar o serviço de manutenção.")
    if not _valor_texto(servico.get("descricao_servico")):
        raise ValueError("Informe descricao_servico para salvar o serviço de manutenção.")
    if not _valor_texto(servico.get("responsavel_execucao")):
        raise ValueError("Informe responsavel_execucao para salvar o serviço de manutenção.")

    def _salvar_com_retry(dados):
        try:
            if id_servico:
                atualizar("manutencao_servicos", dados, {"id": id_servico})
                return selecionar_um("manutencao_servicos", {"id": id_servico})
            return inserir("manutencao_servicos", dados)
        except OperationalError as exc:
            mensagem = str(exc)
            # Mantém o sistema funcionando mesmo se o banco ainda não recebeu as colunas JSON.
            if "checklist_liberacao_json" in mensagem or "plano_acao_json" in mensagem:
                dados_sem_json = dict(dados)
                dados_sem_json.pop("checklist_liberacao_json", None)
                dados_sem_json.pop("plano_acao_json", None)
                if id_servico:
                    atualizar("manutencao_servicos", dados_sem_json, {"id": id_servico})
                    return selecionar_um("manutencao_servicos", {"id": id_servico})
                return inserir("manutencao_servicos", dados_sem_json)
            raise

    salvo = _salvar_com_retry(servico)
    id_servico = salvo.get("id") if salvo else id_servico

    if checklist_mecanica:
        salvar_check_mecanica(id_servico, checklist_mecanica, servico=salvo)

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
    status_servico_efetivo = _valor_texto(
        (salvo or {}).get("status_servico") or servico.get("status_servico")
    ).upper().replace(" ", "_")
    oficina_aberta = bool((salvo or {}).get("entrada_oficina")) and not bool((salvo or {}).get("saida_oficina"))
    servico_concluido = status_servico_efetivo in [
        "FINALIZADO",
        "CONCLUIDO",
        "CONCLUÍDO",
        "FECHADO",
    ] or _resultado_liberado(resultado)

    if oficina_aberta and codigo:
        atualizar(
            "maquinas",
            {"ativo": "Manutenção"},
            {"codigo": codigo, **({"id_filial": id_filial} if possui_filial(id_filial) else {})},
        )

    if atualizar_preventiva and codigo and not servico_concluido:
        maquina_preventiva = _buscar_maquina_para_preventiva(codigo, id_filial=id_filial) or {}
        salvar_historico_preventiva({
            "id_maquina": maquina_preventiva.get("id_maquina") or maquina_preventiva.get("id"),
            "codigo_maquina": codigo,
            "data_ultima_prev": maquina_preventiva.get("ultima_preventiva"),
            "data_prox_prev": maquina_preventiva.get("prox_preventiva"),
            "descricao": (salvo or {}).get("descricao_servico") or servico.get("descricao_servico"),
            "status": "EM_MANUTENCAO" if oficina_aberta else "EM_ANDAMENTO",
            "responsavel": responsavel,
            "observacao": (salvo or {}).get("observacao_liberacao") or servico.get("observacao_liberacao"),
        })

    if resolver_pend and not oficina_aberta and id_pendencia and responsavel:
        resolver_pendencia(
            id_pendencia,
            responsavel,
            agora_mysql(),
            (salvo or {}).get("observacao_liberacao") or servico.get("observacao_liberacao"),
        )

    if not oficina_aberta and _resultado_liberado(resultado) and codigo:
        pendencias = buscar_pendencias_da_maquina(codigo, id_filial)
        abertas = [p for p in pendencias if not p.get("resolvido") and not _normalizar_status_fechado(p.get("status_pendencia"))]
        if not abertas:
            liberar_maquina(codigo, id_filial)

    if atualizar_preventiva and servico_concluido and not oficina_aberta and codigo:
        data_execucao = (salvo or {}).get("data_servico") or servico.get("data_servico") or agora_mysql()
        data_preventiva = _valor_data(data_execucao) or agora_local()
        ultima_preventiva = data_preventiva.date().isoformat()
        proxima_preventiva = _somar_meses(data_preventiva, 1)
        horimetro = (salvo or {}).get("horimetro_servico") or servico.get("horimetro_servico")

        dados_maquina = {
            "ultima_preventiva": ultima_preventiva,
            "prox_preventiva": proxima_preventiva,
            "ultima_manutencao": normalizar_data_mysql(data_execucao),
        }

        # O horímetro permanece como informação histórica/operacional, sem
        # participar do cálculo do próximo vencimento.
        if horimetro is not None:
            dados_maquina.update({
                "horimetro_atual": horimetro,
                "ultimo_reg_horimetro": agora_mysql(),
                "horimetro_manutencao": horimetro,
            })

        atualizar(
            "maquinas",
            dados_maquina,
            {"codigo": codigo, **({"id_filial": id_filial} if possui_filial(id_filial) else {})},
        )

        maquina_preventiva = _buscar_maquina_para_preventiva(codigo, id_filial=id_filial) or {}
        salvar_historico_preventiva({
            "id_maquina": maquina_preventiva.get("id_maquina") or maquina_preventiva.get("id"),
            "codigo_maquina": codigo,
            "data_ultima_prev": ultima_preventiva,
            "data_prox_prev": proxima_preventiva,
            "dias_prox_prev": _dias_ate_preventiva(proxima_preventiva),
            "descricao": (salvo or {}).get("descricao_servico") or servico.get("descricao_servico"),
            "status": "CONCLUIDA",
            "responsavel": responsavel,
            "observacao": (salvo or {}).get("observacao_liberacao") or servico.get("observacao_liberacao"),
        })

    servico_final = selecionar_um("manutencao_servicos", {"id": id_servico})
    return _enriquecer_servicos_com_check_mecanica([servico_final])[0] if servico_final else servico_final


def buscar_pecas_manutencao(busca="", ativo="", categoria="", tipo_maquina="", limit=1000):
    sql = "SELECT * FROM `check_maquinas`.`manutencao_pecas` WHERE 1=1"
    params = []

    if _valor_texto(busca):
        termo = f"%{_valor_texto(busca)}%"
        sql += " AND (`codigo_peca` LIKE %s OR `descricao` LIKE %s OR `categoria` LIKE %s OR `fornecedor` LIKE %s OR `tipo_maquina` LIKE %s)"
        params.extend([termo, termo, termo, termo, termo])

    if _valor_texto(ativo):
        texto = _valor_texto(ativo).lower()
        if texto in ["true", "1", "s", "sim", "ativo"]:
            sql += " AND `ativo` = 1"
        elif texto in ["false", "0", "n", "nao", "não", "inativo"]:
            sql += " AND (`ativo` = 0 OR `ativo` IS NULL)"

    if _valor_texto(categoria):
        sql += " AND `categoria` = %s"
        params.append(categoria)

    if _valor_texto(tipo_maquina):
        sql += """
            AND CONVERT(UPPER(TRIM(`tipo_maquina`)) USING utf8mb4) COLLATE utf8mb4_unicode_ci
              = CONVERT(UPPER(TRIM(%s)) USING utf8mb4) COLLATE utf8mb4_unicode_ci
        """
        params.append(tipo_maquina)

    sql += " ORDER BY `tipo_maquina` ASC, `categoria` ASC, `descricao` ASC LIMIT %s"
    params.append(max(1, min(int(limit or 1000), 2000)))

    with conectar() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
    return [normalizar_linha_saida("manutencao_pecas", r) for r in rows]


def salvar_peca_manutencao(payload):
    dados = dict(payload.get("peca") or payload.get("dados") or payload or {})
    id_peca = dados.pop("id", None)

    # Regra do cadastro de peças:
    # codigo_peca NÃO é um código manual/mnemônico.
    # Ele deve ser sempre igual ao id da própria peça, para ficar simples de consultar e decorar.
    # Por isso a API ignora qualquer codigo_peca enviado pelo Flutter.
    dados.pop("codigo_peca", None)

    dados.setdefault("ativo", True)
    dados["atualizado_em"] = agora_mysql()

    if id_peca:
        atualizar("manutencao_pecas", dados, {"id": id_peca})
        # Garante que registros antigos/editados continuem no padrão codigo_peca = id.
        atualizar(
            "manutencao_pecas",
            {"codigo_peca": str(id_peca), "atualizado_em": agora_mysql()},
            {"id": id_peca},
        )
        return selecionar_um("manutencao_pecas", {"id": id_peca})

    # Para inserir, precisamos de um valor temporário único porque codigo_peca pode estar NOT NULL/UNIQUE.
    # Depois do INSERT, atualizamos codigo_peca com o id gerado pelo AUTO_INCREMENT.
    temp_codigo = "TEMP_" + agora_local().strftime("%Y%m%d%H%M%S%f")
    dados["codigo_peca"] = temp_codigo

    with conectar() as conn:
        try:
            novo = inserir("manutencao_pecas", dados, conn=conn)
            novo_id = novo.get("id") if isinstance(novo, dict) else None
            if not novo_id:
                raise ValueError("Nao foi possivel identificar o ID da peca criada.")

            atualizar(
                "manutencao_pecas",
                {"codigo_peca": str(novo_id), "atualizado_em": agora_mysql()},
                {"id": novo_id},
                conn=conn,
            )
            conn.commit()
            return selecionar_um("manutencao_pecas", {"id": novo_id})
        except Exception:
            conn.rollback()
            raise


def _linha_peca_maquina_com_status(linha, horimetro_atual=None):
    saida = serializar(linha or {})
    status_calculado = _valor_texto(saida.get("status") or "EM_DIA")
    alertas = []

    prox_data = _valor_data(saida.get("proxima_troca_data"))
    if prox_data:
        hoje = agora_local()
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


def buscar_pecas_da_maquina(
    codigo_maquina="",
    id_maquina="",
    id_peca="",
    id_filial="",
    id_registro="",
    somente_alertas=False,
):
    sql = """
        SELECT
            mp.*,
            p.codigo_peca,
            p.descricao AS peca_descricao,
            p.categoria AS peca_categoria,
            p.unidade AS peca_unidade,
            p.fornecedor AS peca_fornecedor,
            p.tipo_maquina AS peca_tipo_maquina,
            m.horimetro_atual AS maquina_horimetro_atual,
            m.descricao AS maquina_descricao,
            m.tipo_maquina AS maquina_tipo,
            m.id_categoria AS maquina_id_categoria
        FROM `check_maquinas`.`manutencao_maquina_pecas` mp
        LEFT JOIN `check_maquinas`.`manutencao_pecas` p
            ON p.id = mp.id_peca
        LEFT JOIN `check_maquinas`.`maquinas` m
            ON m.id_maquina = mp.id_maquina
           AND CONVERT(m.codigo USING utf8mb4) COLLATE utf8mb4_unicode_ci
             = CONVERT(mp.codigo_maquina USING utf8mb4) COLLATE utf8mb4_unicode_ci
           AND CONVERT(CAST(m.id_filial AS CHAR) USING utf8mb4) COLLATE utf8mb4_unicode_ci
             = CONVERT(CAST(mp.id_filial AS CHAR) USING utf8mb4) COLLATE utf8mb4_unicode_ci
        WHERE 1=1
    """
    params = []
    if _valor_texto(id_registro):
        sql += " AND mp.id = %s"
        params.append(id_registro)
    if _valor_texto(codigo_maquina):
        sql += """
            AND CONVERT(mp.codigo_maquina USING utf8mb4) COLLATE utf8mb4_unicode_ci
              = CONVERT(%s USING utf8mb4) COLLATE utf8mb4_unicode_ci
        """
        params.append(_valor_texto(codigo_maquina))
    if _valor_texto(id_maquina):
        sql += " AND mp.id_maquina = %s"
        params.append(id_maquina)
    if _valor_texto(id_filial):
        sql += """
            AND CONVERT(CAST(mp.id_filial AS CHAR) USING utf8mb4) COLLATE utf8mb4_unicode_ci
              = CONVERT(CAST(%s AS CHAR) USING utf8mb4) COLLATE utf8mb4_unicode_ci
        """
        params.append(id_filial)
    if _valor_texto(id_peca):
        sql += " AND mp.id_peca = %s"
        params.append(id_peca)
    sql += " ORDER BY p.categoria ASC, p.descricao ASC, mp.id ASC"

    with conectar() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

    saida = [_linha_peca_maquina_com_status(r) for r in rows]
    if somente_alertas:
        saida = [r for r in saida if r.get("alertas")]
    return saida


def buscar_peca_da_maquina_por_id(id_registro):
    itens = buscar_pecas_da_maquina(id_registro=id_registro)
    return itens[0] if itens else None


def salvar_peca_da_maquina(payload):
    dados = dict(payload.get("maquinaPeca") or payload.get("maquina_peca") or payload.get("dados") or payload or {})
    id_registro = dados.pop("id", None)

    # O controle de troca será administrado diretamente em manutencao_maquina_pecas.
    # Não usamos controle por horas para vida útil; horímetro fica apenas como dado da última troca.
    for campo in ["vida_util_horas", "proxima_troca_horimetro", "alerta_antecedencia_horas"]:
        dados.pop(campo, None)

    codigo = _valor_texto(dados.get("codigo_maquina"))
    id_filial = _valor_texto(dados.get("id_filial"))

    if codigo and (not _valor_texto(dados.get("id_maquina")) or not id_filial):
        maquina = buscar_maquina_por_codigo(codigo, id_filial=id_filial)
        if maquina:
            dados.setdefault("id_maquina", maquina.get("id_maquina"))
            dados.setdefault("id_filial", str(maquina.get("id_filial")) if maquina.get("id_filial") is not None else None)

    if not dados.get("proxima_troca_data") and dados.get("data_ultima_troca") and dados.get("vida_util_dias"):
        dados["proxima_troca_data"] = _somar_dias(dados.get("data_ultima_troca"), dados.get("vida_util_dias"))

    dados["atualizado_em"] = agora_mysql()
    if id_registro:
        atualizar("manutencao_maquina_pecas", dados, {"id": id_registro})
        return buscar_peca_da_maquina_por_id(id_registro)

    criado = inserir("manutencao_maquina_pecas", dados)
    return buscar_peca_da_maquina_por_id(criado.get("id")) if isinstance(criado, dict) and criado.get("id") else criado


def registrar_troca_peca(payload):
    """Atualiza o controle da própria peça vinculada à máquina.

    O controle da última troca, próxima troca e status fica diretamente
    em manutencao_maquina_pecas.
    """
    dados = dict(payload.get("troca") or payload.get("dados") or payload or {})
    id_maquina_peca = dados.get("id_maquina_peca") or dados.get("idMaquinaPeca") or dados.get("id")
    if not id_maquina_peca:
        raise ValueError("Informe id_maquina_peca para atualizar a troca da peça da máquina.")

    maquina_peca = selecionar_um("manutencao_maquina_pecas", {"id": id_maquina_peca})
    if not maquina_peca:
        raise ValueError("Peça vinculada à máquina não encontrada.")

    data_troca = dados.get("data_troca") or dados.get("dataUltimaTroca") or dados.get("data_ultima_troca") or agora_mysql()
    horimetro = dados.get("horimetro_troca") or dados.get("horimetroUltimaTroca") or dados.get("horimetro_ultima_troca")

    atualizacao = {
        "data_ultima_troca": data_troca,
        "horimetro_ultima_troca": horimetro,
        "status": "EM_DIA",
        "atualizado_em": agora_mysql(),
    }

    if dados.get("quantidade") not in [None, ""]:
        atualizacao["quantidade"] = dados.get("quantidade")
    if dados.get("vida_util_dias") not in [None, ""]:
        atualizacao["vida_util_dias"] = dados.get("vida_util_dias")
        maquina_peca["vida_util_dias"] = dados.get("vida_util_dias")
    if dados.get("alerta_antecedencia_dias") not in [None, ""]:
        atualizacao["alerta_antecedencia_dias"] = dados.get("alerta_antecedencia_dias")
    if dados.get("observacao") not in [None, ""]:
        atualizacao["observacao"] = dados.get("observacao")

    motivo_troca = (
        dados.get("motivo_troca")
        or dados.get("motivoTroca")
        or dados.get("origem_troca")
        or dados.get("origemTroca")
    )
    if motivo_troca not in [None, ""]:
        atualizacao["motivo_troca"] = motivo_troca

    id_check_mec = (
        dados.get("id_check_mec")
        or dados.get("idCheckMec")
        or dados.get("id_check_mecanica")
        or dados.get("idCheckMecanica")
    )
    if id_check_mec not in [None, ""]:
        atualizacao["id_check_mec"] = str(id_check_mec)

    if maquina_peca.get("vida_util_dias") not in [None, ""]:
        proxima_data = _somar_dias(data_troca, maquina_peca.get("vida_util_dias"))
        if proxima_data:
            atualizacao["proxima_troca_data"] = proxima_data

    atualizar("manutencao_maquina_pecas", atualizacao, {"id": id_maquina_peca})

    registro_peca = buscar_peca_da_maquina_por_id(id_maquina_peca)
    motivo_normalizado = _valor_texto(motivo_troca).upper().replace(" ", "_")
    if "PREVENTIVA" in motivo_normalizado and registro_peca:
        anexar_peca_historico_preventiva(
            codigo_maquina=registro_peca.get("codigo_maquina"),
            id_maquina=registro_peca.get("id_maquina"),
            id_peca=registro_peca.get("id_peca"),
            nome_peca=registro_peca.get("peca_descricao") or registro_peca.get("codigo_peca"),
            observacao=atualizacao.get("observacao") or "",
        )

    return {
        "maquinaPeca": registro_peca,
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

    pecas = buscar_pecas_da_maquina(codigo_maquina=codigo, id_filial=id_filial)
    servicos = buscar_servicos_manutencao(
        id_filial=id_filial,
        codigo_maquina=codigo,
        limit=200,
    )

    # Anexos documentais podem estar ligados diretamente à máquina OU ao
    # manutencao_servicos.id. As fotos de liberação usam a segunda forma.
    anexos_manutencao = []
    if maquina:
        anexos_manutencao.extend(
            buscar_anexos_manutencao("maquinas", maquina.get("id", ""))
        )

    ids_servicos = [s.get("id") for s in servicos if s.get("id") is not None]
    if ids_servicos:
        placeholders = ",".join(["%s"] * len(ids_servicos))
        sql_anexos_servicos = f"""
            SELECT *
            FROM `check_maquinas`.`manutencao_anexos`
            WHERE `origem_tabela` = 'manutencao_servicos'
              AND `origem_id` IN ({placeholders})
            ORDER BY `criado_em` DESC
            LIMIT 1000
        """
        with conectar() as conn:
            with conn.cursor() as cur:
                cur.execute(sql_anexos_servicos, ids_servicos)
                anexos_manutencao.extend(
                    [
                        normalizar_linha_saida("manutencao_anexos", r)
                        for r in cur.fetchall()
                    ]
                )

    return {
        "maquina": maquina,
        "checks": checks,
        "pendencias": buscar_pendencias_da_maquina(codigo, id_filial=id_filial),
        "servicos": servicos,
        "historicoPreventivas": buscar_historico_preventivas(
            codigo_maquina=codigo,
            id_filial=id_filial,
            limit=500,
        ),
        "checksMecanica": buscar_checks_mecanica(codigo_maquina=codigo, id_filial=id_filial, limit=200),
        "pecas": pecas,
        "trocasPecas": [],
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
        pecas_alerta.extend(buscar_pecas_da_maquina(codigo_maquina=codigo, id_filial=id_filial, somente_alertas=True))

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

            if acao in ["buscarOperadorPorMatricula", "buscarOperador"]:
                return responder(self, 200, {"sucesso": True, "dados": buscar_operador_por_matricula(query_param(query, "matricula", ""))})

            if acao == "buscarOperadores":
                return responder(self, 200, {
                    "sucesso": True,
                    "dados": buscar_operadores(
                        nome=query_param(query, "nome", ""),
                        filial=query_param(query, "filial", ""),
                        apenas_aptos=query_param(query, "apenasAptos", "true").lower() != "false",
                        sincronizar=query_param(query, "sincronizar", "true").lower() != "false",
                        limit=query_param(query, "limit", "500"),
                    ),
                })

            if acao == "buscarOperadorPorNome":
                return responder(self, 200, {
                    "sucesso": True,
                    "dados": buscar_operador_por_nome(
                        query_param(query, "nome", ""),
                        filial=query_param(query, "filial", ""),
                        sincronizar=query_param(query, "sincronizar", "true").lower() != "false",
                    ),
                })

            if acao == "sincronizarOperadoresRH":
                return responder(self, 200, {
                    "sucesso": True,
                    "dados": sincronizar_operadores_rh(),
                })

            if acao == "buscarFiliais":
                return responder(self, 200, {"sucesso": True, "dados": buscar_filiais()})

            if acao == "buscarMaquinas":
                return responder(self, 200, {"sucesso": True, "dados": buscar_maquinas(query_param(query, "idFilial", ""))})

            if acao == "buscarChecks":
                return responder(self, 200, {"sucesso": True, "dados": buscar_checks(query_param(query, "idFilial", ""), query_param(query, "statusCheck", ""))})

            if acao in ["buscarChecksOperadorAuxiliar", "buscarChecksAuxiliares"]:
                return responder(self, 200, {
                    "sucesso": True,
                    "dados": buscar_checks_operador_auxiliar(
                        tipo_checklist=query_param(query, "tipoChecklist", ""),
                        codigo_maquina=query_param(query, "codigoMaquina", ""),
                        tipo_maquina=query_param(query, "tipoMaquina", ""),
                        id_filial=query_param(query, "idFilial", ""),
                        status_check=query_param(query, "statusCheck", ""),
                        operador=query_param(query, "operador", ""),
                        limit=query_param(query, "limit", "500"),
                    ),
                })

            if acao == "buscarCheckOperadorAuxiliarPorId":
                return responder(self, 200, {
                    "sucesso": True,
                    "dados": buscar_check_operador_auxiliar_por_id(
                        id_check=query_param(query, "idCheck", ""),
                        tipo_checklist=query_param(query, "tipoChecklist", ""),
                        codigo_maquina=query_param(query, "codigoMaquina", ""),
                        tipo_maquina=query_param(query, "tipoMaquina", ""),
                        id_filial=query_param(query, "idFilial", ""),
                    ),
                })

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

            if acao == "buscarAnexosOperador":
                return responder(self, 200, {
                    "sucesso": True,
                    "dados": buscar_anexos_operador(
                        query_param(query, "origemTabela", ""),
                        query_param(query, "origemId", ""),
                    ),
                })

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

            if acao == "buscarServicoOficinaAberto":
                return responder(self, 200, {"sucesso": True, "dados": buscar_servico_oficina_aberto(
                    query_param(query, "codigoMaquina", ""),
                    query_param(query, "idFilial", ""),
                )})

            if acao == "buscarHistoricoPreventivas":
                return responder(self, 200, {"sucesso": True, "dados": buscar_historico_preventivas(
                    codigo_maquina=query_param(query, "codigoMaquina", ""),
                    id_maquina=query_param(query, "idMaquina", ""),
                    id_filial=query_param(query, "idFilial", ""),
                    status=query_param(query, "status", ""),
                    data_inicio=query_param(query, "dataInicio", ""),
                    data_fim=query_param(query, "dataFim", ""),
                    limit=query_param(query, "limit", "1000"),
                )})

            if acao == "buscarServicosManutencao":
                return responder(self, 200, {"sucesso": True, "dados": buscar_servicos_manutencao(
                    id_filial=query_param(query, "idFilial", ""),
                    codigo_maquina=query_param(query, "codigoMaquina", ""),
                    id_pendencia=query_param(query, "idPendencia", ""),
                    id_check=query_param(query, "idCheck", ""),
                    tipo_servico=query_param(query, "tipoServico", ""),
                    status_servico=query_param(query, "statusServico", ""),
                    data_inicio=query_param(query, "dataInicio", ""),
                    data_fim=query_param(query, "dataFim", ""),
                    limit=query_param(query, "limit", "500"),
                )})

            if acao == "buscarPecasManutencao":
                return responder(self, 200, {"sucesso": True, "dados": buscar_pecas_manutencao(
                    busca=query_param(query, "busca", ""),
                    ativo=query_param(query, "ativo", ""),
                    categoria=query_param(query, "categoria", ""),
                    tipo_maquina=query_param(query, "tipoMaquina", ""),
                    limit=query_param(query, "limit", "1000"),
                )})

            if acao == "buscarPecasDaMaquina":
                return responder(self, 200, {"sucesso": True, "dados": buscar_pecas_da_maquina(
                    codigo_maquina=query_param(query, "codigoMaquina", ""),
                    id_maquina=query_param(query, "idMaquina", ""),
                    id_peca=query_param(query, "idPeca", ""),
                    id_filial=query_param(query, "idFilial", ""),
                    somente_alertas=query_param(query, "somenteAlertas", "false").lower() in ["1", "true", "sim"],
                )})

            if acao == "buscarTrocasPecas":
                return responder(self, 200, {"sucesso": True, "dados": []})

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

            if acao == "buscarCheckMecanica":
                return responder(self, 200, {"sucesso": True, "dados": buscar_check_mecanica(
                    id_servico=query_param(query, "idServico", ""),
                )})

            if acao == "buscarChecksMecanica":
                return responder(self, 200, {"sucesso": True, "dados": buscar_checks_mecanica(
                    codigo_maquina=query_param(query, "codigoMaquina", ""),
                    id_filial=query_param(query, "idFilial", ""),
                    limit=query_param(query, "limit", "200"),
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

            if acao in ["buscarOperadorPorMatricula", "buscarOperador"]:
                dados = body.get("dados") if isinstance(body.get("dados"), dict) else {}
                return responder(self, 200, {"sucesso": True, "dados": buscar_operador_por_matricula(body.get("matricula", "") or dados.get("matricula", ""))})

            if acao == "buscarOperadores":
                dados = body.get("dados") if isinstance(body.get("dados"), dict) else {}
                return responder(self, 200, {
                    "sucesso": True,
                    "dados": buscar_operadores(
                        nome=body.get("nome", "") or dados.get("nome", ""),
                        filial=body.get("filial", "") or dados.get("filial", ""),
                        apenas_aptos=body.get("apenasAptos", dados.get("apenasAptos", True)) is not False,
                        sincronizar=body.get("sincronizar", dados.get("sincronizar", True)) is not False,
                        limit=body.get("limit", dados.get("limit", 500)),
                    ),
                })

            if acao == "buscarOperadorPorNome":
                dados = body.get("dados") if isinstance(body.get("dados"), dict) else {}
                return responder(self, 200, {
                    "sucesso": True,
                    "dados": buscar_operador_por_nome(
                        body.get("nome", "") or dados.get("nome", ""),
                        filial=body.get("filial", "") or dados.get("filial", ""),
                        sincronizar=body.get("sincronizar", dados.get("sincronizar", True)) is not False,
                    ),
                })

            if acao == "sincronizarOperadoresRH":
                return responder(self, 200, {
                    "sucesso": True,
                    "dados": sincronizar_operadores_rh(),
                })

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

            if acao == "inserirAnexoOperador":
                return responder(self, 200, {
                    "sucesso": True,
                    "dados": inserir_anexo_operador(body.get("dados", body)),
                })

            if acao == "inserirAnexoCheck":
                return responder(self, 200, {
                    "sucesso": True,
                    "dados": inserir_anexo_check_empi(body.get("dados", body)),
                })

            if acao == "salvarCheck":
                dados_check = body.get("check") or body.get("dados") or {}

                return responder(self, 200, {
                    "sucesso": True,
                    "dados": salvar_check(dados_check),
                })


            if acao in [
                "salvarCheckOperadorAuxiliar",
                "salvarCheckAuxiliar",
                "salvarCheckPaleteira",
                "salvarCheckTranspaleteira",
                "salvarCheckLimpeza",
            ]:
                dados_check = body.get("check") or body.get("dados") or {}

                tipo_checklist = body.get("tipoChecklist", "")
                if acao == "salvarCheckPaleteira":
                    tipo_checklist = "PLT-MANUAL"
                elif acao == "salvarCheckTranspaleteira":
                    tipo_checklist = "PLT-ELETRICA"
                elif acao == "salvarCheckLimpeza":
                    tipo_checklist = "LIMP"

                return responder(self, 200, {
                    "sucesso": True,
                    "dados": salvar_check_operador_auxiliar(
                        tipo_checklist=tipo_checklist,
                        dados_check=dados_check,
                        tipo_maquina=body.get("tipoMaquina", ""),
                    ),
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


            if acao == "salvarHistoricoPreventiva":
                return responder(self, 200, {
                    "sucesso": True,
                    "dados": salvar_historico_preventiva(body.get("dados", body)),
                })

            if acao == "salvarServicoManutencao":
                return responder(self, 200, {
                    "sucesso": True,
                    "dados": salvar_servico_manutencao(body.get("dados", body)),
                })

            if acao == "iniciarManutencaoOficina":
                return responder(self, 200, {
                    "sucesso": True,
                    "dados": iniciar_manutencao_oficina(body.get("dados", body)),
                })

            if acao == "finalizarManutencaoOficina":
                return responder(self, 200, {
                    "sucesso": True,
                    "dados": finalizar_manutencao_oficina(body.get("dados", body)),
                })

            if acao == "salvarCheckMecanica":
                dados = body.get("dados", body)
                return responder(self, 200, {
                    "sucesso": True,
                    "dados": salvar_check_mecanica(dados.get("id_servico") or dados.get("idServico"), dados.get("itens", [])),
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

            if acao in ["atualizarControlePreventivaMaquina", "atualizarControlePreventivaMensal"]:
                return responder(self, 200, {"sucesso": True, "dados": atualizar_controle_preventiva_maquina(
                    codigo_maquina=body.get("codigoMaquina", ""),
                    id_filial=body.get("idFilial", ""),
                    ultima_preventiva=body.get("ultimaPreventiva") or body.get("ultimaManutencao"),
                    proxima_preventiva=body.get("proximaPreventiva"),
                )})

            if acao == "finalizarTurno":
                return responder(self, 200, {"sucesso": True, "dados": finalizar_turno(
                    id_check=body.get("idCheck"),
                    codigo_maquina=body.get("codigoMaquina", ""),
                    id_filial=body.get("idFilial"),
                    horimetro_final=body.get("horimetroFinal"),
                    carga_final=body.get("cargaFinal", body.get("carga_atual")),
                    ultima_carga_realizada=body.get("ultimaCargaRealizada", body.get("ultima_carga_realizada")),
                )})

            if acao in [
                "finalizarCheckOperadorAuxiliar",
                "finalizarCheckAuxiliar",
                "finalizarTurnoAuxiliar",
            ]:
                return responder(self, 200, {
                    "sucesso": True,
                    "dados": finalizar_check_operador_auxiliar(
                        tipo_checklist=body.get("tipoChecklist", ""),
                        id_check=body.get("idCheck"),
                        codigo_maquina=body.get("codigoMaquina", ""),
                        id_filial=body.get("idFilial", ""),
                        tipo_maquina=body.get("tipoMaquina", ""),
                        horimetro_final=body.get("horimetroFinal"),
                        carga_final=body.get(
                            "cargaFinal",
                            body.get("carga_final"),
                        ),
                        ultima_carga_realizada=body.get(
                            "ultimaCargaRealizada",
                            body.get("ultima_carga_realizada"),
                        ),
                    ),
                })

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
