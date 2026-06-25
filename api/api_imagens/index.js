import {
  BlobSASPermissions,
  BlobServiceClient,
  SASProtocol,
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

function setCorsHeaders(res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, GET, OPTIONS');
  res.setHeader(
    'Access-Control-Allow-Headers',
    'Content-Type'
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
  const valor = fields[nome];

  if (Array.isArray(valor)) {
    return valor[0]?.toString() || padrao;
  }

  return valor?.toString() || padrao;
}

function normalizarTexto(texto) {
  return String(texto || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/_+/g, '_')
    .replace(/^_|_$/g, '');
}

// api_imagens: define a extensao correta para fotos e videos enviados pelo app.
function obterExtensao(mimetype, nomeArquivo = '') {
  const tipo = String(mimetype || '').toLowerCase();
  const nome = String(nomeArquivo || '').toLowerCase();

  if (tipo.includes('image/png') || nome.endsWith('.png')) return 'png';
  if (tipo.includes('image/webp') || nome.endsWith('.webp')) return 'webp';
  if (tipo.includes('video/webm') || nome.endsWith('.webm')) return 'webm';
  if (tipo.includes('video/quicktime') || nome.endsWith('.mov')) return 'mov';
  if (tipo.includes('video/mp4') || nome.endsWith('.mp4')) return 'mp4';

  return 'jpg';
}

// api_imagens: fallback de content-type quando o multipart chegar como octet-stream.
function contentTypePorExtensao(extensao) {
  if (extensao === 'png') return 'image/png';
  if (extensao === 'webp') return 'image/webp';
  if (extensao === 'webm') return 'video/webm';
  if (extensao === 'mov') return 'video/quicktime';
  if (extensao === 'mp4') return 'video/mp4';
  return 'image/jpeg';
}

// api_imagens: pastas virtuais permitidas dentro do container check-empi-avarias.
function obterPastaUpload(pasta) {
  const pastaLimpa = normalizarTexto(pasta || 'avarias') || 'avarias';
  const permitidas = new Set(['avarias', 'pos_conferencia', 'pos_uso']);
  return permitidas.has(pastaLimpa) ? pastaLimpa : 'avarias';
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
  const containerName =
    process.env.AZURE_BLOB_CONTAINER || 'check-empi-avarias';

  if (!connectionString) {
    throw new Error('Variavel AZURE_STORAGE_CONNECTION_STRING nao configurada.');
  }

  if (!containerName) {
    throw new Error('Variavel AZURE_BLOB_CONTAINER nao configurada.');
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

  const accountName = extrairValorConnectionString(
    connectionString,
    'AccountName'
  );
  const accountKey = extrairValorConnectionString(
    connectionString,
    'AccountKey'
  );

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
      protocol: SASProtocol.Https,
    },
    credential
  ).toString();

  const accountUrl = limparBaseUrl(
    extrairValorConnectionString(connectionString, 'BlobEndpoint') ||
      `https://${accountName}.blob.core.windows.net`
  );

  return `${accountUrl}/${containerName}/${encodeURI(blobName)}?${sas}`;
}

async function uploadImagem(req, res) {
  const { containerName } = getAzureConfig();

  const form = formidable({
    multiples: false,
    keepExtensions: true,
    maxFileSize: 8 * 1024 * 1024,
  });

  const [fields, files] = await form.parse(req);

  const arquivo = Array.isArray(files.file) ? files.file[0] : files.file;

  if (!arquivo) {
    return responder(res, 400, {
      sucesso: false,
      erro: 'Nenhum arquivo enviado no campo file.',
    });
  }

  const empilhadeira = getCampo(fields, 'empilhadeira', 'sem_empilhadeira');
  const idCheck = getCampo(fields, 'id_check', 'sem_check');
  const categoria = getCampo(fields, 'categoria', 'geral');
  const item = getCampo(fields, 'item', 'item');
  const pastaUpload = obterPastaUpload(getCampo(fields, 'pasta', 'avarias'));

  const buffer = fs.readFileSync(arquivo.filepath);

  const agora = new Date();
  const ano = agora.getFullYear();
  const mes = String(agora.getMonth() + 1).padStart(2, '0');

  const categoriaLimpa = normalizarTexto(categoria);
  const itemLimpo = normalizarTexto(item);
  const empilhadeiraLimpa = normalizarTexto(empilhadeira);

  const extensao = obterExtensao(arquivo.mimetype, arquivo.originalFilename);
  const contentType =
    arquivo.mimetype && arquivo.mimetype !== 'application/octet-stream'
      ? arquivo.mimetype
      : contentTypePorExtensao(extensao);

  const nomeArquivo =
    `${pastaUpload}/${ano}/${mes}/emp_${empilhadeiraLimpa}/` +
    `check_${idCheck}_${categoriaLimpa}_${itemLimpo}_${Date.now()}.${extensao}`;

  const blobServiceClient = criarBlobServiceClient();
  const containerClient = blobServiceClient.getContainerClient(containerName);

  await containerClient.createIfNotExists();

  const blockBlobClient = containerClient.getBlockBlobClient(nomeArquivo);

  await blockBlobClient.uploadData(buffer, {
    blobHTTPHeaders: {
      blobContentType: contentType,
    },
  });

  try {
    fs.unlinkSync(arquivo.filepath);
  } catch (_) {
    // Nao bloqueia o upload caso o temporario nao seja apagado.
  }

  const urlTemporaria = criarSasLeitura({
    blobName: nomeArquivo,
    minutos: Number(process.env.AZURE_BLOB_SAS_MINUTES || 240),
  });

  const urlDiretaAzure = blockBlobClient.url;
  const urlVisualizacao = urlTemporaria || urlDiretaAzure;

  return responder(res, 200, {
    sucesso: true,
    url: urlVisualizacao,
    url_publica: urlVisualizacao,
    pathname: nomeArquivo,
    caminho_arquivo: nomeArquivo,
    tamanho_bytes: arquivo.size || buffer.length,
    content_type: contentType,
    storage_origem: 'AZURE',
    pasta_azure: pastaUpload,
    container_azure: containerName,
    blob_azure: nomeArquivo,
    url_azure: urlDiretaAzure,
    url_temporaria: urlTemporaria,
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
    return responder(res, 400, {
      sucesso: false,
      erro: 'Informe o caminho do blob em ?blob=...',
    });
  }

  const minutos = Number(
    req.query?.minutos || process.env.AZURE_BLOB_SAS_MINUTES || 240
  );

  const urlTemporaria = criarSasLeitura({
    blobName: String(blob),
    minutos,
  });

  if (!urlTemporaria) {
    return responder(res, 500, {
      sucesso: false,
      erro: 'Nao foi possivel gerar URL temporaria. Verifique a connection string.',
    });
  }

  const retornarJson =
    req.query?.json === '1' ||
    req.query?.json === 'true' ||
    req.query?.formato === 'json';

  if (!retornarJson) {
    const respostaAzure = await fetch(urlTemporaria);

    if (!respostaAzure.ok) {
      return responder(res, respostaAzure.status, {
        sucesso: false,
        erro: 'Nao foi possivel carregar a m?dia no Azure Blob.',
        detalhe: await respostaAzure.text(),
      });
    }

    const contentType =
      respostaAzure.headers.get('content-type') || 'image/jpeg';
    const arrayBuffer = await respostaAzure.arrayBuffer();

    setCorsHeaders(res);
    res.setHeader('Content-Type', contentType);
    res.setHeader('Cache-Control', 'private, max-age=300');
    res.setHeader('Content-Disposition', 'inline');
    return res.status(200).send(Buffer.from(arrayBuffer));
  }

  return responder(res, 200, {
    sucesso: true,
    blob_azure: String(blob),
    url: urlTemporaria,
    url_publica: urlTemporaria,
    url_temporaria: urlTemporaria,
    expira_em_minutos: minutos,
  });
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
      erro: 'Metodo nao permitido. Use POST para enviar imagem ou GET para gerar URL temporaria.',
    });
  } catch (error) {
    console.error('ERRO_API_IMAGENS_AZURE:', error);

    return responder(res, 500, {
      sucesso: false,
      erro: 'Erro ao processar m?dia no Azure Blob Storage.',
      detalhe: error?.message || String(error),
      name: error?.name || null,
    });
  }
}
