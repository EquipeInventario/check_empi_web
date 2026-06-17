import { verificarConexaoEvolution } from './_evolution.js';

function aplicarCors(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
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

export default async function handler(req, res) {
  if (aplicarCors(req, res)) return;

  if (req.method !== 'GET' && req.method !== 'POST') {
    return res.status(405).json({
      ok: false,
      erro: 'Método não permitido.',
    });
  }

  try {
    if (!validarToken(req)) {
      return res.status(401).json({
        ok: false,
        erro: 'Token inválido.',
      });
    }

    const status = await verificarConexaoEvolution();

    return res.status(200).json({
      ok: true,
      conectado: status.conectado === true,
      evolution: status,
      mensagem: status.conectado
        ? 'Evolution API ativa e WhatsApp conectado.'
        : 'Evolution API respondeu, mas WhatsApp ainda não está conectado.',
    });
  } catch (e) {
    return res.status(500).json({
      ok: false,
      conectado: false,
      erro: 'Erro ao preparar WhatsApp.',
      detalhe: String(e),
    });
  }
}
