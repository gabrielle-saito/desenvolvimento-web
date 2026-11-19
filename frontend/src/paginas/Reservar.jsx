// Consultar disponibilidade e reservar (casos de uso 1 e 2).
// Aceita ?data=AAAA-MM-DD (vindo da Agenda) e ?sala=ID (vindo do catálogo).

import { useEffect, useState } from "react";
import { useSearchParams } from "react-router";

import { api, ErroApi, errosPorCampo, mensagemDeErro } from "../api/cliente.js";
import Aviso from "../componentes/Aviso.jsx";
import Campo from "../componentes/Campo.jsx";
import Carregando from "../componentes/Carregando.jsx";
import EtiquetasRecursos from "../componentes/EtiquetasRecursos.jsx";
import * as datas from "../util/datas.js";
import { useTitulo } from "../util/useCarregar.js";

const DATA_VALIDA = /^\d{4}-\d{2}-\d{2}$/;

function CartaoDisponibilidade({ item, aoReservar, reservando }) {
  const { sala, livre, reservas_conflitantes: conflitos } = item;
  return (
    <article className={`cartao sala cartao-vinho cartao-disponibilidade ${livre ? "sala-livre" : "sala-ocupada"}`}>
      <h3>{sala.nome}</h3>
      <p className="discreto">
        {sala.capacidade} pessoas{sala.localizacao ? ` · ${sala.localizacao}` : ""}
      </p>
      {sala.descricao ? <p>{sala.descricao}</p> : null}
      <EtiquetasRecursos recursos={sala.recursos} />
      {livre ? (
        <>
          <p className="livre">Livre neste horário</p>
          <button type="button" className="primario botao-reservar" onClick={() => aoReservar(sala)} disabled={reservando} aria-label={`Reservar ${sala.nome}`}>
            Reservar
          </button>
        </>
      ) : (
        <div>
          <p className="ocupada">Ocupada:</p>
          <ul className="horarios">
            {conflitos.map((r) => (
              <li key={r.id}>
                {datas.hora(r.inicio)} – {datas.hora(r.fim)}
                {r.detalhes_ocultos ? "" : ` · ${r.usuario.nome}`}
              </li>
            ))}
          </ul>
        </div>
      )}
    </article>
  );
}

export default function Reservar() {
  useTitulo("Reservar sala");
  const [params, setParams] = useSearchParams();
  const salaEscolhida = Number(params.get("sala")) || null;
  const dataInicial = params.get("data");

  const [campos, setCampos] = useState({
    data: DATA_VALIDA.test(dataInicial ?? "") ? dataInicial : datas.hojeEmSaoPaulo(),
    inicio: "09:00",
    fim: "10:00",
    capacidade_minima: "",
    finalidade: "",
  });
  const [erros, setErros] = useState({});
  const [aviso, setAviso] = useState(null);
  const [consulta, setConsulta] = useState({ carregando: false, dados: null });
  const [reservando, setReservando] = useState(false);

  const mudar = (evento) => setCampos((c) => ({ ...c, [evento.target.name]: evento.target.value }));
  const periodo = () => ({
    inicio: datas.isoSaoPaulo(campos.data, campos.inicio),
    fim: datas.isoSaoPaulo(campos.data, campos.fim),
  });

  async function consultar() {
    // Validação local: só conveniência (resposta imediata). A que vale é a da API.
    const faltando = {};
    if (!campos.data) faltando.data = "Escolha a data.";
    if (!campos.inicio) faltando.inicio = "Informe o início.";
    if (!campos.fim) faltando.fim = "Informe o fim.";
    setErros(faltando);
    if (Object.keys(faltando).length) return;

    setConsulta((c) => ({ ...c, carregando: true }));
    try {
      const dados = await api.get("/v1/disponibilidade", { ...periodo(), capacidade_minima: campos.capacidade_minima });
      setConsulta({ carregando: false, dados });
    } catch (erro) {
      setErros(errosPorCampo(erro));
      setAviso({ texto: mensagemDeErro(erro), tipo: "erro" });
      setConsulta({ carregando: false, dados: null });
    }
  }

  // Vindo do catálogo com uma sala escolhida: já mostra o horário padrão.
  useEffect(() => {
    if (salaEscolhida) consultar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function reservar(sala) {
    if (!campos.finalidade.trim()) {
      setErros({ finalidade: "Informe a finalidade para reservar." });
      document.getElementById("finalidade").focus();
      return;
    }
    const { inicio, fim } = periodo();
    if (!window.confirm(`Confirmar a reserva da ${sala.nome}, ${datas.data(inicio)}, ${datas.hora(inicio)}–${datas.hora(fim)}?`)) return;
    setReservando(true);
    try {
      const reserva = await api.post("/v1/reservas", { sala_id: sala.id, inicio, fim, finalidade: campos.finalidade.trim() });
      setAviso({
        texto: `Reserva confirmada: ${reserva.sala.nome}, ${datas.data(reserva.inicio)}, ${datas.hora(reserva.inicio)}–${datas.hora(reserva.fim)}.`,
        tipo: "sucesso",
      });
    } catch (erro) {
      // 409: ex.: alguém reservou esta sala segundos antes. A lista é
      // atualizada para a pessoa escolher outra sala ou horário.
      setErros(errosPorCampo(erro));
      setAviso({ texto: erro instanceof ErroApi && erro.status === 409 ? erro.problema.detail : mensagemDeErro(erro), tipo: "erro" });
    } finally {
      setReservando(false);
    }
    await consultar();
  }

  const todas = consulta.dados?.salas ?? [];
  const filtradas = salaEscolhida ? todas.filter((i) => i.sala.id === salaEscolhida) : todas;
  // Livres primeiro: é o que a pessoa procura.
  const ordenadas = [...filtradas].sort((a, b) => Number(b.livre) - Number(a.livre));

  return (
    <>
      <h1>Consultar e reservar</h1>
      <form
        className="cartao"
        noValidate
        onSubmit={(e) => {
          e.preventDefault();
          setAviso(null);
          consultar();
        }}
      >
        <div className="linha">
          <Campo id="data" rotulo="Data" type="date" name="data" required value={campos.data} onChange={mudar} erro={erros.data} />
          <Campo id="inicio" rotulo="Início" type="time" step={300} name="inicio" required value={campos.inicio} onChange={mudar} erro={erros.inicio} />
          <Campo id="fim" rotulo="Fim" type="time" step={300} name="fim" required value={campos.fim} onChange={mudar} erro={erros.fim} />
          <Campo
            id="capacidade"
            rotulo="Pessoas (mínimo)"
            type="number"
            min={1}
            inputMode="numeric"
            name="capacidade_minima"
            value={campos.capacidade_minima}
            onChange={mudar}
            erro={erros.capacidade_minima}
          />
        </div>
        <Campo
          id="finalidade"
          rotulo="Finalidade da reunião"
          name="finalidade"
          maxLength={500}
          placeholder="Ex.: Planejamento da sprint"
          value={campos.finalidade}
          onChange={mudar}
          erro={erros.finalidade}
        />
        <div className="acoes">
          <button type="submit" className="primario" disabled={consulta.carregando}>
            {consulta.carregando ? "Consultando…" : "Ver salas livres"}
          </button>
        </div>
      </form>

      <Aviso aviso={aviso} />

      {consulta.carregando && !consulta.dados ? <Carregando texto="Consultando as salas…" /> : null}

      {consulta.dados ? (
        <section aria-labelledby="titulo-resultado" aria-busy={consulta.carregando}>
          <h2 id="titulo-resultado">Salas no período</h2>
          {salaEscolhida ? (
            <p className="discreto">
              Mostrando só a sala escolhida no catálogo.{" "}
              <button
                type="button"
                className="botao-link"
                onClick={() => {
                  const p = new URLSearchParams(params);
                  p.delete("sala");
                  setParams(p, { replace: true });
                }}
              >
                Ver todas as salas
              </button>
            </p>
          ) : null}
          <div className="grade-salas">
            {/* Nenhuma livre: a API manda uma mensagem clara (caso de uso 2). */}
            {consulta.dados.mensagem && !salaEscolhida ? (
              <p className="aviso aviso-info largura-total">{consulta.dados.mensagem}</p>
            ) : null}
            {ordenadas.length === 0 ? (
              <p className="vazio largura-total">Nenhuma sala atende a esses critérios.</p>
            ) : null}
            {ordenadas.map((item) => (
              <CartaoDisponibilidade key={item.sala.id} item={item} aoReservar={reservar} reservando={reservando} />
            ))}
          </div>
        </section>
      ) : null}
    </>
  );
}
