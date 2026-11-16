import { Link } from "react-router";

import EtiquetasRecursos from "./EtiquetasRecursos.jsx";

// Cartão de uma sala no catálogo. O nome leva à página de detalhe.
export default function CartaoSala({ sala }) {
  return (
    <article className="cartao sala cartao-catalogo">
      <h2>
        <Link to={`/salas/${sala.id}`}>{sala.nome}</Link>
      </h2>
      <p className="discreto">
        {sala.capacidade} {sala.capacidade === 1 ? "pessoa" : "pessoas"}
        {sala.localizacao ? ` · ${sala.localizacao}` : ""}
      </p>
      {sala.descricao ? <p>{sala.descricao}</p> : null}
      <EtiquetasRecursos recursos={sala.recursos} />
      <div className="acoes">
        <Link className="botao" to={`/salas/${sala.id}`} aria-label={`Ver detalhes e horários da ${sala.nome}`}>
          Detalhes
        </Link>
        <Link className="botao" to={`/reservar?sala=${sala.id}`} aria-label={`Reservar ${sala.nome}`}>
          Reservar esta sala
        </Link>
      </div>
    </article>
  );
}
