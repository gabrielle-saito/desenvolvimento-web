// Lista de reservas com editar/cancelar (usada em "Minhas reservas" e na
// área do responsável).

import { api, ErroApi, mensagemDeErro } from "./api.js";
import * as datas from "./datas.js";
import { avisar, el, limparErrosDeCampo, mostrarErrosDeCampo } from "./dom.js";

// Trata o erro de uma ação e escreve a mensagem certa para o usuário.
export function tratarErro(erro, regiaoAvisos, form) {
  if (erro instanceof ErroApi && erro.status === 422 && form && erro.problema.erros) {
    const sobras = mostrarErrosDeCampo(form, erro.problema.erros);
    avisar(regiaoAvisos, sobras.length ? sobras.join(" ") : "Corrija os campos destacados.", "erro");
    return;
  }
  avisar(regiaoAvisos, mensagemDeErro(erro), "erro");
}

function linhaReserva(reserva, { aoEditar, aoCancelar, mostrarDono }) {
  return el(
    "tr",
    {},
    el("td", {}, datas.data(reserva.inicio)),
    el("td", {}, `${datas.hora(reserva.inicio)} – ${datas.hora(reserva.fim)}`),
    el("td", {}, reserva.sala.nome),
    mostrarDono ? el("td", {}, reserva.usuario.nome) : null,
    el("td", {}, reserva.finalidade),
    el(
      "td",
      { class: "acoes" },
      el("button", { type: "button", onclick: () => aoEditar(reserva) }, "Editar"),
      el(
        "button",
        { type: "button", class: "perigo", onclick: () => aoCancelar(reserva) },
        "Cancelar",
      ),
    ),
  );
}

export function tabelaReservas(reservas, opcoes) {
  if (!reservas.length) {
    return el("p", { class: "vazio" }, "Não há reservas para o período.");
  }
  return el(
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
          el("th", { scope: "col" }, "Data"),
          el("th", { scope: "col" }, "Horário"),
          el("th", { scope: "col" }, "Sala"),
          opcoes.mostrarDono ? el("th", { scope: "col" }, "Reservado por") : null,
          el("th", { scope: "col" }, "Finalidade"),
          el("th", { scope: "col" }, el("span", { class: "visualmente-oculto" }, "Ações")),
        ),
      ),
      el("tbody", {}, reservas.map((r) => linhaReserva(r, opcoes))),
    ),
  );
}

export async function cancelarComConfirmacao(reserva, regiaoAvisos, aoConcluir) {
  const texto = `Cancelar a reserva da ${reserva.sala.nome} em ${datas.data(reserva.inicio)}, ${datas.hora(reserva.inicio)}–${datas.hora(reserva.fim)}?`;
  if (!window.confirm(texto)) return;
  try {
    await api.post(`/v1/reservas/${reserva.id}/cancelamento`);
    avisar(regiaoAvisos, "Reserva cancelada. O horário ficou livre.", "sucesso");
  } catch (erro) {
    tratarErro(erro, regiaoAvisos);
  }
  await aoConcluir();
}

// Abre o <dialog> de edição. Envia a "versao" lida (locking otimista):
// se outra pessoa salvou antes, a API responde 409 e pedimos para recarregar.
export function abrirEdicao(reserva, salas, regiaoAvisos, aoConcluir) {
  const campos = { inicio: datas.paraCampos(reserva.inicio), fim: datas.paraCampos(reserva.fim) };
  const avisosDialogo = el("div", { "aria-live": "assertive" });
  const opcoesSala = salas
    .filter((s) => s.ativa || s.id === reserva.sala_id)
    .map((s) =>
      el("option", { value: s.id, selected: s.id === reserva.sala_id }, `${s.nome} (${s.capacidade} pessoas)`),
    );

  const form = el(
    "form",
    { id: "form-editar", method: "dialog" },
    el("h2", {}, "Editar reserva"),
    avisosDialogo,
    el("label", { for: "ed-sala" }, "Sala"),
    el("select", { id: "ed-sala", name: "sala_id", required: true }, opcoesSala),
    el("label", { for: "ed-data" }, "Data"),
    el("input", { id: "ed-data", name: "data", type: "date", required: true, value: campos.inicio.data }),
    el(
      "div",
      { class: "linha" },
      el(
        "div",
        {},
        el("label", { for: "ed-inicio" }, "Início"),
        el("input", { id: "ed-inicio", name: "inicio", type: "time", required: true, value: campos.inicio.hora, step: 300 }),
      ),
      el(
        "div",
        {},
        el("label", { for: "ed-fim" }, "Fim"),
        el("input", { id: "ed-fim", name: "fim", type: "time", required: true, value: campos.fim.hora, step: 300 }),
      ),
    ),
    el("label", { for: "ed-finalidade" }, "Finalidade"),
    el("input", { id: "ed-finalidade", name: "finalidade", required: true, maxlength: 500, value: reserva.finalidade }),
    el(
      "div",
      { class: "acoes" },
      el("button", { type: "submit", class: "primario" }, "Salvar"),
      el("button", { type: "button", onclick: () => dialogo.close() }, "Fechar"),
    ),
  );
  const dialogo = el("dialog", { "aria-labelledby": "titulo-editar" }, form);
  form.querySelector("h2").id = "titulo-editar";

  form.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    limparErrosDeCampo(form);
    const dados = new FormData(form);
    const corpo = {
      versao: reserva.versao,
      sala_id: Number(dados.get("sala_id")),
      inicio: datas.isoSaoPaulo(dados.get("data"), dados.get("inicio")),
      fim: datas.isoSaoPaulo(dados.get("data"), dados.get("fim")),
      finalidade: dados.get("finalidade"),
    };
    try {
      await api.patch(`/v1/reservas/${reserva.id}`, corpo);
      dialogo.close();
      avisar(regiaoAvisos, "Reserva atualizada.", "sucesso");
      await aoConcluir();
    } catch (erro) {
      if (erro instanceof ErroApi && erro.problema.type === "/problemas/versao-desatualizada") {
        dialogo.close();
        avisar(regiaoAvisos, "Outra pessoa alterou esta reserva enquanto você editava. A lista foi recarregada: confira e tente de novo.", "erro");
        await aoConcluir();
        return;
      }
      tratarErro(erro, avisosDialogo, form);
    }
  });

  dialogo.addEventListener("close", () => dialogo.remove());
  document.body.append(dialogo);
  dialogo.showModal();
}
