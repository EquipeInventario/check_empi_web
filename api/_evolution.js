function limparBaseUrl(url) {
  return String(url || '').trim().replace(/\/+$/, '');
}

function getConfigEvolution() {
  const apiUrl = limparBaseUrl(process.env.EVOLUTION_API_URL);
  const apiKey = process.env.EVOLUTION_API_KEY;
  const instance = process.env.EVOLUTION_INSTANCE;

  if (!apiUrl || !apiKey || !instance) {
    throw new Error(
      'Configuração da Evolution API incompleta. Verifique EVOLUTION_API_URL, EVOLUTION_API_KEY e EVOLUTION_INSTANCE.',
    );
  }

  return { apiUrl, apiKey, instance };
}

function headersEvolution() {
  const { apiKey } = getConfigEvolution();

  return {
    'Content-Type': 'application/json',
    apikey: apiKey,
  };
}

export async function verificarConexaoEvolution() {
  const { apiUrl, instance } = getConfigEvolution();

  const url = `${apiUrl}/instance/connectionState/${instance}`;

  const response = await fetch(url, {
    method: 'GET',
    headers: headersEvolution(),
  });

  const body = await response.json().catch(() => ({}));

  if (!response.ok) {
    return {
      ok: false,
      conectado: false,
      state: null,
      statusCode: response.status,
      erro: body,
    };
  }

  const state = body?.instance?.state || null;

  return {
    ok: true,
    conectado: state === 'open',
    state,
    retorno: body,
  };
}

export async function enviarTextoEvolution({ telefone, mensagem }) {
  const { apiUrl, instance } = getConfigEvolution();

  const numeroLimpo = String(telefone || '').replace(/\D/g, '').trim();
  const texto = String(mensagem || '').trim();

  if (!numeroLimpo) {
    throw new Error('Telefone de destino não informado.');
  }

  if (!texto) {
    throw new Error('Mensagem não informada.');
  }

  const url = `${apiUrl}/message/sendText/${instance}`;

  const response = await fetch(url, {
    method: 'POST',
    headers: headersEvolution(),
    body: JSON.stringify({
      number: numeroLimpo,
      text: texto,
    }),
  });

  const body = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(
      `Erro ao enviar WhatsApp pela Evolution API: ${JSON.stringify(body)}`,
    );
  }

  return body;
}
