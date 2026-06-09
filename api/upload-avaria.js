import { put } from '@vercel/blob';
import formidable from 'formidable';
import fs from 'fs';

export const config = {
  api: {
    bodyParser: false,
  },
};

function setCorsHeaders(res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS, GET');
  res.setHeader(
    'Access-Control-Allow-Headers',
    'Content-Type, Authorization'
  );
}

function getCampo(fields, nome, padrao = '') {
  const valor = fields[nome];

  if (Array.isArray(valor)) {
    return valor[0]?.toString() || padrao;
  }

  return valor?.toString() || padrao;
}

function normalizarTexto(texto) {
  return texto
    .toString()
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/_+/g, '_')
    .replace(/^_|_$/g, '');
}

export default async function handler(req, res) {
  setCorsHeaders(res);

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method === 'GET') {
    return res.status(405).json({
      sucesso: false,
      erro: 'Método não permitido. Use POST para enviar imagem.',
    });
  }

  if (req.method !== 'POST') {
    return res.status(405).json({
      sucesso: false,
      erro: 'Método não permitido',
    });
  }

  try {
    const form = formidable({
      multiples: false,
      keepExtensions: true,
      maxFileSize: 8 * 1024 * 1024,
    });

    const [fields, files] = await form.parse(req);

    const arquivo = Array.isArray(files.file) ? files.file[0] : files.file;

    if (!arquivo) {
      return res.status(400).json({
        sucesso: false,
        erro: 'Nenhum arquivo enviado no campo file.',
      });
    }

    const empilhadeira = getCampo(
      fields,
      'empilhadeira',
      'sem_empilhadeira'
    );

    const idCheck = getCampo(fields, 'id_check', 'sem_check');
    const categoria = getCampo(fields, 'categoria', 'geral');
    const item = getCampo(fields, 'item', 'item');

    const buffer = fs.readFileSync(arquivo.filepath);

    const agora = new Date();
    const ano = agora.getFullYear();
    const mes = String(agora.getMonth() + 1).padStart(2, '0');

    const categoriaLimpa = normalizarTexto(categoria);
    const itemLimpo = normalizarTexto(item);
    const empilhadeiraLimpa = normalizarTexto(empilhadeira);

    const extensao = arquivo.mimetype === 'image/png' ? 'png' : 'jpg';

    const nomeArquivo =
      `avarias/${ano}/${mes}/emp_${empilhadeiraLimpa}/` +
      `check_${idCheck}_${categoriaLimpa}_${itemLimpo}_${Date.now()}.${extensao}`;

    const blob = await put(nomeArquivo, buffer, {
      access: 'public',
      contentType: arquivo.mimetype || 'image/jpeg',
      addRandomSuffix: false,
    });

    return res.status(200).json({
      sucesso: true,
      url: blob.url,
      pathname: blob.pathname,
      tamanho_bytes: arquivo.size || buffer.length,
      content_type: arquivo.mimetype || 'image/jpeg',
    });
  } catch (error) {
    console.error('ERRO_UPLOAD_AVARIA:', error);

    return res.status(500).json({
      sucesso: false,
      erro: 'Erro ao enviar imagem para o Vercel Blob',
      detalhe: error?.message || String(error),
      name: error?.name || null,
    });
  }
}
