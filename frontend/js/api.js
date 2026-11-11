// Cliente HTTP da API: fetch + token Bearer + tratamento de erros.
//
// Toda resposta de erro da API vem em Problem Details (RFC 9457):
//   { type, title, status, detail, instance, erros?, versao_atual? ... }
// Aqui ela vira um ErroApi, que as telas tratam por status:
//   401 -> volta ao login | 403 -> "acesso negado" | 409 -> mostra o detail
//   422 -> erro em cada campo do formulário

import { API_URL } from "../config.js";
import { limparSessao, obterToken } from "./sessao.js";

export class ErroApi extends Error {
  constructor(status, problema) {
    super(problema?.detail || `Erro ${status}`);
    this.status = status;
    this.problema = problema || {};
  }
}

async function lerCorpo(resposta) {
  const tipo = resposta.headers.get("content-type") || "";
  if (tipo.includes("json")) return resposta.json();
  return null;
}

export async function requisicao(metodo, caminho, { corpo, formulario, params } = {}) {
  const url = new URL(caminho, API_URL);
  if (params) {
    for (const [chave, valor] of Object.entries(params)) {
      if (valor !== undefined && valor !== null && valor !== "") url.searchParams.set(chave, valor);
    }
  }

  const headers = {};
  const token = obterToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  let body;
  if (formulario) {
    body = new URLSearchParams(formulario); // login OAuth2: form-urlencoded
  } else if (corpo !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(corpo);
  }

  let resposta;
  try {
    resposta = await fetch(url, { method: metodo, headers, body });
  } catch {
    throw new ErroApi(0, { detail: "Não foi possível falar com o servidor. Verifique sua conexão." });
  }

  const dados = await lerCorpo(resposta);
  if (resposta.ok) return dados;

  // 401 fora da tela de login = token ausente/expirado: volta para o login.
  if (resposta.status === 401 && !caminho.endsWith("/auth/login")) {
    limparSessao();
    window.location.href = "login.html?expirou=1";
  }
  throw new ErroApi(resposta.status, dados);
}

export const api = {
  get: (caminho, params) => requisicao("GET", caminho, { params }),
  post: (caminho, corpo) => requisicao("POST", caminho, { corpo }),
  patch: (caminho, corpo) => requisicao("PATCH", caminho, { corpo }),
  login: (email, senha) =>
    requisicao("POST", "/v1/auth/login", { formulario: { username: email, password: senha } }),
};

// Mensagem amigável para qualquer erro, usada quando a tela não precisa de
// um tratamento específico.
export function mensagemDeErro(erro) {
  if (!(erro instanceof ErroApi)) return "Erro inesperado. Tente novamente.";
  if (erro.status === 403) return "Acesso negado: você não tem permissão para esta ação.";
  if (erro.status === 404) return erro.problema.detail || "Não encontrado.";
  if (erro.status >= 500) {
    const id = erro.problema.request_id;
    return `Erro no servidor. Tente novamente${id ? ` (código para o suporte: ${id})` : ""}.`;
  }
  return erro.problema.detail || erro.message;
}
