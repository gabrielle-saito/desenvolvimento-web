// Área do responsável (caso de uso 8): qualquer reserva, editar/cancelar.
// A API também confere o papel: um colaborador que abrir esta página na
// mão vê "acesso negado" aqui e recebe 403 se tentar alterar algo.

import { api } from "../api.js";
import * as datas from "../datas.js";
import { el } from "../dom.js";
import { iniciarPagina } from "../layout.js";
import { abrirEdicao, cancelarComConfirmacao, tabelaReservas, tratarErro } from "../reservas-ui.js";

const form = document.getElementById("filtro");
const avisos = document.getElementById("avisos");
const lista = document.getElementById("lista");
let salas = [];

async function carregar() {
  try {
    const reservas = await api.get("/v1/reservas", {
      de: datas.isoSaoPaulo(form.de.value, "00:00"),
      ate: datas.isoSaoPaulo(datas.somarDias(form.ate.value, 1), "00:00"),
      sala_id: form.sala_id.value,
      status: "ativa",
      limit: 500,
    });
    lista.replaceChildren(
      tabelaReservas(reservas, {
        mostrarDono: true,
        aoEditar: (r) => abrirEdicao(r, salas, avisos, carregar),
        aoCancelar: (r) => cancelarComConfirmacao(r, avisos, carregar),
      }),
    );
  } catch (erro) {
    tratarErro(erro, avisos, form);
  }
}

const usuario = await iniciarPagina("responsavel");
if (usuario) {
  const hoje = datas.hojeEmSaoPaulo();
  form.de.value = hoje;
  form.ate.value = datas.somarDias(hoje, 7);
  salas = await api.get("/v1/salas", { limit: 100 });
  form.sala_id.append(...salas.map((s) => el("option", { value: s.id }, s.nome)));
  form.addEventListener("submit", (evento) => {
    evento.preventDefault();
    carregar();
  });
  await carregar();
}
