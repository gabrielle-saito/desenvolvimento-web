// Agenda do dia, agrupada por sala, atualizada a cada 30 s (polling).
// Por que polling e não WebSocket/SSE: ver docs/adr/ADR-003.

import { INTERVALO_ATUALIZACAO_MS } from "../../config.js";
import { api, mensagemDeErro } from "../api.js";
import * as datas from "../datas.js";
import { avisar, el } from "../dom.js";
import { iniciarPagina } from "../layout.js";

const campoDia = document.getElementById("dia");
const areaAgenda = document.getElementById("agenda");
const avisos = document.getElementById("avisos");
const atualizado = document.getElementById("atualizado");

function cartaoSala(sala, reservas) {
  const itens = reservas.map((r) =>
    el(
      "li",
      {},
      el("strong", {}, `${datas.hora(r.inicio)} – ${datas.hora(r.fim)}`),
      " ",
      el("span", {}, r.finalidade),
      el("span", { class: "discreto bloco" }, r.usuario.nome),
    ),
  );
  return el(
    "article",
    { class: "cartao sala" },
    el("h2", {}, sala.nome),
    el(
      "p",
      { class: "discreto" },
      `${sala.capacidade} pessoas${sala.localizacao ? ` · ${sala.localizacao}` : ""}`,
      sala.ativa ? null : " · desativada",
    ),
    itens.length ? el("ul", { class: "horarios" }, itens) : el("p", { class: "livre" }, "Livre o dia todo"),
  );
}

async function carregar() {
  const dia = campoDia.value;
  if (!dia) return;
  try {
    const { de, ate } = datas.janelaDoDia(dia);
    const [salas, reservas] = await Promise.all([
      api.get("/v1/salas", { limit: 100 }),
      api.get("/v1/reservas", { de, ate, status: "ativa", limit: 500 }),
    ]);
    const porSala = new Map();
    for (const r of reservas) {
      if (!porSala.has(r.sala_id)) porSala.set(r.sala_id, []);
      porSala.get(r.sala_id).push(r);
    }
    // Salas ativas sempre; desativadas só se ainda tiverem reserva no dia.
    const visiveis = salas.filter((s) => s.ativa || porSala.has(s.id));
    avisar(avisos, reservas.length ? "" : "Não há reservas para o período.", "info");
    areaAgenda.replaceChildren(...visiveis.map((s) => cartaoSala(s, porSala.get(s.id) || [])));
    atualizado.textContent = `Atualizado às ${datas.hora(new Date().toISOString())}. Atualiza sozinha a cada ${INTERVALO_ATUALIZACAO_MS / 1000} s.`;
  } catch (erro) {
    avisar(avisos, mensagemDeErro(erro), "erro");
  }
}

function mudarDia(dias) {
  campoDia.value = datas.somarDias(campoDia.value, dias);
  carregar();
}

const usuario = await iniciarPagina();
if (usuario) {
  campoDia.value = datas.hojeEmSaoPaulo();
  campoDia.addEventListener("change", carregar);
  document.getElementById("anterior").addEventListener("click", () => mudarDia(-1));
  document.getElementById("proximo").addEventListener("click", () => mudarDia(1));
  document.getElementById("hoje").addEventListener("click", () => {
    campoDia.value = datas.hojeEmSaoPaulo();
    carregar();
  });
  await carregar();

  // Polling: só consulta com a aba VISÍVEL (aba escondida não gasta servidor)
  // e atualiza na hora quando o usuário volta para a aba.
  setInterval(() => {
    if (document.visibilityState === "visible") carregar();
  }, INTERVALO_ATUALIZACAO_MS);
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") carregar();
  });
}
