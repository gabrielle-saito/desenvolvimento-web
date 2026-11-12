// Consultar disponibilidade e reservar (casos de uso 1 e 2).

import { api, ErroApi } from "../api.js";
import * as datas from "../datas.js";
import { avisar, el, limparErrosDeCampo, mostrarErrosDeCampo } from "../dom.js";
import { iniciarPagina } from "../layout.js";
import { tratarErro } from "../reservas-ui.js";

const form = document.getElementById("consulta");
const avisos = document.getElementById("avisos");
const resultado = document.getElementById("resultado");
const areaSalas = document.getElementById("salas");

function periodoDoFormulario() {
  return {
    inicio: datas.isoSaoPaulo(form.data.value, form.inicio.value),
    fim: datas.isoSaoPaulo(form.data.value, form.fim.value),
  };
}

function validarLocalmente() {
  // Só conveniência (resposta imediata). A validação que vale é a da API.
  const erros = [];
  if (!form.data.value) erros.push({ campo: "data", mensagem: "Escolha a data." });
  if (!form.inicio.value) erros.push({ campo: "inicio", mensagem: "Informe o início." });
  if (!form.fim.value) erros.push({ campo: "fim", mensagem: "Informe o fim." });
  mostrarErrosDeCampo(form, erros);
  return erros.length === 0;
}

async function reservar(sala) {
  limparErrosDeCampo(form);
  if (!form.finalidade.value.trim()) {
    mostrarErrosDeCampo(form, [{ campo: "finalidade", mensagem: "Informe a finalidade para reservar." }]);
    form.finalidade.focus();
    return;
  }
  const { inicio, fim } = periodoDoFormulario();
  if (!window.confirm(`Confirmar a reserva da ${sala.nome}, ${datas.data(inicio)}, ${datas.hora(inicio)}–${datas.hora(fim)}?`)) return;
  try {
    const reserva = await api.post("/v1/reservas", {
      sala_id: sala.id,
      inicio,
      fim,
      finalidade: form.finalidade.value.trim(),
    });
    avisar(avisos, `Reserva confirmada: ${reserva.sala.nome}, ${datas.data(reserva.inicio)}, ${datas.hora(reserva.inicio)}–${datas.hora(reserva.fim)}.`, "sucesso");
    await consultar();
  } catch (erro) {
    if (erro instanceof ErroApi && erro.status === 409) {
      // Ex.: alguém reservou esta sala segundos antes. Mostra o motivo e
      // atualiza a lista para o usuário escolher outra sala/horário.
      avisar(avisos, erro.problema.detail, "erro");
      await consultar();
      return;
    }
    tratarErro(erro, avisos, form);
  }
}

function cartaoSala({ sala, livre, reservas_conflitantes: conflitos }) {
  return el(
    "article",
    { class: `cartao sala ${livre ? "sala-livre" : "sala-ocupada"}` },
    el("h3", {}, sala.nome),
    el("p", { class: "discreto" }, `${sala.capacidade} pessoas${sala.localizacao ? ` · ${sala.localizacao}` : ""}`),
    sala.descricao ? el("p", {}, sala.descricao) : null,
    livre
      ? el("p", { class: "livre" }, "Livre neste horário")
      : el(
          "div",
          {},
          el("p", { class: "ocupada" }, "Ocupada:"),
          el(
            "ul",
            { class: "horarios" },
            conflitos.map((r) =>
              el("li", {}, `${datas.hora(r.inicio)} – ${datas.hora(r.fim)} · ${r.usuario.nome}`),
            ),
          ),
        ),
    livre
      ? el("button", { type: "button", class: "primario", onclick: () => reservar(sala) }, `Reservar ${sala.nome}`)
      : null,
  );
}

async function consultar() {
  if (!validarLocalmente()) return;
  const { inicio, fim } = periodoDoFormulario();
  try {
    const dados = await api.get("/v1/disponibilidade", {
      inicio,
      fim,
      capacidade_minima: form.capacidade_minima.value,
    });
    // Livres primeiro: é o que o usuário procura.
    const ordenadas = [...dados.salas].sort((a, b) => Number(b.livre) - Number(a.livre));
    areaSalas.replaceChildren(
      // Nenhuma livre: a API manda uma mensagem clara (caso de uso 2).
      dados.mensagem ? el("p", { class: "aviso aviso-info largura-total" }, dados.mensagem) : "",
      ...ordenadas.map(cartaoSala),
    );
    resultado.hidden = false;
  } catch (erro) {
    tratarErro(erro, avisos, form);
  }
}

const usuario = await iniciarPagina();
if (usuario) {
  form.data.value = datas.hojeEmSaoPaulo();
  form.addEventListener("submit", (evento) => {
    evento.preventDefault();
    avisar(avisos, "");
    consultar();
  });
}
