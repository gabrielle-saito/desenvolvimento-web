// Estrutura comum das páginas: confere login, monta o menu conforme o papel.

import { api, mensagemDeErro } from "./api.js";
import { el } from "./dom.js";
import { limparSessao, obterToken, salvarSessao, temPapel } from "./sessao.js";

const NOME_PAPEL = { colaborador: "Colaborador", responsavel: "Responsável", admin: "Admin" };

const MENU = [
  { href: "agenda.html", texto: "Agenda", papel: "colaborador" },
  { href: "reservar.html", texto: "Consultar e reservar", papel: "colaborador" },
  { href: "minhas.html", texto: "Minhas reservas", papel: "colaborador" },
  { href: "responsavel.html", texto: "Gerenciar reservas", papel: "responsavel" },
  { href: "admin.html", texto: "Administração", papel: "admin" },
];

function montarMenu(usuario) {
  const atual = window.location.pathname.split("/").pop();
  const itens = MENU.filter((i) => temPapel(usuario, i.papel)).map((i) =>
    el(
      "li",
      {},
      el("a", { href: i.href, "aria-current": i.href === atual ? "page" : undefined }, i.texto),
    ),
  );
  const sair = el(
    "button",
    {
      type: "button",
      class: "botao-link",
      onclick: () => {
        limparSessao();
        window.location.href = "login.html";
      },
    },
    "Sair",
  );
  document.getElementById("menu").replaceChildren(
    el("ul", {}, itens),
    el(
      "p",
      { class: "usuario-logado" },
      el("span", {}, `${usuario.nome} `),
      el("span", { class: "etiqueta" }, NOME_PAPEL[usuario.papel] || usuario.papel),
      " ",
      sair,
    ),
  );
}

// Chame no início de cada página protegida. Devolve o usuário logado, ou
// null se ele não tiver o papel mínimo (a página mostra "acesso negado").
export async function iniciarPagina(papelMinimo = "colaborador") {
  if (!obterToken()) {
    window.location.href = "login.html";
    return null;
  }
  let usuario;
  try {
    // Sempre busca de novo: se o admin mudou o papel, o menu acompanha.
    usuario = await api.get("/v1/auth/me");
    salvarSessao(obterToken(), usuario);
  } catch (erro) {
    document.getElementById("conteudo").replaceChildren(el("p", { class: "aviso aviso-erro" }, mensagemDeErro(erro)));
    return null;
  }
  montarMenu(usuario);
  if (!temPapel(usuario, papelMinimo)) {
    document.getElementById("conteudo").replaceChildren(
      el("h1", {}, "Acesso negado"),
      el("p", { class: "aviso aviso-erro" }, "Você não tem permissão para acessar esta área."),
    );
    return null;
  }
  return usuario;
}
