import { useState } from "react";
import { Link } from "react-router";

import { api, mensagemDeErro } from "../api/cliente.js";
import Aviso from "../componentes/Aviso.jsx";
import Carregando from "../componentes/Carregando.jsx";
import Paginacao from "../componentes/Paginacao.jsx";
import TabelaReservas from "../componentes/TabelaReservas.jsx";
import { useAcoesReserva } from "../componentes/useAcoesReserva.jsx";
import { ITENS_POR_PAGINA } from "../config.js";
import { useCarregar, useTitulo } from "../util/useCarregar.js";

// Só as reservas da própria pessoa ("minhas=true"): o colaborador vê e
// altera apenas os próprios dados.
export default function MinhasReservas() {
  useTitulo("Minhas reservas");
  const [pagina, setPagina] = useState(1);
  // "Agora" fixo ao abrir a tela: a paginação não muda de lugar sozinha.
  const [desde] = useState(() => new Date().toISOString());

  const salas = useCarregar(() => api.get("/v1/salas", { limit: 100 }), []);
  const reservas = useCarregar(
    () =>
      api.pagina("/v1/reservas", {
        minhas: true,
        status: "ativa",
        de: desde,
        limit: ITENS_POR_PAGINA,
        offset: (pagina - 1) * ITENS_POR_PAGINA,
      }),
    [pagina],
  );
  const acoes = useAcoesReserva(reservas.recarregar);
  const erro = reservas.erro ?? salas.erro;

  return (
    <>
      <h1>Minhas reservas</h1>
      <p className="discreto">Suas reservas ativas de hoje em diante. Reservas que já começaram não podem ser alteradas.</p>
      <Aviso aviso={erro ? { texto: mensagemDeErro(erro), tipo: "erro" } : acoes.aviso} />

      {reservas.carregando && !reservas.dados ? <Carregando texto="Carregando suas reservas…" /> : null}

      {reservas.dados?.total === 0 ? (
        <div className="agenda-sem-reservas">
          <h2>Você não tem reservas futuras</h2>
          <p>Quando reservar uma sala, ela aparece aqui.</p>
          <Link className="botao primario" to="/reservar">
            Reservar sala
          </Link>
        </div>
      ) : null}

      {reservas.dados?.total > 0 ? (
        <div aria-busy={reservas.carregando}>
          <TabelaReservas reservas={reservas.dados.itens} aoEditar={acoes.editar} aoCancelar={acoes.cancelar} />
          <Paginacao
            pagina={pagina}
            total={reservas.dados.total}
            porPagina={ITENS_POR_PAGINA}
            aoMudar={setPagina}
            rotulo="Páginas das suas reservas"
          />
        </div>
      ) : null}

      {acoes.dialogo(salas.dados ?? [])}
    </>
  );
}
