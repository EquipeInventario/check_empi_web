import {
  BlobSASPermissions,
  BlobServiceClient,
  StorageSharedKeyCredential,
  generateBlobSASQueryParameters,
} from '@azure/storage-blob';
import formidable from 'formidable';
import fs from 'fs';

export const config = {
  api: {
    bodyParser: false,
  },
};

const PASTA_PADRAO = 'avarias';
const CONTAINER_PADRAO = 'check-empi-avarias';
const LIMITE_UPLOAD_MB = Number(process.env.AZURE_UPLOAD_MAX_MB || 20);

function setCorsHeaders(res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, GET, OPTIONS');
  res.setHeader(
    'Access-Control-Allow-Headers',
    'Content-Type, Authorization, X-API-Token, x-checkempi-token',
  );
}

function responder(res, status, body) {
  setCorsHeaders(res);
  return res.status(status).json(body);
}

function limparBaseUrl(url) {
  return String(url || '').trim().replace(/\/+$/, '');
}

function getCampo(fields, nome, padrao = '') {
  const valor = fields?.[nome];

  if (Array.isArray(valor)) {
    return valor[0]?.toString() || padrao;
  }

  return valor?.toString() || padrao;
}

function getCampoAlternativo(fields, nomes, padrao = '') {
  for (const nome of nomes) {
    const valor = getCampo(fields, nome, '');
    if (String(valor || '').trim()) return valor;
  }
  return padrao;
}

function normalizarTexto(texto) {
  return String(texto || '')
    .trim()
    .replace(/([a-z0-9])([A-Z])/g, '$1_$2')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/_+/g, '_')
    .replace(/^_|_$/g, '');
}

function obterExtensao(mimetype, nomeArquivo = '') {
  const tipo = String(mimetype || '').toLowerCase();
  const nome = String(nomeArquivo || '').toLowerCase();

  if (tipo.includes('image/png') || nome.endsWith('.png')) return 'png';
  if (tipo.includes('image/webp') || nome.endsWith('.webp')) return 'webp';
  if (tipo.includes('image/gif') || nome.endsWith('.gif')) return 'gif';
  if (tipo.includes('video/webm') || nome.endsWith('.webm')) return 'webm';
  if (tipo.includes('video/quicktime') || nome.endsWith('.mov')) return 'mov';
  if (tipo.includes('video/mp4') || nome.endsWith('.mp4')) return 'mp4';

  return 'jpg';
}

function contentTypePorExtensao(extensao) {
  if (extensao === 'png') return 'image/png';
  if (extensao === 'webp') return 'image/webp';
  if (extensao === 'gif') return 'image/gif';
  if (extensao === 'webm') return 'video/webm';
  if (extensao === 'mov') return 'video/quicktime';
  if (extensao === 'mp4') return 'video/mp4';
  return 'image/jpeg';
}

function obterPastaUpload(pasta) {
  const pastaLimpa = normalizarTexto(pasta || PASTA_PADRAO) || PASTA_PADRAO;

  const aliases = {
    avaria: 'avarias',
    avarias: 'avarias',
    pendencia: 'avarias',
    pendencias: 'avarias',

    pos_conferencia: 'pos_conferencia',
    posconferencia: 'pos_conferencia',
    pos_conf: 'pos_conferencia',
    posconf: 'pos_conferencia',
    conferencia: 'pos_conferencia',
    checklist: 'pos_conferencia',
    check: 'pos_conferencia',
    foto_checklist: 'pos_conferencia',
    foto_pos_conferencia: 'pos_conferencia',

    pos_uso: 'pos_uso',
    posuso: 'pos_uso',
    uso: 'pos_uso',
    finalizacao: 'pos_uso',
    finalizacao_turno: 'pos_uso',
    pos_turno: 'pos_uso',
    foto_pos_uso: 'pos_uso',
  };

  return aliases[pastaLimpa] || PASTA_PADRAO;
}

function extrairValorConnectionString(connectionString, chave) {
  const partes = String(connectionString || '').split(';');

  for (const parte of partes) {
    const indice = parte.indexOf('=');
    if (indice <= 0) continue;

    const nome = parte.slice(0, indice).trim();
    const valor = parte.slice(indice + 1).trim();

    if (nome.toLowerCase() === chave.toLowerCase()) {
      return valor;
    }
  }

  return '';
}

function getAzureConfig() {
  const connectionString = process.env.AZURE_STORAGE_CONNECTION_STRING;
  const containerName = process.env.AZURE_BLOB_CONTAINER || CONTAINER_PADRAO;

  if (!connectionString) {
    throw new Error('Variável AZURE_STORAGE_CONNECTION_STRING não configurada.');
  }

  if (!containerName) {
    throw new Error('Variável AZURE_BLOB_CONTAINER não configurada.');
  }

  return {
    connectionString,
    containerName,
  };
}

function criarBlobServiceClient() {
  const { connectionString } = getAzureConfig();
  return BlobServiceClient.fromConnectionString(connectionString);
}

function criarSasLeitura({ blobName, minutos = 240 }) {
  const { connectionString, containerName } = getAzureConfig();

  const accountName = extrairValorConnectionString(connectionString, 'AccountName');
  const accountKey = extrairValorConnectionString(connectionString, 'AccountKey');

  if (!accountName || !accountKey) {
    return null;
  }

  const credential = new StorageSharedKeyCredential(accountName, accountKey);

  const agora = new Date();
  const startsOn = new Date(agora.valueOf() - 5 * 60 * 1000);
  const expiresOn = new Date(agora.valueOf() + minutos * 60 * 1000);

  const sas = generateBlobSASQueryParameters(
    {
      containerName,
      blobName,
      permissions: BlobSASPermissions.parse('r'),
      startsOn,
      expiresOn,
    },
    credential,
  ).toString();

  const accountUrl = limparBaseUrl(
    extrairValorConnectionString(connectionString, 'BlobEndpoint') ||
      `https://${accountName}.blob.core.windows.net`,
  );

  return `${accountUrl}/${containerName}/${encodeURI(blobName)}?${sas}`;
}

function getBasePublica(req) {
  const envUrl = limparBaseUrl(process.env.API_IMAGENS_PUBLIC_BASE_URL);
  if (envUrl) return envUrl;

  const vercelUrl = limparBaseUrl(process.env.VERCEL_URL);
  if (vercelUrl) return vercelUrl.startsWith('http') ? vercelUrl : `https://${vercelUrl}`;

  const host = req.headers['x-forwarded-host'] || req.headers.host;
  const proto = req.headers['x-forwarded-proto'] || 'https';

  if (!host) return 'https://check-empi-web.vercel.app';

  return `${proto}://${host}`;
}

function criarUrlVisualizacaoApi(req, blobName) {
  const base = getBasePublica(req);
  return `${base}/api/api_imagens?blob=${encodeURIComponent(blobName)}`;
}

function obterArquivo(files) {
  const camposPossiveis = ['file', 'arquivo', 'imagem', 'foto', 'media', 'midia'];

  for (const campo of camposPossiveis) {
    const valor = files?.[campo];
    if (!valor) continue;
    return Array.isArray(valor) ? valor[0] : valor;
  }

  return null;
}

async function uploadImagem(req, res) {
  const { containerName } = getAzureConfig();

  const form = formidable({
    multiples: false,
    keepExtensions: true,
    maxFileSize: Math.max(1, LIMITE_UPLOAD_MB) * 1024 * 1024,
  });

  const [fields, files] = await form.parse(req);
  const arquivo = obterArquivo(files);

  if (!arquivo) {
    return responder(res, 400, {
      sucesso: false,
      erro: 'Nenhum arquivo enviado. Use o campo multipart file, arquivo, imagem, foto ou media.',
    });
  }

  const empilhadeira = getCampo(fields, 'empilhadeira', 'sem_empilhadeira');
  const idCheck = getCampoAlternativo(fields, ['id_check', 'idCheck', 'check_id'], 'sem_check');
  const idFilial = getCampoAlternativo(fields, ['id_filial', 'idFilial'], '');
  const categoria = getCampo(fields, 'categoria', 'geral');
  const item = getCampo(fields, 'item', 'item');
  const pastaUpload = obterPastaUpload(
    getCampoAlternativo(fields, ['pasta', 'folder', 'tipo_pasta', 'tipoMidia', 'tipo_midia'], PASTA_PADRAO),
  );

  const buffer = fs.readFileSync(arquivo.filepath);

  if (!buffer.length) {
    return responder(res, 400, {
      sucesso: false,
      erro: 'Arquivo recebido está vazio.',
    });
  }

  const agora = new Date();
  const ano = agora.getFullYear();
  const mes = String(agora.getMonth() + 1).padStart(2, '0');

  const categoriaLimpa = normalizarTexto(categoria) || 'geral';
  const itemLimpo = normalizarTexto(item) || 'item';
  const empilhadeiraLimpa = normalizarTexto(empilhadeira) || 'sem_empilhadeira';
  const idCheckLimpo = normalizarTexto(idCheck) || 'sem_check';

  const extensao = obterExtensao(arquivo.mimetype, arquivo.originalFilename);
  const contentType =
    arquivo.mimetype && arquivo.mimetype !== 'application/octet-stream'
      ? arquivo.mimetype
      : contentTypePorExtensao(extensao);

  const nomeArquivo =
    `${pastaUpload}/${ano}/${mes}/emp_${empilhadeiraLimpa}/` +
    `check_${idCheckLimpo}_${categoriaLimpa}_${itemLimpo}_${Date.now()}.${extensao}`;

  const blobServiceClient = criarBlobServiceClient();
  const containerClient = blobServiceClient.getContainerClient(containerName);

  if (String(process.env.AZURE_CREATE_CONTAINER_IF_MISSING || 'true').toLowerCase() !== 'false') {
    await containerClient.createIfNotExists();
  }

  const blockBlobClient = containerClient.getBlockBlobClient(nomeArquivo);

  await blockBlobClient.uploadData(buffer, {
    blobHTTPHeaders: {
      blobContentType: contentType,
    },
    metadata: {
      origem: 'check_empi',
      pasta: pastaUpload,
      id_check: idCheckLimpo,
      id_filial: normalizarTexto(idFilial),
      empilhadeira: empilhadeiraLimpa,
      categoria: categoriaLimpa,
      item: itemLimpo,
    },
  });

  try {
    fs.unlinkSync(arquivo.filepath);
  } catch (_) {
    // Não bloqueia o retorno se o temporário não puder ser removido.
  }

  const minutosSas = Number(process.env.AZURE_BLOB_SAS_MINUTES || 240);
  const urlTemporaria = criarSasLeitura({
    blobName: nomeArquivo,
    minutos: minutosSas,
  });

  const urlAzureDireta = blockBlobClient.url;
  const urlVisualizacaoApi = criarUrlVisualizacaoApi(req, nomeArquivo);

  return responder(res, 200, {
    sucesso: true,
    mensagem: 'Mídia salva no Azure Blob Storage.',
    url: urlVisualizacaoApi,
    url_publica: urlVisualizacaoApi,
    url_visualizacao: urlVisualizacaoApi,
    pathname: nomeArquivo,
    caminho_arquivo: nomeArquivo,
    tamanho_bytes: arquivo.size || buffer.length,
    content_type: contentType,
    storage_origem: 'AZURE',
    pasta_azure: pastaUpload,
    container_azure: containerName,
    blob_azure: nomeArquivo,
    url_azure: urlAzureDireta,
    url_temporaria: urlTemporaria,
    url_sas: urlTemporaria,
    expira_em_minutos: urlTemporaria ? minutosSas : null,
    migrado_azure: 1,
  });
}

async function gerarUrlTemporaria(req, res) {
  const blob =
    req.query?.blob ||
    req.query?.pathname ||
    req.query?.caminho_arquivo ||
    req.query?.blob_azure;

  if (!blob) {
    return responder(res, 200, {
      sucesso: true,
      mensagem: 'API de imagens ativa. Use POST para enviar mídia ou GET com ?blob=... para visualizar.',
      rotas: {
        upload: 'POST /api/api_imagens',
        visualizar: 'GET /api/api_imagens?blob=CAMINHO_DO_BLOB',
        json: 'GET /api/api_imagens?blob=CAMINHO_DO_BLOB&json=1',
      },
      pastas_permitidas: ['avarias', 'pos_conferencia', 'pos_uso'],
    });
  }

  const blobName = String(blob);
  const minutos = Number(req.query?.minutos || process.env.AZURE_BLOB_SAS_MINUTES || 240);

  const urlTemporaria = criarSasLeitura({
    blobName,
    minutos,
  });

  if (!urlTemporaria) {
    return responder(res, 500, {
      sucesso: false,
      erro: 'Não foi possível gerar URL temporária. Verifique se a connection string possui AccountName e AccountKey.',
    });
  }

  const retornarJson =
    req.query?.json === '1' ||
    req.query?.json === 'true' ||
    req.query?.formato === 'json';

  const urlVisualizacaoApi = criarUrlVisualizacaoApi(req, blobName);

  if (retornarJson) {
    return responder(res, 200, {
      sucesso: true,
      blob_azure: blobName,
      url: urlVisualizacaoApi,
      url_publica: urlVisualizacaoApi,
      url_visualizacao: urlVisualizacaoApi,
      url_temporaria: urlTemporaria,
      url_sas: urlTemporaria,
      expira_em_minutos: minutos,
    });
  }

  const respostaAzure = await fetch(urlTemporaria);

  if (!respostaAzure.ok) {
    return responder(res, respostaAzure.status, {
      sucesso: false,
      erro: 'Não foi possível carregar a mídia no Azure Blob.',
      detalhe: await respostaAzure.text(),
    });
  }

  const contentType = respostaAzure.headers.get('content-type') || 'application/octet-stream';
  const arrayBuffer = await respostaAzure.arrayBuffer();

  setCorsHeaders(res);
  res.setHeader('Content-Type', contentType);
  res.setHeader('Cache-Control', 'private, max-age=300');
  res.setHeader('Content-Disposition', 'inline');
  return res.status(200).send(Buffer.from(arrayBuffer));
}

export default async function handler(req, res) {
  setCorsHeaders(res);

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  try {
    if (req.method === 'POST') {
      return await uploadImagem(req, res);
    }

    if (req.method === 'GET') {
      return await gerarUrlTemporaria(req, res);
    }

    return responder(res, 405, {
      sucesso: false,
      erro: 'Método não permitido. Use POST para enviar mídia ou GET para visualizar mídia salva.',
    });
  } catch (error) {
    console.error('ERRO_API_IMAGENS_AZURE:', error);

    return responder(res, 500, {
      sucesso: false,
      erro: 'Erro ao processar mídia no Azure Blob Storage.',
      detalhe: error?.message || String(error),
      name: error?.name || null,
    });
  }
}
