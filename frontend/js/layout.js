// Estrutura comum das páginas: confere login, monta o menu conforme o papel.

import { api, mensagemDeErro } from "./api.js";
import { el } from "./dom.js";
import { limparSessao, obterToken, salvarSessao, temPapel } from "./sessao.js";

const NOME_PAPEL = { colaborador: "Colaborador(a)", responsavel: "Responsável", admin: "Administrador(a)" };

// "Salas" e "Usuários" são as duas seções da página de administração.
const MENU = [
  { href: "agenda.html", texto: "Agenda", papel: "colaborador" },
  { href: "reservar.html", texto: "Reservar sala", papel: "colaborador" },
  { href: "minhas.html", texto: "Minhas reservas", papel: "colaborador" },
  { href: "responsavel.html", texto: "Gerenciar reservas", papel: "responsavel" },
  { href: "admin.html#titulo-salas", texto: "Salas", papel: "admin" },
  { href: "admin.html#titulo-usuarios", texto: "Usuários", papel: "admin" },
];

// Qual item do menu é a página atual. Na administração, decide pelo #:
// sem # (ou com outro), conta como "Salas", a primeira seção.
function itemAtual(itens) {
  const pagina = window.location.pathname.split("/").pop() || "index.html";
  const daPagina = itens.filter((i) => i.href.split("#")[0] === pagina);
  return daPagina.find((i) => i.href.endsWith(window.location.hash || "#")) || daPagina[0];
}

function marcarAtual(lista, itens) {
  const atual = itemAtual(itens);
  for (const link of lista.querySelectorAll("a")) {
    if (link.getAttribute("href") === atual?.href) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  }
}

function montarMenu(usuario) {
  const itens = MENU.filter((i) => temPapel(usuario, i.papel));
  const lista = el(
    "ul",
    {},
    itens.map((i) => el("li", {}, el("a", { href: i.href }, i.texto))),
  );
  marcarAtual(lista, itens);
  window.addEventListener("hashchange", () => marcarAtual(lista, itens));
  document.getElementById("menu").replaceChildren(lista);

  // Avatar, nome, papel e "Sair" ficam fora do <nav>, à direita da barra.
  document.querySelector(".topo .usuario-logado")?.remove();
  const sair = el(
    "button",
    {
      type: "button",
      class: "botao-fantasma",
      onclick: () => {
        limparSessao();
        window.location.href = "login.html";
      },
    },
    "Sair",
  );
  document.getElementById("menu").after(
    el(
      "div",
      { class: "usuario-logado" },
      el("span", { class: "avatar", "aria-hidden": "true" }, iniciais(usuario.nome)),
      el(
        "span",
        { class: "usuario-texto" },
        el("strong", {}, usuario.nome),
        el("span", { class: "usuario-papel" }, NOME_PAPEL[usuario.papel] || usuario.papel),
      ),
      sair,
    ),
  );
}

// "Mariana Souza" -> "MS"; "Ana" -> "A".
function iniciais(nome) {
  const partes = String(nome).trim().split(/\s+/).filter(Boolean);
  const letras = partes.length > 1 ? [partes[0], partes[partes.length - 1]] : partes;
  return letras.map((p) => p[0].toUpperCase()).join("");
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
