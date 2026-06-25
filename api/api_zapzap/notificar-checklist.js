import mysql from 'mysql2/promise';

import { enviarTextoEvolution } from './_evolution.js';

const ALERTA_PREVENTIVA_HORAS = 20;
const DB_CHECK = process.env.MYSQL_DATABASE || 'check_maquinas';

let poolMysql = null;

function aplicarCors(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader(
    'Access-Control-Allow-Headers',
    'Content-Type, x-checkempi-token',
  );

  if (req.method === 'OPTIONS') {
    res.status(200).end();
    return true;
  }

  return false;
}

function validarToken(req) {
  const tokenEsperado = process.env.CHECKEMPI_API_TOKEN;

  if (!tokenEsperado) return true;

  const tokenRecebido = req.headers['x-checkempi-token'];

  return tokenRecebido === tokenEsperado;
}

function limparTexto(valor) {
  if (valor === null || valor === undefined) return '';
  return String(valor).trim();
}

function temValor(valor) {
  return limparTexto(valor) !== '';
}

function paraNumero(valor) {
  if (valor === null || valor === undefined || valor === '') return null;

  const numero = Number(String(valor).replace(',', '.'));

  if (Number.isNaN(numero)) return null;

  return numero;
}

function formatarNumero(valor) {
  const numero = paraNumero(valor);

  if (numero === null) return '-';

  return numero.toLocaleString('pt-BR', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });
}

function obterBody(req) {
  if (!req.body) return {};

  if (typeof req.body === 'string') {
    try {
      return JSON.parse(req.body);
    } catch (_) {
      return {};
    }
  }

  return req.body;
}

function validarConfigMysql() {
  const faltando = [];

  if (!process.env.MYSQL_HOST) faltando.push('MYSQL_HOST');
  if (!process.env.MYSQL_USER) faltando.push('MYSQL_USER');
  if (!process.env.MYSQL_PASSWORD) faltando.push('MYSQL_PASSWORD');
  if (!DB_CHECK) faltando.push('MYSQL_DATABASE');

  if (faltando.length > 0) {
    throw new Error(`Variáveis MySQL ausentes: ${faltando.join(', ')}`);
  }
}

function getPoolMysql() {
  validarConfigMysql();

  if (!poolMysql) {
    poolMysql = mysql.createPool({
      host: process.env.MYSQL_HOST,
      port: Number(process.env.MYSQL_PORT || 3306),
      user: process.env.MYSQL_USER,
      password: process.env.MYSQL_PASSWORD,
      database: DB_CHECK,
      waitForConnections: true,
      connectionLimit: 4,
      queueLimit: 0,
      charset: 'utf8mb4',
      dateStrings: true,
      enableKeepAlive: true,
      keepAliveInitialDelay: 0,
    });
  }

  return poolMysql;
}

async function consultar(sql, params = []) {
  const pool = getPoolMysql();
  const [rows] = await pool.execute(sql, params);
  return rows || [];
}

async function consultarUm(sql, params = []) {
  const rows = await consultar(sql, params);
  return rows.length > 0 ? rows[0] : null;
}

function calcularPreventiva(maquina) {
  const horimetroAtual = paraNumero(maquina.horimetro_atual);
  const horimetroManutencao = paraNumero(maquina.horimetro_manutencao);
  const intervaloPreventiva = paraNumero(maquina.intervalo_preventiva_horas);
  let proximaManutencao = paraNumero(maquina.prox_manutencao_hora);

  if (horimetroAtual === null) {
    return null;
  }

  if (proximaManutencao === null) {
    if (horimetroManutencao === null || intervaloPreventiva === null) {
      return null;
    }

    if (intervaloPreventiva <= 0) {
      return null;
    }

    proximaManutencao = horimetroManutencao + intervaloPreventiva;
  }

  const faltam = proximaManutencao - horimetroAtual;

  if (faltam > ALERTA_PREVENTIVA_HORAS) {
    return null;
  }

  return {
    codigo: limparTexto(maquina.codigo),
    descricao: limparTexto(maquina.descricao),
    horimetroAtual,
    horimetroManutencao,
    intervaloPreventiva,
    proxima: proximaManutencao,
    faltam,
    vencida: faltam <= 0,
  };
}

async function buscarCheck(idCheck) {
  return consultarUm(
    `
      SELECT
        id,
        empilhadeira,
        operador,
        turno,
        id_filial,
        resultado_check,
        horimetro_inicial
      FROM \`${DB_CHECK}\`.\`check_empi\`
      WHERE id = ?
      LIMIT 1
    `,
    [idCheck],
  );
}

async function buscarPendenciasDoCheckAbertas(idCheck, idFilial) {
  const params = [idCheck];

  let sql = `
    SELECT id
    FROM \`${DB_CHECK}\`.\`check_empi_pendencias\`
    WHERE id_check = ?
      AND status_pendencia IN ('ABERTA', 'EM_ANALISE')
      AND (resolvido = 0 OR resolvido IS NULL)
  `;

  if (temValor(idFilial)) {
    sql += ' AND id_filial = ?';
    params.push(idFilial);
  }

  sql += ' LIMIT 1';

  return consultar(sql, params);
}

async function buscarMaquinaDoCheck(codigoMaquina, idFilial) {
  if (!temValor(codigoMaquina)) return null;

  const params = [codigoMaquina];

  let sql = `
    SELECT
      codigo,
      descricao,
      id_filial,
      horimetro_atual,
      horimetro_manutencao,
      intervalo_preventiva_horas,
      prox_manutencao_hora
    FROM \`${DB_CHECK}\`.\`maquinas\`
    WHERE codigo = ?
  `;

  if (temValor(idFilial)) {
    sql += ' AND id_filial = ?';
    params.push(idFilial);
  }

  sql += ' ORDER BY id ASC LIMIT 1';

  return consultarUm(sql, params);
}

async function buscarPendenciasAbertas(idFilial, idCheckFallback) {
  const params = [];

  let sql = `
    SELECT
      id,
      empilhadeira,
      categoria,
      item,
      observacao,
      status_pendencia,
      criado_em
    FROM \`${DB_CHECK}\`.\`check_empi_pendencias\`
    WHERE status_pendencia IN ('ABERTA', 'EM_ANALISE')
      AND (resolvido = 0 OR resolvido IS NULL)
  `;

  if (temValor(idFilial)) {
    sql += ' AND id_filial = ?';
    params.push(idFilial);
  } else if (temValor(idCheckFallback)) {
    sql += ' AND id_check = ?';
    params.push(idCheckFallback);
  }

  sql += ' ORDER BY criado_em DESC';

  return consultar(sql, params);
}

async function buscarMaquinasPreventiva(idFilial, codigoFallback) {
  const params = [];

  let sql = `
    SELECT
      codigo,
      descricao,
      id_filial,
      horimetro_atual,
      horimetro_manutencao,
      intervalo_preventiva_horas,
      prox_manutencao_hora
    FROM \`${DB_CHECK}\`.\`maquinas\`
    WHERE ativo IN (0, 1)
  `;

  if (temValor(idFilial)) {
    sql += ' AND id_filial = ?';
    params.push(idFilial);
  } else if (temValor(codigoFallback)) {
    sql += ' AND codigo = ?';
    params.push(codigoFallback);
  } else {
    return [];
  }

  sql += ' ORDER BY codigo ASC';

  return consultar(sql, params);
}

async function buscarNomeFilial(idFilial) {
  if (!temValor(idFilial)) return '';

  const filial = await consultarUm(
    `
      SELECT filial, cidade, estado
      FROM \`indicadores_matriz\`.\`filiais\`
      WHERE id = ?
      LIMIT 1
    `,
    [idFilial],
  );

  if (!filial) return '';

  const nome = limparTexto(filial.filial);
  const cidade = limparTexto(filial.cidade);
  const estado = limparTexto(filial.estado);

  if (nome && cidade && estado) return `${nome} - ${cidade}/${estado}`;
  if (nome && cidade) return `${nome} - ${cidade}`;
  return nome;
}

function montarMensagem({ filialNome, check, pendenciasAbertas, preventivas }) {
  const linhas = [];

  linhas.push('⚠️ *Alerta Check Empi*');
  linhas.push('');

  if (filialNome) {
    linhas.push(`Filial: ${filialNome}`);
  }

  linhas.push(`${pendenciasAbertas.length} pendência(s) aberta(s)/em análise.`);
  linhas.push(`${preventivas.length} alerta(s) preventivo(s).`);
  linhas.push('');

  if (check) {
    linhas.push('*Checklist que acionou o alerta:*');
    linhas.push(`Máquina: ${limparTexto(check.empilhadeira)}`);

    if (limparTexto(check.operador)) {
      linhas.push(`Operador: ${limparTexto(check.operador)}`);
    }

    if (limparTexto(check.turno)) {
      linhas.push(`Turno: ${limparTexto(check.turno)}`);
    }

    linhas.push('');
  }

  if (pendenciasAbertas.length > 0) {
    linhas.push('*Pendências:*');

    for (const pendencia of pendenciasAbertas.slice(0, 15)) {
      linhas.push(
        `🔧 Máquina ${limparTexto(pendencia.empilhadeira)} - ${limparTexto(
          pendencia.item,
        )}`,
      );

      if (limparTexto(pendencia.categoria)) {
        linhas.push(`Categoria: ${limparTexto(pendencia.categoria)}`);
      }

      if (limparTexto(pendencia.status_pendencia)) {
        linhas.push(`Status: ${limparTexto(pendencia.status_pendencia)}`);
      }

      linhas.push('');
    }

    if (pendenciasAbertas.length > 15) {
      linhas.push(`...e mais ${pendenciasAbertas.length - 15} pendência(s).`);
      linhas.push('');
    }
  }

  if (preventivas.length > 0) {
    linhas.push('*Preventivas próximas ou vencidas:*');

    for (const preventiva of preventivas.slice(0, 10)) {
      const icone = preventiva.vencida ? '🔴' : '🟠';
      const status = preventiva.vencida ? 'VENCIDA' : 'PRÓXIMA';

      linhas.push(`${icone} Máquina ${preventiva.codigo} - ${status}`);

      if (preventiva.descricao) {
        linhas.push(preventiva.descricao);
      }

      linhas.push(`Atual: ${formatarNumero(preventiva.horimetroAtual)} h`);
      linhas.push(`Próxima: ${formatarNumero(preventiva.proxima)} h`);

      if (preventiva.intervaloPreventiva !== null) {
        linhas.push(
          `Intervalo: ${formatarNumero(preventiva.intervaloPreventiva)} h`,
        );
      }

      if (preventiva.vencida) {
        linhas.push(`Excedeu: ${formatarNumero(Math.abs(preventiva.faltam))} h`);
      } else {
        linhas.push(`Faltam: ${formatarNumero(preventiva.faltam)} h`);
      }

      linhas.push('');
    }

    if (preventivas.length > 10) {
      linhas.push(`...e mais ${preventivas.length - 10} alerta(s) preventivo(s).`);
      linhas.push('');
    }
  }

  linhas.push('Acesse o Check Empi Web para verificar.');

  return linhas.join('\n').trim();
}

export default async function handler(req, res) {
  if (aplicarCors(req, res)) return;

  if (req.method !== 'POST') {
    return res.status(405).json({
      ok: false,
      erro: 'Método não permitido. Use POST.',
    });
  }

  try {
    if (!validarToken(req)) {
      return res.status(401).json({
        ok: false,
        erro: 'Token inválido.',
      });
    }

    const body = obterBody(req);
    const { id_check, id_filial } = body || {};

    if (!id_check) {
      return res.status(400).json({
        ok: false,
        erro: 'id_check é obrigatório.',
      });
    }

    const check = await buscarCheck(id_check);

    if (!check) {
      return res.status(404).json({
        ok: false,
        erro: 'Checklist não encontrado.',
      });
    }

    const idFilialFinal = limparTexto(id_filial || check.id_filial);
    const codigoMaquina = limparTexto(check.empilhadeira);

    const pendenciasDoCheck = await buscarPendenciasDoCheckAbertas(
      id_check,
      idFilialFinal,
    );

    const maquinaCheck = await buscarMaquinaDoCheck(codigoMaquina, idFilialFinal);
    const preventivaMaquinaCheck = maquinaCheck
      ? calcularPreventiva(maquinaCheck)
      : null;

    const checklistGerouPendencia = pendenciasDoCheck.length > 0;
    const checklistGerouPreventiva = preventivaMaquinaCheck !== null;

    if (!checklistGerouPendencia && !checklistGerouPreventiva) {
      return res.status(200).json({
        ok: true,
        enviado: false,
        motivo: 'Checklist sem pendência e sem alerta preventivo.',
      });
    }

    const pendenciasAbertas = await buscarPendenciasAbertas(
      idFilialFinal,
      id_check,
    );

    let preventivas = [];
    let erroPreventiva = null;

    try {
      const maquinas = await buscarMaquinasPreventiva(idFilialFinal, codigoMaquina);
      preventivas = maquinas
        .map(calcularPreventiva)
        .filter(Boolean)
        .sort((a, b) => a.faltam - b.faltam);
    } catch (e) {
      erroPreventiva = String(e);
    }

    const filialNome = await buscarNomeFilial(idFilialFinal);

    const mensagem = montarMensagem({
      filialNome,
      check,
      pendenciasAbertas,
      preventivas,
    });

    const destinos = String(process.env.WHATSAPP_DESTINOS || '')
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean);

    if (destinos.length === 0) {
      return res.status(500).json({
        ok: false,
        erro: 'Nenhum destino configurado em WHATSAPP_DESTINOS.',
      });
    }

    const envios = [];

    for (const telefone of destinos) {
      try {
        const retorno = await enviarTextoEvolution({
          telefone,
          mensagem,
        });

        envios.push({
          telefone,
          ok: true,
          retorno,
        });
      } catch (e) {
        envios.push({
          telefone,
          ok: false,
          erro: String(e),
        });
      }
    }

    const algumEnviado = envios.some((item) => item.ok);

    return res.status(200).json({
      ok: algumEnviado,
      enviado: algumEnviado,
      banco: 'MYSQL',
      total_pendencias: pendenciasAbertas.length,
      total_preventivas: preventivas.length,
      erro_preventiva: erroPreventiva,
      destinos: envios,
      mensagem,
    });
  } catch (e) {
    return res.status(500).json({
      ok: false,
      erro: 'Erro interno ao notificar checklist.',
      detalhe: String(e),
    });
  }
}
