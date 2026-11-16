import { Link } from "react-router";

import EtiquetasRecursos from "./EtiquetasRecursos.jsx";

// Cartão de uma sala no catálogo.
export default function CartaoSala({ sala }) {
  return (
    <article className="cartao sala cartao-catalogo">
      <h2>{sala.nome}</h2>
      <p className="discreto">
        {sala.capacidade} {sala.capacidade === 1 ? "pessoa" : "pessoas"}
        {sala.localizacao ? ` · ${sala.localizacao}` : ""}
      </p>
      {sala.descricao ? <p>{sala.descricao}</p> : null}
      <EtiquetasRecursos recursos={sala.recursos} />
      <div className="acoes">
        <Link className="botao" to={`/reservar?sala=${sala.id}`} aria-label={`Reservar ${sala.nome}`}>
          Reservar esta sala
        </Link>
      </div>
    </article>
  );
}
