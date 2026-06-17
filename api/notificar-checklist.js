import { createClient } from '@supabase/supabase-js';

import { enviarTextoEvolution } from './_evolution.js';

const ALERTA_PREVENTIVA_HORAS = 20;

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

function calcularPreventiva(maquina) {
  const horimetroAtual = paraNumero(maquina.horimetro_atual);
  const horimetroManutencao = paraNumero(maquina.horimetro_manutencao);
  const calcBase = paraNumero(maquina.calc_base);

  if (horimetroAtual === null || horimetroManutencao === null || calcBase === null) {
    return null;
  }

  if (calcBase <= 0) return null;

  const proxima = horimetroManutencao + calcBase;
  const faltam = proxima - horimetroAtual;

  if (faltam > ALERTA_PREVENTIVA_HORAS) {
    return null;
  }

  return {
    codigo: limparTexto(maquina.codigo),
    descricao: limparTexto(maquina.descricao),
    horimetroAtual,
    horimetroManutencao,
    calcBase,
    proxima,
    faltam,
    vencida: faltam <= 0,
  };
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

    const { id_check, id_filial } = req.body || {};

    if (!id_check) {
      return res.status(400).json({
        ok: false,
        erro: 'id_check é obrigatório.',
      });
    }

    const supabaseUrl = process.env.SUPABASE_URL;
    const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

    if (!supabaseUrl || !supabaseKey) {
      return res.status(500).json({
        ok: false,
        erro: 'SUPABASE_URL ou SUPABASE_SERVICE_ROLE_KEY não configurados.',
      });
    }

    const supabase = createClient(supabaseUrl, supabaseKey);

    const { data: check, error: erroCheck } = await supabase
      .from('check_empi')
      .select(
        'id, empilhadeira, operador, turno, id_filial, resultado_check, horimetro_inicial',
      )
      .eq('id', id_check)
      .single();

    if (erroCheck || !check) {
      return res.status(404).json({
        ok: false,
        erro: 'Checklist não encontrado.',
        detalhe: erroCheck?.message,
      });
    }

    const idFilialFinal = id_filial || check.id_filial;

    const { data: pendenciasDoCheck, error: erroPendenciasCheck } =
      await supabase
        .from('check_empi_pendencias')
        .select('id')
        .eq('id_check', id_check)
        .eq('id_filial', idFilialFinal)
        .in('status_pendencia', ['ABERTA', 'EM_ANALISE'])
        .or('resolvido.is.false,resolvido.is.null');

    if (erroPendenciasCheck) {
      return res.status(500).json({
        ok: false,
        erro: 'Erro ao verificar pendências do checklist.',
        detalhe: erroPendenciasCheck.message,
      });
    }

    const { data: maquinaCheck } = await supabase
      .from('maquinas')
      .select(
        'codigo, descricao, id_filial, horimetro_atual, horimetro_manutencao, calc_base',
      )
      .eq('codigo', check.empilhadeira)
      .eq('id_filial', idFilialFinal)
      .maybeSingle();

    const preventivaMaquinaCheck = maquinaCheck
      ? calcularPreventiva(maquinaCheck)
      : null;

    const checklistGerouPendencia =
      Array.isArray(pendenciasDoCheck) && pendenciasDoCheck.length > 0;

    const checklistGerouPreventiva = preventivaMaquinaCheck !== null;

    if (!checklistGerouPendencia && !checklistGerouPreventiva) {
      return res.status(200).json({
        ok: true,
        enviado: false,
        motivo: 'Checklist sem pendência e sem alerta preventivo.',
      });
    }

    const { data: pendenciasAbertas, error: erroPendenciasAbertas } =
      await supabase
        .from('check_empi_pendencias')
        .select(
          'id, empilhadeira, categoria, item, observacao, status_pendencia, criado_em',
        )
        .eq('id_filial', idFilialFinal)
        .in('status_pendencia', ['ABERTA', 'EM_ANALISE'])
        .or('resolvido.is.false,resolvido.is.null')
        .order('criado_em', { ascending: false });

    if (erroPendenciasAbertas) {
      return res.status(500).json({
        ok: false,
        erro: 'Erro ao buscar pendências abertas.',
        detalhe: erroPendenciasAbertas.message,
      });
    }

    const { data: maquinas, error: erroMaquinas } = await supabase
      .from('maquinas')
      .select(
        'codigo, descricao, id_filial, horimetro_atual, horimetro_manutencao, calc_base',
      )
      .eq('id_filial', idFilialFinal)
      .order('codigo', { ascending: true });

    if (erroMaquinas) {
      return res.status(500).json({
        ok: false,
        erro: 'Erro ao buscar máquinas para preventiva.',
        detalhe: erroMaquinas.message,
      });
    }

    const preventivas = (maquinas || [])
      .map(calcularPreventiva)
      .filter(Boolean)
      .sort((a, b) => a.faltam - b.faltam);

    let filialNome = '';

    const { data: filial } = await supabase
      .from('filial')
      .select('filial')
      .eq('id', idFilialFinal)
      .maybeSingle();

    if (filial?.filial) {
      filialNome = limparTexto(filial.filial);
    }

    const mensagem = montarMensagem({
      filialNome,
      check,
      pendenciasAbertas: pendenciasAbertas || [],
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
      total_pendencias: pendenciasAbertas?.length || 0,
      total_preventivas: preventivas.length,
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
