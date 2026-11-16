// Agenda do dia em linha do tempo: salas nas linhas, horas (8h–20h) nas
// colunas. Clicar numa reserva abre o painel de detalhes (editar/cancelar,
// se puder). Atualiza a cada 30 s (polling) só com a aba visível. Por que
// polling e não WebSocket/SSE: ver docs/adr/ADR-003.

import { useEffect, useState } from "react";
import { Link } from "react-router";

import { api, mensagemDeErro } from "../api/cliente.js";
import Aviso from "../componentes/Aviso.jsx";
import Carregando from "../componentes/Carregando.jsx";
import DialogoEditarReserva from "../componentes/DialogoEditarReserva.jsx";
import { INTERVALO_ATUALIZACAO_MS } from "../config.js";
import { useAuth } from "../contexto/AuthContext.jsx";
import * as datas from "../util/datas.js";
import { cancelarReserva, jaComecou, periodo } from "../util/reservas.js";
import { useCarregar, useTitulo } from "../util/useCarregar.js";

// A grade vai das 8h às 20h: 12 colunas, 720 minutos.
const HORA_INICIAL = 8;
const MINUTOS_NA_GRADE = 12 * 60;

// Minutos desde as 8h (de São Paulo) do dia mostrado, presos entre 0 e 720.
function minutosNaGrade(instante, oitoHoras) {
  const m = (new Date(instante) - new Date(oitoHoras)) / 60000;
  return Math.min(Math.max(m, 0), MINUTOS_NA_GRADE);
}

function descricaoSala(sala) {
  const pessoas = `${sala.capacidade} ${sala.capacidade === 1 ? "pessoa" : "pessoas"}`;
  return sala.localizacao ? `${pessoas}, ${sala.localizacao}` : pessoas;
}

function quando(reserva) {
  const dia = datas.paraCampos(reserva.inicio).data;
  const hoje = datas.hojeEmSaoPaulo();
  if (dia === hoje) return "hoje";
  if (dia === datas.somarDias(hoje, 1)) return "amanhã";
  if (dia === datas.somarDias(hoje, -1)) return "ontem";
  return datas.data(reserva.inicio);
}

function BlocoReserva({ reserva, oitoHoras, minha, selecionada, aoClicar }) {
  const dono = minha ? "você" : reserva.usuario.nome;
  return (
    <button
      type="button"
      className={`bloco-reserva${minha ? " minha" : ""}${selecionada ? " selecionada" : ""}`}
      style={{ "--inicio": minutosNaGrade(reserva.inicio, oitoHoras), "--fim": minutosNaGrade(reserva.fim, oitoHoras) }}
      data-id={reserva.id}
      aria-pressed={selecionada}
      aria-label={`${reserva.finalidade}, ${periodo(reserva)}, ${reserva.sala.nome}, reservada por ${dono}`}
      onClick={aoClicar}
    >
      <span className="bloco-titulo">{reserva.finalidade}</span>
      <span className="bloco-hora">
        {periodo(reserva)}
        {minha ? ", você" : ""}
      </span>
    </button>
  );
}

function Grade({ dia, salas, reservas, ehMinha, selecionadaId, aoSelecionar }) {
  const oitoHoras = datas.isoSaoPaulo(dia, `${String(HORA_INICIAL).padStart(2, "0")}:00`);
  const agora = new Date();
  const minutoAgora = (agora - new Date(oitoHoras)) / 60000;
  const mostrarAgora = dia === datas.hojeEmSaoPaulo() && minutoAgora >= 0 && minutoAgora <= MINUTOS_NA_GRADE;

  return (
    <>
      <div className="agenda-rolavel">
        <div className="agenda">
          <div className="agenda-canto" style={{ gridArea: "1 / 1" }} />
          <div className="agenda-regua" style={{ gridArea: "1 / 2" }} aria-hidden="true">
            {Array.from({ length: 12 }, (_, i) => (
              <span key={i}>{HORA_INICIAL + i}h</span>
            ))}
          </div>
          {salas.map((sala, i) => {
            // Linha e coluna explícitas: a camada do "agora" divide a coluna 2
            // com as faixas, e o posicionamento automático as empurraria.
            const linha = i + 2;
            const ultima = i === salas.length - 1 ? " ultima" : "";
            // Reserva inteira fora das 8h–20h não tem onde aparecer na grade.
            const doDia = reservas.filter(
              (r) => r.sala_id === sala.id && minutosNaGrade(r.fim, oitoHoras) > minutosNaGrade(r.inicio, oitoHoras),
            );
            return [
              <div key={`s${sala.id}`} className={`agenda-sala${ultima}`} style={{ gridArea: `${linha} / 1` }}>
                <strong>{sala.nome}</strong>
                <span>{descricaoSala(sala)}</span>
              </div>,
              <div
                key={`f${sala.id}`}
                className={`agenda-faixa${ultima}`}
                style={{ gridArea: `${linha} / 2` }}
                role="group"
                aria-label={`Reservas da ${sala.nome}`}
              >
                {doDia.length ? (
                  doDia.map((r) => (
                    <BlocoReserva
                      key={r.id}
                      reserva={r}
                      oitoHoras={oitoHoras}
                      minha={ehMinha(r)}
                      selecionada={r.id === selecionadaId}
                      aoClicar={() => aoSelecionar(r.id)}
                    />
                  ))
                ) : (
                  <span className="visualmente-oculto">Livre o dia todo</span>
                )}
              </div>,
            ];
          })}
          {/* Linha "agora": só no dia de hoje, entre 8h e 20h, numa camada
              que cobre a coluna das horas de todas as salas. */}
          {mostrarAgora ? (
            <div className="agenda-camada-agora" style={{ gridRow: `2 / span ${salas.length}` }} aria-hidden="true">
              <div className="agenda-agora" style={{ "--pos": minutoAgora }} />
            </div>
          ) : null}
        </div>
      </div>
      <ul className="legenda" aria-label="Legenda">
        <li>
          <span className="amostra minha" aria-hidden="true" />
          Suas reservas
        </li>
        <li>
          <span className="amostra outra" aria-hidden="true" />
          Reservas de outras pessoas
        </li>
        {mostrarAgora ? (
          <li>
            <span className="amostra agora" aria-hidden="true" />
            Agora, {datas.hora(agora.toISOString())}
          </li>
        ) : null}
      </ul>
    </>
  );
}

function Detalhe({ reserva, minha, podeGerenciar, aoEditar, aoCancelar, aoFechar }) {
  const comecou = jaComecou(reserva);
  const podeAlterar = !comecou && (minha || podeGerenciar);
  return (
    <div className="detalhe-reserva" role="region" aria-labelledby="titulo-detalhe" aria-live="polite">
      <div>
        <h2 id="titulo-detalhe">{reserva.finalidade}</h2>
        <p>
          {reserva.sala.nome}, {quando(reserva)}, {periodo(reserva)}. Reservada por {minha ? "você" : reserva.usuario.nome}.
        </p>
        {comecou && (minha || podeGerenciar) ? <p>Esta reserva já começou e não pode mais ser alterada.</p> : null}
      </div>
      <div className="acoes">
        {podeAlterar ? (
          <>
            <button type="button" onClick={aoEditar}>
              Editar
            </button>
            <button type="button" className="perigo" onClick={aoCancelar}>
              Cancelar reserva
            </button>
          </>
        ) : null}
        <button type="button" className="botao-fantasma" onClick={aoFechar}>
          Fechar
        </button>
      </div>
    </div>
  );
}

export default function Agenda() {
  useTitulo("Agenda");
  const { usuario, tem } = useAuth();
  const [dia, setDia] = useState(datas.hojeEmSaoPaulo);
  const [selecionadaId, setSelecionadaId] = useState(null);
  const [editando, setEditando] = useState(null);
  const [aviso, setAviso] = useState(null);

  const { dados, carregando, erro, recarregar } = useCarregar(async () => {
    const { de, ate } = datas.janelaDoDia(dia);
    const [salas, reservas] = await Promise.all([
      api.get("/v1/salas", { ativas: true, limit: 100 }),
      api.get("/v1/reservas", { de, ate, status: "ativa", limit: 500 }),
    ]);
    return { salas, reservas };
  }, [dia]);

  // Polling: só consulta com a aba VISÍVEL (aba escondida não gasta
  // servidor) e atualiza na hora quando a pessoa volta para a aba.
  useEffect(() => {
    const atualizarSeVisivel = () => document.visibilityState === "visible" && recarregar();
    const intervalo = setInterval(atualizarSeVisivel, INTERVALO_ATUALIZACAO_MS);
    document.addEventListener("visibilitychange", atualizarSeVisivel);
    return () => {
      clearInterval(intervalo);
      document.removeEventListener("visibilitychange", atualizarSeVisivel);
    };
  }, [recarregar]);

  function irPara(novoDia) {
    if (!novoDia) return;
    setDia(novoDia);
    setSelecionadaId(null);
  }

  const ehMinha = (r) => r.usuario_id === usuario.id;
  const salas = dados?.salas ?? [];
  const reservas = (dados?.reservas ?? []).filter((r) => salas.some((s) => s.id === r.sala_id));
  const selecionada = reservas.find((r) => r.id === selecionadaId);

  async function cancelar(reserva) {
    try {
      if (!(await cancelarReserva(reserva))) return;
      setAviso({ texto: "Reserva cancelada. O horário ficou livre.", tipo: "sucesso" });
      setSelecionadaId(null);
    } catch (e) {
      setAviso({ texto: mensagemDeErro(e), tipo: "erro" });
    }
    recarregar();
  }

  return (
    <>
      <div className="agenda-topo">
        <div>
          <h1>Agenda</h1>
          <p>{datas.dataPorExtenso(dia)}</p>
        </div>
        <form className="agenda-controles" aria-label="Escolher data" onSubmit={(e) => e.preventDefault()}>
          <label htmlFor="dia" className="visualmente-oculto">
            Data
          </label>
          <input id="dia" type="date" required value={dia} onChange={(e) => irPara(e.target.value)} />
          <button type="button" onClick={() => irPara(datas.hojeEmSaoPaulo())}>
            Hoje
          </button>
          <Link className="botao primario" to={`/reservar?data=${dia}`}>
            Reservar sala
          </Link>
        </form>
      </div>

      <Aviso aviso={erro ? { texto: mensagemDeErro(erro), tipo: "erro" } : aviso} />

      {carregando && !dados ? <Carregando texto="Carregando a agenda…" /> : null}

      {dados && reservas.length === 0 ? (
        <div className="agenda-sem-reservas">
          <h2>Nenhuma reserva neste dia</h2>
          <p>Todas as salas estão livres. Escolha outra data ou reserve uma sala.</p>
          <Link className="botao primario" to={`/reservar?data=${dia}`}>
            Reservar sala
          </Link>
        </div>
      ) : null}

      {dados && reservas.length > 0 ? (
        <Grade
          dia={dia}
          salas={salas}
          reservas={reservas}
          ehMinha={ehMinha}
          selecionadaId={selecionadaId}
          aoSelecionar={(id) => setSelecionadaId((atual) => (atual === id ? null : id))}
        />
      ) : null}

      {selecionada ? (
        <Detalhe
          reserva={selecionada}
          minha={ehMinha(selecionada)}
          podeGerenciar={tem("responsavel")}
          aoEditar={() => setEditando(selecionada)}
          aoCancelar={() => cancelar(selecionada)}
          aoFechar={() => {
            setSelecionadaId(null);
            // Devolve o foco ao bloco da reserva (quem usa teclado não se perde).
            document.querySelector(`.bloco-reserva[data-id="${selecionada.id}"]`)?.focus();
          }}
        />
      ) : null}

      {editando ? (
        <DialogoEditarReserva
          reserva={editando}
          salas={salas}
          aoFechar={() => setEditando(null)}
          aoConcluir={(resultado) => {
            setEditando(null);
            setAviso(resultado);
            recarregar();
          }}
        />
      ) : null}
    </>
  );
}
