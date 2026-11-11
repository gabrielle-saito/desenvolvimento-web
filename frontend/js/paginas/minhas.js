import { api } from "../api.js";
import { el } from "../dom.js";
import { iniciarPagina } from "../layout.js";
import { abrirEdicao, cancelarComConfirmacao, tabelaReservas, tratarErro } from "../reservas-ui.js";

const avisos = document.getElementById("avisos");
const lista = document.getElementById("lista");
let salas = [];

async function carregar() {
  try {
    const reservas = await api.get("/v1/reservas", {
      minhas: true,
      status: "ativa",
      de: new Date().toISOString(),
      limit: 500,
    });
    lista.replaceChildren(
      tabelaReservas(reservas, {
        mostrarDono: false,
        aoEditar: (r) => abrirEdicao(r, salas, avisos, carregar),
        aoCancelar: (r) => cancelarComConfirmacao(r, avisos, carregar),
      }),
    );
  } catch (erro) {
    tratarErro(erro, avisos);
  }
}

const usuario = await iniciarPagina();
if (usuario) {
  lista.append(el("p", { class: "discreto" }, "Carregando…"));
  salas = await api.get("/v1/salas", { limit: 100 });
  await carregar();
}
