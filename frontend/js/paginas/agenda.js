// Agenda do dia em linha do tempo: salas nas linhas, horas (8h–20h) nas
// colunas. Clicar numa reserva abre o painel de detalhes (editar/cancelar,
// se puder). Atualiza a cada 30 s (polling). Por que polling e não
// WebSocket/SSE: ver docs/adr/ADR-003.

import { INTERVALO_ATUALIZACAO_MS } from "../../config.js";
import { api, mensagemDeErro } from "../api.js";
import * as datas from "../datas.js";
import { avisar, el } from "../dom.js";
import { iniciarPagina } from "../layout.js";
import { abrirEdicao, cancelarComConfirmacao } from "../reservas-ui.js";
import { temPapel } from "../sessao.js";

// A grade vai das 8h às 20h: 12 colunas, 720 minutos.
const HORA_INICIAL = 8;
const MINUTOS_NA_GRADE = 12 * 60;

const campoDia = document.getElementById("dia");
const areaAgenda = document.getElementById("agenda");
const grade = document.getElementById("grade");
const legenda = document.getElementById("legenda");
const semReservas = document.getElementById("sem-reservas");
const avisos = document.getElementById("avisos");
const detalhe = document.getElementById("detalhe");

let usuario;
let salas = [];
let reservas = [];
let selecionadaId = null;

const ehMinha = (r) => r.usuario_id === usuario.id;
const periodo = (r) => `${datas.hora(r.inicio)}–${datas.hora(r.fim)}`;

// Minutos desde as 8h (de São Paulo) do dia mostrado, presos entre 0 e 720.
function minutosNaGrade(instante, oitoHoras) {
  const m = (new Date(instante) - new Date(oitoHoras)) / 60000;
  return Math.min(Math.max(m, 0), MINUTOS_NA_GRADE);
}

function descricaoSala(sala) {
  return sala.localizacao ? `${sala.capacidade} pessoas, ${sala.localizacao}` : `${sala.capacidade} pessoas`;
}

function quando(reserva) {
  const dia = datas.paraCampos(reserva.inicio).data;
  const hoje = datas.hojeEmSaoPaulo();
  if (dia === hoje) return "hoje";
  if (dia === datas.somarDias(hoje, 1)) return "amanhã";
  if (dia === datas.somarDias(hoje, -1)) return "ontem";
  return datas.data(reserva.inicio);
}

function blocoReserva(r, oitoHoras) {
  const minha = ehMinha(r);
  const selecionada = r.id === selecionadaId;
  return el(
    "button",
    {
      type: "button",
      class: `bloco-reserva${minha ? " minha" : ""}${selecionada ? " selecionada" : ""}`,
      style: `--inicio: ${minutosNaGrade(r.inicio, oitoHoras)}; --fim: ${minutosNaGrade(r.fim, oitoHoras)};`,
      "data-id": r.id,
      "aria-pressed": String(selecionada),
      "aria-label": `${r.finalidade}, ${periodo(r)}, ${r.sala.nome}, reservada por ${minha ? "você" : r.usuario.nome}`,
      onclick: () => selecionar(r.id),
    },
    el("span", { class: "bloco-titulo" }, r.finalidade),
    el("span", { class: "bloco-hora" }, `${periodo(r)}${minha ? ", você" : ""}`),
  );
}

function desenhar() {
  const dia = campoDia.value;
  const oitoHoras = datas.isoSaoPaulo(dia, `${String(HORA_INICIAL).padStart(2, "0")}:00`);

  const porSala = new Map(salas.map((s) => [s.id, []]));
  for (const r of reservas) porSala.get(r.sala_id)?.push(r);
  const totalNoDia = [...porSala.values()].reduce((n, lista) => n + lista.length, 0);

  // Dia sem reservas: a caixa tracejada entra no lugar da grade.
  const vazio = totalNoDia === 0;
  grade.hidden = vazio;
  legenda.hidden = vazio;
  semReservas.hidden = !vazio;
  if (vazio) {
    areaAgenda.replaceChildren();
    mostrarDetalhe();
    return;
  }

  // Guarda qual reserva estava com o foco para devolvê-lo depois de redesenhar.
  const focada = document.activeElement?.closest?.(".bloco-reserva")?.dataset.id;

  const celulas = [
    el("div", { class: "agenda-canto", style: "grid-area: 1 / 1;" }),
    el(
      "div",
      { class: "agenda-regua", style: "grid-area: 1 / 2;", "aria-hidden": "true" },
      Array.from({ length: 12 }, (_, i) => el("span", {}, `${HORA_INICIAL + i}h`)),
    ),
  ];
  salas.forEach((sala, i) => {
    // Linha e coluna explícitas: a camada do "agora" divide a coluna 2 com
    // as faixas, e o posicionamento automático as empurraria para o lado.
    const linha = i + 2;
    const ultima = i === salas.length - 1 ? " ultima" : "";
    // Reserva inteira fora das 8h–20h não tem onde aparecer na grade.
    const doDia = porSala
      .get(sala.id)
      .filter((r) => minutosNaGrade(r.fim, oitoHoras) > minutosNaGrade(r.inicio, oitoHoras));
    celulas.push(
      el(
        "div",
        { class: `agenda-sala${ultima}`, style: `grid-area: ${linha} / 1;` },
        el("strong", {}, sala.nome),
        el("span", {}, descricaoSala(sala)),
      ),
      el(
        "div",
        { class: `agenda-faixa${ultima}`, style: `grid-area: ${linha} / 2;`, role: "group", "aria-label": `Reservas da ${sala.nome}` },
        doDia.length
          ? doDia.map((r) => blocoReserva(r, oitoHoras))
          : el("span", { class: "visualmente-oculto" }, "Livre o dia todo"),
      ),
    );
  });

  // Linha "agora": só no dia de hoje e entre 8h e 20h. Fica numa camada que
  // cobre a coluna das horas de todas as salas.
  const agora = new Date();
  const minutoAgora = (agora - new Date(oitoHoras)) / 60000;
  const mostrarAgora = dia === datas.hojeEmSaoPaulo() && minutoAgora >= 0 && minutoAgora <= MINUTOS_NA_GRADE;
  if (mostrarAgora) {
    celulas.push(
      el(
        "div",
        { class: "agenda-camada-agora", style: `grid-row: 2 / span ${salas.length};`, "aria-hidden": "true" },
        el("div", { class: "agenda-agora", style: `--pos: ${minutoAgora};` }),
      ),
    );
  }
  document.getElementById("legenda-agora").hidden = !mostrarAgora;
  document.getElementById("texto-agora").textContent = `Agora, ${datas.hora(agora.toISOString())}`;

  areaAgenda.replaceChildren(...celulas);
  if (focada) areaAgenda.querySelector(`.bloco-reserva[data-id="${focada}"]`)?.focus();
  mostrarDetalhe();
}

function selecionar(id) {
  selecionadaId = selecionadaId === id ? null : id;
  for (const bloco of areaAgenda.querySelectorAll(".bloco-reserva")) {
    const marcado = Number(bloco.dataset.id) === selecionadaId;
    bloco.classList.toggle("selecionada", marcado);
    bloco.setAttribute("aria-pressed", String(marcado));
  }
  mostrarDetalhe();
}

function fecharDetalhe() {
  const id = selecionadaId;
  selecionar(null);
  areaAgenda.querySelector(`.bloco-reserva[data-id="${id}"]`)?.focus();
}

function mostrarDetalhe() {
  const r = reservas.find((x) => x.id === selecionadaId && salas.some((s) => s.id === x.sala_id));
  if (!r) {
    selecionadaId = null;
    detalhe.hidden = true;
    detalhe.replaceChildren();
    return;
  }
  const minha = ehMinha(r);
  // Reserva que já começou não pode ser alterada (regra do domínio; a API
  // também recusa). Esconder botões só decide o que MOSTRAR: quem bloqueia
  // de verdade é a API (403/409).
  const jaComecou = new Date(r.inicio) <= new Date();
  const podeAlterar = !jaComecou && (minha || temPapel(usuario, "responsavel"));

  detalhe.replaceChildren(
    el(
      "div",
      {},
      el("h2", { id: "titulo-detalhe" }, r.finalidade),
      el("p", {}, `${r.sala.nome}, ${quando(r)}, ${periodo(r)}. Reservada por ${minha ? "você" : r.usuario.nome}.`),
      jaComecou && (minha || temPapel(usuario, "responsavel"))
        ? el("p", {}, "Esta reserva já começou e não pode mais ser alterada.")
        : null,
    ),
    el(
      "div",
      { class: "acoes" },
      podeAlterar
        ? el("button", { type: "button", onclick: () => abrirEdicao(r, salas, avisos, carregar) }, "Editar")
        : null,
      podeAlterar
        ? el(
            "button",
            { type: "button", class: "perigo", onclick: () => cancelarComConfirmacao(r, avisos, carregar) },
            "Cancelar reserva",
          )
        : null,
      el("button", { type: "button", class: "botao-fantasma", onclick: fecharDetalhe }, "Fechar"),
    ),
  );
  detalhe.hidden = false;
}

async function carregar() {
  const dia = campoDia.value;
  if (!dia) return;
  document.getElementById("data-extenso").textContent = datas.dataPorExtenso(dia);
  for (const link of document.querySelectorAll(".link-reservar")) link.href = `reservar.html?data=${dia}`;
  try {
    const { de, ate } = datas.janelaDoDia(dia);
    [salas, reservas] = await Promise.all([
      api.get("/v1/salas", { ativas: true, limit: 100 }),
      api.get("/v1/reservas", { de, ate, status: "ativa", limit: 500 }),
    ]);
    avisar(avisos, "");
    desenhar();
  } catch (erro) {
    avisar(avisos, mensagemDeErro(erro), "erro");
  }
}

function irPara(dia) {
  campoDia.value = dia;
  selecionadaId = null;
  carregar();
}

usuario = await iniciarPagina();
if (usuario) {
  campoDia.value = datas.hojeEmSaoPaulo();
  campoDia.addEventListener("change", () => campoDia.value && irPara(campoDia.value));
  document.getElementById("hoje").addEventListener("click", () => irPara(datas.hojeEmSaoPaulo()));
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
