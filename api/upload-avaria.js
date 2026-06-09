import { put } from '@vercel/blob';
import formidable from 'formidable';
import fs from 'fs';

export const config = {
  api: {
    bodyParser: false
  }
};

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({
      sucesso: false,
      erro: 'Método não permitido'
    });
  }

  try {
    const form = formidable({
      multiples: false,
      keepExtensions: true
    });

    const [fields, files] = await form.parse(req);

    const arquivo = Array.isArray(files.file) ? files.file[0] : files.file;

    if (!arquivo) {
      return res.status(400).json({
        sucesso: false,
        erro: 'Nenhum arquivo enviado'
      });
    }

    const empilhadeira = Array.isArray(fields.empilhadeira)
      ? fields.empilhadeira[0]
      : fields.empilhadeira || 'sem-empilhadeira';

    const idCheck = Array.isArray(fields.id_check)
      ? fields.id_check[0]
      : fields.id_check || 'sem-check';

    const buffer = fs.readFileSync(arquivo.filepath);

    const agora = new Date();
    const ano = agora.getFullYear();
    const mes = String(agora.getMonth() + 1).padStart(2, '0');

    const nomeArquivo = `avarias/${ano}/${mes}/emp_${empilhadeira}/check_${idCheck}_${Date.now()}.jpg`;

    const blob = await put(nomeArquivo, buffer, {
      access: 'public',
      contentType: arquivo.mimetype || 'image/jpeg',
      addRandomSuffix: false
    });

    return res.status(200).json({
      sucesso: true,
      url: blob.url,
      pathname: blob.pathname,
      tamanho_bytes: arquivo.size
    });
  } catch (error) {
    return res.status(500).json({
      sucesso: false,
      erro: 'Erro ao enviar imagem para o Vercel Blob',
      detalhe: error.message
    });
  }
}