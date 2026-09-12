// Mesma convenção do frontend/: mesma origem quando servido pela API, e
// VITE_API_BASE_URL quando rodando no Vite em outra porta.
const API_BASE = import.meta.env.VITE_API_BASE_URL || window.location.origin;

const CHAVE_SESSAO = 'painel-editorial:sessao';

export function lerSessao() {
  try {
    const bruto = localStorage.getItem(CHAVE_SESSAO);
    return bruto ? JSON.parse(bruto) : null;
  } catch {
    // Navegador com armazenamento bloqueado: a pessoa faz login de novo.
    return null;
  }
}

export function guardarSessao(sessao) {
  try {
    localStorage.setItem(CHAVE_SESSAO, JSON.stringify(sessao));
  } catch {
    /* segue sem lembrar da sessão */
  }
}

export function esquecerSessao() {
  try {
    localStorage.removeItem(CHAVE_SESSAO);
  } catch {
    /* nada a fazer */
  }
}

export class ErroDaApi extends Error {
  constructor(mensagem, status, detalhe) {
    super(mensagem);
    this.status = status;
    this.detalhe = detalhe;
  }
}

async function pedir(caminho, { metodo = 'GET', corpo, token } = {}) {
  const resposta = await fetch(`${API_BASE}${caminho}`, {
    method: metodo,
    headers: {
      ...(corpo ? { 'Content-Type': 'application/json' } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: corpo ? JSON.stringify(corpo) : undefined,
  });

  let dados = null;
  try {
    dados = await resposta.json();
  } catch {
    dados = null;
  }

  if (!resposta.ok) {
    const detalhe = dados?.detail ?? dados;
    const mensagem =
      typeof detalhe === 'string'
        ? detalhe
        : detalhe?.mensagem || `Falha na requisição (${resposta.status})`;
    throw new ErroDaApi(mensagem, resposta.status, detalhe);
  }
  return dados;
}

export const api = {
  login: (nome, senha) => pedir('/admin/login', { metodo: 'POST', corpo: { nome, senha } }),
  sessao: (token) => pedir('/admin/sessao', { token }),
  manifesto: () => pedir('/manifesto?usar_banco=true'),
  cidades: () => pedir('/cities'),
  conexao: (token) => pedir('/admin/conexao', { token }),
  contratos: (token) => pedir('/admin/contratos', { token }),
  contrato: (slug, token) => pedir(`/admin/contratos/${slug}`, { token }),
  historico: (slug, token) => pedir(`/admin/contratos/${slug}/historico`, { token }),
  versao: (slug, versao, token) =>
    pedir(`/admin/contratos/${slug}/versoes/${versao}`, { token }),
  publicar: (slug, contrato, versaoEsperada, token) =>
    pedir(`/admin/contratos/${slug}`, {
      metodo: 'PUT',
      corpo: { contrato, versao_esperada: versaoEsperada },
      token,
    }),
  importar: (slug, baixar, token) =>
    pedir(`/admin/contratos/${slug}/importar?baixar=${baixar ? 'true' : 'false'}`, {
      metodo: 'POST',
      token,
    }),
  previa: (slug, contrato, cidade, token) =>
    pedir(`/admin/contratos/${slug}/previa`, {
      metodo: 'POST',
      corpo: { contrato, cidade },
      token,
    }),
};
