// Cliente HTTP da API: fetch + token Bearer + tratamento de erros.
//
// Toda resposta de erro da API vem em Problem Details (RFC 9457):
//   { type, title, status, detail, instance, erros?, versao_atual? ... }
// Aqui ela vira um ErroApi, que as telas tratam por status:
//   401 -> volta ao login | 403 -> "acesso negado" | 409 -> mostra o detail
//   422 -> erro embaixo de cada campo do formulário (ver errosPorCampo)

import { API_URL } from "../config.js";
import { obterToken } from "./sessao.js";

export class ErroApi extends Error {
  constructor(status, problema) {
    super(problema?.detail || `Erro ${status}`);
    this.status = status;
    this.problema = problema || {};
  }
}

// Quem quer saber de um 401 (sessão expirada) se registra aqui. É o
// AuthContext: ele limpa a sessão e leva para o login.
let aoExpirarSessao = () => {};
export function quandoSessaoExpirar(funcao) {
  aoExpirarSessao = funcao;
}

async function requisicao(metodo, caminho, { corpo, formulario, params, comTotal } = {}) {
  const url = new URL(caminho, API_URL);
  for (const [chave, valor] of Object.entries(params ?? {})) {
    if (valor === undefined || valor === null || valor === "") continue;
    // Lista vira parâmetro repetido: ?recurso=1&recurso=3
    for (const v of [valor].flat()) url.searchParams.append(chave, v);
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

  const tipo = resposta.headers.get("content-type") || "";
  const dados = tipo.includes("json") ? await resposta.json() : null;
  if (resposta.ok) {
    // Listagens paginadas: o total vem no cabeçalho X-Total-Count.
    if (comTotal) return { itens: dados, total: Number(resposta.headers.get("X-Total-Count") ?? dados.length) };
    return dados;
  }

  // 401 com token = token expirado ou usuário desativado: volta ao login.
  if (resposta.status === 401 && token && !caminho.endsWith("/auth/login")) aoExpirarSessao();
  throw new ErroApi(resposta.status, dados);
}

export const api = {
  get: (caminho, params) => requisicao("GET", caminho, { params }),
  // Uma página de uma listagem: devolve { itens, total }.
  pagina: (caminho, params) => requisicao("GET", caminho, { params, comTotal: true }),
  post: (caminho, corpo) => requisicao("POST", caminho, { corpo }),
  patch: (caminho, corpo) => requisicao("PATCH", caminho, { corpo }),
  login: (email, senha) =>
    requisicao("POST", "/v1/auth/login", { formulario: { username: email, password: senha } }),
};

// Mensagem amigável para qualquer erro.
export function mensagemDeErro(erro) {
  if (!(erro instanceof ErroApi)) return "Erro inesperado. Tente novamente.";
  if (erro.status === 403) return "Acesso negado: você não tem permissão para esta ação.";
  if (erro.status === 404) return erro.problema.detail || "Não encontrado.";
  if (erro.status === 422 && erro.problema.erros?.length) return "Corrija os campos destacados.";
  if (erro.status >= 500) {
    const id = erro.problema.request_id;
    return `Erro no servidor. Tente novamente${id ? ` (código para o suporte: ${id})` : ""}.`;
  }
  return erro.problema.detail || erro.message;
}

// 422: { campo: mensagem } para mostrar embaixo de cada campo.
export function errosPorCampo(erro) {
  if (!(erro instanceof ErroApi) || erro.status !== 422) return {};
  return Object.fromEntries((erro.problema.erros ?? []).map((e) => [e.campo, e.mensagem]));
}
