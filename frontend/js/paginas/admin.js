// Área do admin: salas (caso de uso 6) e usuários (caso de uso 7).

import { api } from "../api.js";
import { avisar, el, limparErrosDeCampo } from "../dom.js";
import { iniciarPagina } from "../layout.js";
import { tratarErro } from "../reservas-ui.js";

const avisos = document.getElementById("avisos");
const formSala = document.getElementById("form-sala");
const formUsuario = document.getElementById("form-usuario");
const listaSalas = document.getElementById("lista-salas");
const listaUsuarios = document.getElementById("lista-usuarios");
let usuarioLogado;

const PAPEIS = [
  ["colaborador", "Colaborador"],
  ["responsavel", "Responsável"],
  ["admin", "Admin"],
];

// Campos de texto opcionais vazios viram null (e não "").
function textoOuNulo(valor) {
  const t = String(valor ?? "").trim();
  return t ? t : null;
}

async function executar(acao, sucesso, form) {
  try {
    await acao();
    avisar(avisos, sucesso, "sucesso");
    return true;
  } catch (erro) {
    tratarErro(erro, avisos, form);
    return false;
  }
}

// ------------------------------------------------------------------- salas
function linhaSala(sala) {
  const id = `sala-${sala.id}`;
  const salvar = async (evento) => {
    evento.preventDefault();
    const f = evento.currentTarget;
    limparErrosDeCampo(f);
    const ok = await executar(
      () =>
        api.patch(`/v1/salas/${sala.id}`, {
          nome: f.nome.value.trim(),
          capacidade: Number(f.capacidade.value),
          localizacao: textoOuNulo(f.localizacao.value),
        }),
      `Sala "${f.nome.value.trim()}" atualizada.`,
      f,
    );
    if (ok) carregarSalas();
  };
  const alternarAtiva = async () => {
    const acao = sala.ativa ? "desativar" : "reativar";
    if (sala.ativa && !window.confirm(`Desativar a ${sala.nome}? Ela deixa de receber reservas novas; as reservas existentes continuam valendo.`)) return;
    const ok = await executar(
      () => api.patch(`/v1/salas/${sala.id}`, { ativa: !sala.ativa }),
      `Sala "${sala.nome}" ${acao === "desativar" ? "desativada" : "reativada"}.`,
    );
    if (ok) carregarSalas();
  };
  return el(
    "li",
    { class: `cartao item-admin ${sala.ativa ? "" : "inativo"}` },
    el(
      "form",
      { onsubmit: salvar, "aria-label": `Editar ${sala.nome}`, novalidate: true },
      el(
        "div",
        { class: "linha" },
        el("div", {}, el("label", { for: `${id}-nome` }, "Nome"), el("input", { id: `${id}-nome`, name: "nome", value: sala.nome, required: true, maxlength: 120 })),
        el("div", {}, el("label", { for: `${id}-cap` }, "Capacidade"), el("input", { id: `${id}-cap`, name: "capacidade", type: "number", min: 1, value: sala.capacidade, required: true })),
        el("div", {}, el("label", { for: `${id}-loc` }, "Localização"), el("input", { id: `${id}-loc`, name: "localizacao", value: sala.localizacao ?? "", maxlength: 200 })),
      ),
      el(
        "div",
        { class: "acoes" },
        el("span", { class: "etiqueta" }, sala.ativa ? "ativa" : "desativada"),
        el("button", { type: "submit" }, "Salvar"),
        el("button", { type: "button", class: sala.ativa ? "perigo" : "", onclick: alternarAtiva }, sala.ativa ? "Desativar" : "Reativar"),
      ),
    ),
  );
}

async function carregarSalas() {
  try {
    const salas = await api.get("/v1/salas", { limit: 100 });
    listaSalas.replaceChildren(
      salas.length ? el("ul", { class: "lista-admin" }, salas.map(linhaSala)) : el("p", { class: "vazio" }, "Nenhuma sala cadastrada."),
    );
  } catch (erro) {
    tratarErro(erro, avisos);
  }
}

formSala.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  limparErrosDeCampo(formSala);
  const ok = await executar(
    () =>
      api.post("/v1/salas", {
        nome: formSala.nome.value.trim(),
        // Vazio vai como null: a API responde 422 "campo obrigatório" no campo certo.
        capacidade: formSala.capacidade.value ? Number(formSala.capacidade.value) : null,
        localizacao: textoOuNulo(formSala.localizacao.value),
        descricao: textoOuNulo(formSala.descricao.value),
      }),
    `Sala "${formSala.nome.value.trim()}" cadastrada.`,
    formSala,
  );
  if (ok) {
    formSala.reset();
    carregarSalas();
  }
});

// ---------------------------------------------------------------- usuários
function linhaUsuario(u) {
  const ehVoce = u.id === usuarioLogado.id;
  const seletor = el(
    "select",
    { id: `papel-${u.id}`, "aria-label": `Papel de ${u.nome}`, disabled: ehVoce },
    PAPEIS.map(([valor, rotulo]) => el("option", { value: valor, selected: valor === u.papel }, rotulo)),
  );
  seletor.addEventListener("change", async () => {
    const ok = await executar(
      () => api.patch(`/v1/usuarios/${u.id}`, { papel: seletor.value }),
      `Papel de ${u.nome} alterado para ${seletor.value}.`,
    );
    carregarUsuarios();
    return ok;
  });
  const alternarAtivo = async () => {
    if (u.is_active && !window.confirm(`Desativar ${u.nome}? A pessoa não conseguirá mais entrar.`)) return;
    const ok = await executar(
      () => api.patch(`/v1/usuarios/${u.id}`, { is_active: !u.is_active }),
      `${u.nome} ${u.is_active ? "desativado(a)" : "reativado(a)"}.`,
    );
    if (ok) carregarUsuarios();
  };
  return el(
    "tr",
    { class: u.is_active ? "" : "inativo" },
    el("td", {}, u.nome, ehVoce ? el("span", { class: "discreto" }, " (você)") : null),
    el("td", {}, u.email),
    el("td", {}, seletor),
    el("td", {}, u.is_active ? "Ativo" : "Desativado"),
    el(
      "td",
      { class: "acoes" },
      // Um admin não pode se desativar nem tirar o próprio papel (a API
      // também recusa com 409; aqui só evitamos o clique).
      ehVoce
        ? null
        : el("button", { type: "button", class: u.is_active ? "perigo" : "", onclick: alternarAtivo }, u.is_active ? "Desativar" : "Reativar"),
    ),
  );
}

async function carregarUsuarios() {
  try {
    const usuarios = await api.get("/v1/usuarios", { limit: 100 });
    listaUsuarios.replaceChildren(
      el(
        "div",
        { class: "tabela-rolavel" },
        el(
          "table",
          {},
          el(
            "thead",
            {},
            el(
              "tr",
              {},
              el("th", { scope: "col" }, "Nome"),
              el("th", { scope: "col" }, "E-mail"),
              el("th", { scope: "col" }, "Papel"),
              el("th", { scope: "col" }, "Situação"),
              el("th", { scope: "col" }, el("span", { class: "visualmente-oculto" }, "Ações")),
            ),
          ),
          el("tbody", {}, usuarios.map(linhaUsuario)),
        ),
      ),
    );
  } catch (erro) {
    tratarErro(erro, avisos);
  }
}

formUsuario.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  limparErrosDeCampo(formUsuario);
  const ok = await executar(
    () =>
      api.post("/v1/usuarios", {
        nome: formUsuario.nome.value.trim(),
        email: formUsuario.email.value.trim(),
        senha: formUsuario.senha.value,
        papel: formUsuario.papel.value,
      }),
    `Usuário ${formUsuario.email.value.trim()} cadastrado.`,
    formUsuario,
  );
  if (ok) {
    formUsuario.reset();
    carregarUsuarios();
  }
});

usuarioLogado = await iniciarPagina("admin");
if (usuarioLogado) {
  await Promise.all([carregarSalas(), carregarUsuarios()]);
}
