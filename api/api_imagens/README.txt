# API de Imagens - Azure Blob Storage

Estrutura esperada no projeto:

api/
  api_imagens/
    index.js

Rota no Vercel:

/api/api_imagens

Variáveis necessárias no Vercel:

AZURE_STORAGE_CONNECTION_STRING
AZURE_BLOB_CONTAINER=check-empi-avarias

Variáveis opcionais:

API_IMAGENS_TOKEN
AZURE_BLOB_SAS_MINUTES=240

POST /api/api_imagens
Campo multipart: file
Campos adicionais:
- empilhadeira
- id_check
- categoria
- item

GET /api/api_imagens?blob=CAMINHO_DO_BLOB
Gera uma URL temporária para visualização quando o container é privado.
