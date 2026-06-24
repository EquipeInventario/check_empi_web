import {
  BlobServiceClient,
  BlobSASPermissions,
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
    'Content-Type, Authorization, x-checkempi-token, X-API-Token'
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

function obterExtensao(mimetype) {
  if (mimetype === 'image/png') return 'png';
  if (mimetype === 'image/webp') return 'webp';
  return 'jpg';
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

/**
 * Token opcional apenas para esta API de imagens.
 * Se API_IMAGENS_TOKEN não existir no Vercel, a rota fica liberada,
 * mantendo compatibilidade com o app atual.
 */
function validarTokenImagem(req) {
  const tokenEsperado = String(process.env.API_IMAGENS_TOKEN || '').trim();

  if (!tokenEsperado) {
    return true;
  }

  const authorization = String(req.headers.authorization || '').trim();
  const tokenBearer = authorization.startsWith('Bearer ')
    ? authorization.replace('Bearer ', '').trim()
    : '';

  const tokenRecebido =
    tokenBearer ||
    String(req.headers['x-api-token'] || '').trim() ||
    String(req.headers['x-checkempi-token'] || '').trim();

  return tokenRecebido === tokenEsperado;
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
  if (!validarTokenImagem(req)) {
    return responder(res, 401, {
      sucesso: false,
      erro: 'Token inválido ou ausente.',
    });
  }

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

  const buffer = fs.readFileSync(arquivo.filepath);

  const agora = new Date();
  const ano = agora.getFullYear();
  const mes = String(agora.getMonth() + 1).padStart(2, '0');

  const categoriaLimpa = normalizarTexto(categoria);
  const itemLimpo = normalizarTexto(item);
  const empilhadeiraLimpa = normalizarTexto(empilhadeira);

  const contentType = arquivo.mimetype || 'image/jpeg';
  const extensao = obterExtensao(contentType);

  const nomeArquivo =
    `avarias/${ano}/${mes}/emp_${empilhadeiraLimpa}/` +
    `check_${idCheck}_${categoriaLimpa}_${itemLimpo}_${Date.now()}.${extensao}`;

  const blobServiceClient = criarBlobServiceClient();
  const containerClient = blobServiceClient.getContainerClient(containerName);

  /**
   * O container já foi criado no Azure.
   * Mesmo assim, createIfNotExists evita erro se subir em outro ambiente novo.
   */
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
    // Não bloqueia o upload caso o temporário não seja apagado.
  }

  /**
   * Como o container está privado, a URL direta do blob não abre sozinha.
   * Por isso retornamos também uma URL temporária de leitura.
   */
  const urlTemporaria = criarSasLeitura({
    blobName: nomeArquivo,
    minutos: Number(process.env.AZURE_BLOB_SAS_MINUTES || 240),
  });

  const urlDiretaAzure = blockBlobClient.url;
  const urlVisualizacao = urlTemporaria || urlDiretaAzure;

  return responder(res, 200, {
    sucesso: true,

    /**
     * Campos mantidos para compatibilidade com o app atual.
     */
    url: urlVisualizacao,
    url_publica: urlVisualizacao,
    pathname: nomeArquivo,
    caminho_arquivo: nomeArquivo,
    tamanho_bytes: arquivo.size || buffer.length,
    content_type: contentType,

    /**
     * Campos novos para controle/migração Azure.
     */
    storage_origem: 'AZURE',
    container_azure: containerName,
    blob_azure: nomeArquivo,
    url_azure: urlDiretaAzure,
    url_temporaria: urlTemporaria,
    migrado_azure: 1,
  });
}

async function gerarUrlTemporaria(req, res) {
  if (!validarTokenImagem(req)) {
    return responder(res, 401, {
      sucesso: false,
      erro: 'Token inválido ou ausente.',
    });
  }

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

  const minutos = Number(req.query?.minutos || process.env.AZURE_BLOB_SAS_MINUTES || 240);

  const urlTemporaria = criarSasLeitura({
    blobName: String(blob),
    minutos,
  });

  if (!urlTemporaria) {
    return responder(res, 500, {
      sucesso: false,
      erro: 'Não foi possível gerar URL temporária. Verifique a connection string.',
    });
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
      erro: 'Método não permitido. Use POST para enviar imagem ou GET para gerar URL temporária.',
    });
  } catch (error) {
    console.error('ERRO_API_IMAGENS_AZURE:', error);

    return responder(res, 500, {
      sucesso: false,
      erro: 'Erro ao processar imagem no Azure Blob Storage.',
      detalhe: error?.message || String(error),
      name: error?.name || null,
    });
  }
}
