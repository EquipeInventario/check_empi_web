import { BlobServiceClient } from '@azure/storage-blob';
import formidable from 'formidable';
import { readFile, unlink } from 'node:fs/promises';

export const config = { api: { bodyParser: false } };
const MAX = 4 * 1024 * 1024;
const BASE = 'https://manutencao-predial-nine.vercel.app';
const allowedOrigins = new Set(['https://manutencao-predial.inventario-pg.workers.dev','https://manutencao-predial.pages.dev']);
const validId = /^[1-9][0-9]{0,9}$/;
const validPhoto = /^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/;
class HttpError extends Error {
  constructor(status, message) { super(message); this.status = status; }
}
function cors(req, res) {
  const origin = req.headers.origin;
  if (allowedOrigins.has(origin) || /^http:\/\/(localhost|127\.0\.0\.1)(:[0-9]{1,5})?$/.test(origin || '')) {
    res.setHeader('Access-Control-Allow-Origin', origin);
  }
  res.setHeader('Vary', 'Origin');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Authorization, Content-Type');
  res.setHeader('Cache-Control', 'no-store, private');
  res.setHeader('X-Content-Type-Options', 'nosniff');
}
function json(res, status, body) { res.statusCode = status; res.setHeader('Content-Type','application/json; charset=utf-8'); res.end(JSON.stringify(body)); }
async function authorize(req, oid, fase, operacao) {
  const token = req.headers.authorization;
  if (typeof token !== 'string' || !token.startsWith('Bearer ')) throw new HttpError(401,'Sessão inválida.');
  const url = new URL('/api/ordens/'+oid+'/imagens/permissao', BASE);
  url.searchParams.set('fase', fase); url.searchParams.set('operacao', operacao);
  const response = await fetch(url, {headers:{Authorization:token,Accept:'application/json'},redirect:'error',signal:AbortSignal.timeout(12000)});
  if (!response.ok) throw new HttpError([401,403,404,422].includes(response.status)?response.status:503,'Acesso à imagem não autorizado ou indisponível.');
  const result = await response.json();
  if (result.permitido !== true || String(result.ordem_id) !== oid || result.fase !== fase) throw new HttpError(403,'Acesso à imagem não autorizado.');
}
function getContainer() {
  const connection = process.env.AZURE_STORAGE_CONNECTION_STRING;
  const name = process.env.AZURE_BLOB_CONTAINER;
  if (!connection || name !== 'os-manutencao') throw new HttpError(503,'Armazenamento de imagens não configurado.');
  return BlobServiceClient.fromConnectionString(connection).getContainerClient(name);
}
async function parsePhoto(req) {
  const temp = new Set();
  try {
    const form = formidable({multiples:false,maxFiles:1,maxFileSize:MAX,maxTotalFileSize:MAX,maxFields:0,allowEmptyFiles:false,minFileSize:1});
    form.on('fileBegin', (_,file)=>temp.add(file.filepath));
    const [,files] = await form.parse(req);
    const file = files.file?.[0];
    if (!file) throw new HttpError(400,'Envie uma imagem no campo file.');
    const data = await readFile(file.filepath);
    if (data.length > MAX) throw new HttpError(413,'Imagem acima de 4 MB.');
    // Browser normalizes images to JPEG. Reject other payloads regardless of extension.
    if (file.mimetype !== 'image/jpeg' || data.length < 4 || data[0]!==255 || data[1]!==216 || data[2]!==255 || data[data.length-2]!==255 || data[data.length-1]!==217)
      throw new HttpError(415,'Imagem JPEG inválida.');
    return data;
  } finally { await Promise.all([...temp].map(path=>unlink(path).catch(()=>{}))); }
}
export function makeHandler({check=authorize,storage=getContainer,parse=parsePhoto}={}) {
  return async function handler(req,res) {
    cors(req,res);
    if (req.method==='OPTIONS') {res.statusCode=204;return res.end();}
    if (!['GET','POST'].includes(req.method)) return json(res,405,{detail:'Método não permitido.'});
    try {
      const q = new URL(req.url,'http://localhost').searchParams;
      const oid=q.get('os') || '', fase=q.get('fase') || '', photo=q.get('foto');
      if (!validId.test(oid) || !['abertura','conclusao'].includes(fase) || (photo!==null && !validPhoto.test(photo)))
        throw new HttpError(422,'Identificação da imagem inválida.');
      if (req.method==='POST' && !photo) throw new HttpError(422,'Identificação da imagem obrigatória.');
      await check(req,oid,fase,req.method==='POST'?'envio':'leitura');
      const container=storage(), prefix='os/'+oid+'/'+fase+'/';
      if (req.method==='POST') {
        const data=await parse(req);
        const blob=container.getBlockBlobClient(prefix+photo+'.jpg');
        try {
          await blob.uploadData(data,{conditions:{ifNoneMatch:'*'},blobHTTPHeaders:{blobContentType:'image/jpeg',blobCacheControl:'private, no-store'}});
        } catch(e) {
          // An identical retry cannot overwrite an existing image.
          if (![409,412].includes(e.statusCode)) throw e;
          if (!(await blob.exists())) throw e;
        }
        return json(res,200,{sucesso:true,id:photo});
      }
      if (photo) {
        const blob=container.getBlockBlobClient(prefix+photo+'.jpg');
        const props=await blob.getProperties();
        if (props.contentType!=='image/jpeg' || !Number.isInteger(props.contentLength) || props.contentLength>MAX) throw new HttpError(415,'Imagem indisponível.');
        const data=await blob.downloadToBuffer();
        res.statusCode=200;res.setHeader('Content-Type','image/jpeg');res.setHeader('Content-Disposition','inline');return res.end(data);
      }
      const fotos=[];
      for await (const blob of container.listBlobsFlat({prefix})) {
        const name=blob.name.slice(prefix.length);
        const id=name.endsWith('.jpg')?name.slice(0,-4):'';
        if (!validPhoto.test(id)) continue;
        fotos.push({id,criado_em:blob.properties.lastModified?.toISOString() || ''});
      }
      fotos.sort((a,b)=>a.criado_em.localeCompare(b.criado_em)||a.id.localeCompare(b.id));
      return json(res,200,{fotos});
    } catch(e) {
      const code=e instanceof HttpError?e.status:e.httpCode===413?413:e.statusCode===404?404:503;
      if (code===503) console.error('Falha imagens:',e?.name || 'Error',e?.code || '');
      return json(res,code,{detail:e instanceof HttpError?e.message:code===413?'Imagem acima de 4 MB.':code===404?'Imagem não encontrada.':'Não foi possível processar a imagem.'});
    }
  };
}
export default makeHandler();
