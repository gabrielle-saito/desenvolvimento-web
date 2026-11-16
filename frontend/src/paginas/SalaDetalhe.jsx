// Detalhe de uma sala (/salas/:id): dados completos, recursos e os horários
// ocupados no dia escolhido, com o botão para reservar. É o equivalente da
// "página de detalhe do produto" do roteiro.

import { useState } from "react";
import { Link, useParams } from "react-router";

import { api, mensagemDeErro } from "../api/cliente.js";
import Aviso from "../componentes/Aviso.jsx";
import Carregando from "../componentes/Carregando.jsx";
import EtiquetasRecursos from "../componentes/EtiquetasRecursos.jsx";
import { useAuth } from "../contexto/AuthContext.jsx";
import * as datas from "../util/datas.js";
import { AVISO_PRIVACIDADE, periodo, titulo } from "../util/reservas.js";
import { useCarregar, useTitulo } from "../util/useCarregar.js";

function Ocupacao({ reservas, usuarioId }) {
  if (!reservas.length) return <p className="livre">Livre o dia todo.</p>;
  const temOcultas = reservas.some((r) => r.detalhes_ocultos);
  return (
    <>
      <ul className="horarios" aria-label="Horários ocupados">
        {reservas.map((r) => {
          const minha = r.usuario_id === usuarioId;
          return (
            <li key={r.id}>
              <strong>{periodo(r)}</strong> · {titulo(r)}
              {minha ? " (sua reserva)" : r.detalhes_ocultos ? "" : ` · ${r.usuario.nome}`}
            </li>
          );
        })}
      </ul>
      {temOcultas ? <p className="discreto">{AVISO_PRIVACIDADE}</p> : null}
    </>
  );
}

export default function SalaDetalhe() {
  const { id } = useParams();
  const { usuario } = useAuth();
  const [dia, setDia] = useState(datas.hojeEmSaoPaulo);

  const sala = useCarregar(() => api.get(`/v1/salas/${id}`), [id]);
  const reservas = useCarregar(() => {
    const { de, ate } = datas.janelaDoDia(dia);
    return api.get("/v1/reservas", { sala_id: id, de, ate, status: "ativa", limit: 100 });
  }, [id, dia]);

  useTitulo(sala.dados?.nome ?? "Sala");

  if (sala.erro?.status === 404 || sala.erro?.status === 422) {
    return (
      <div className="agenda-sem-reservas">
        <h1>Sala não encontrada</h1>
        <p>O endereço pode estar errado ou a sala pode ter sido removida do catálogo.</p>
        <Link className="botao primario" to="/salas">
          Ver todas as salas
        </Link>
      </div>
    );
  }
  if (sala.erro) return <Aviso aviso={{ texto: mensagemDeErro(sala.erro), tipo: "erro" }} />;
  if (!sala.dados) return <Carregando texto="Carregando a sala…" />;

  const s = sala.dados;
  return (
    <>
      <p>
        <Link to="/salas">← Voltar para as salas</Link>
      </p>

      <article className="cartao sala detalhe-sala" aria-labelledby="nome-sala">
        <h1 id="nome-sala">{s.nome}</h1>
        {s.ativa ? null : (
          <p className="ocupada">Sala desativada: não recebe reservas novas.</p>
        )}
        <dl className="dados-sala">
          <div>
            <dt>Capacidade</dt>
            <dd>
              {s.capacidade} {s.capacidade === 1 ? "pessoa" : "pessoas"}
            </dd>
          </div>
          <div>
            <dt>Localização</dt>
            <dd>{s.localizacao || "Não informada"}</dd>
          </div>
          {s.descricao ? (
            <div>
              <dt>Descrição</dt>
              <dd>{s.descricao}</dd>
            </div>
          ) : null}
        </dl>
        <h2 className="subtitulo">Recursos</h2>
        <EtiquetasRecursos recursos={s.recursos} />
      </article>

      <section className="cartao" aria-labelledby="titulo-ocupacao">
        <div className="agenda-topo">
          <div>
            <h2 id="titulo-ocupacao">Ocupação</h2>
            <p>{datas.dataPorExtenso(dia)}</p>
          </div>
          <form className="agenda-controles" aria-label="Escolher data" onSubmit={(e) => e.preventDefault()}>
            <label htmlFor="dia-sala" className="visualmente-oculto">
              Data
            </label>
            <input id="dia-sala" type="date" required value={dia} onChange={(e) => e.target.value && setDia(e.target.value)} />
            <button type="button" onClick={() => setDia(datas.hojeEmSaoPaulo())}>
              Hoje
            </button>
          </form>
        </div>

        {reservas.erro ? <Aviso aviso={{ texto: mensagemDeErro(reservas.erro), tipo: "erro" }} /> : null}
        {reservas.carregando && !reservas.dados ? <Carregando texto="Carregando os horários…" /> : null}
        {reservas.dados ? <Ocupacao reservas={reservas.dados} usuarioId={usuario.id} /> : null}

        {s.ativa ? (
          <div className="acoes">
            <Link className="botao primario" to={`/reservar?sala=${s.id}&data=${dia}`}>
              Reservar {s.nome}
            </Link>
          </div>
        ) : null}
      </section>
    </>
  );
}
