// Área do responsável (caso de uso 8): qualquer reserva, editar/cancelar.
// A API também confere o papel: um colaborador que abrir esta tela vê
// "acesso negado" aqui e recebe 403 se tentar alterar algo.

import { useState } from "react";

import { api, mensagemDeErro } from "../api/cliente.js";
import Aviso from "../componentes/Aviso.jsx";
import Campo from "../componentes/Campo.jsx";
import Carregando from "../componentes/Carregando.jsx";
import Paginacao from "../componentes/Paginacao.jsx";
import TabelaReservas from "../componentes/TabelaReservas.jsx";
import { useAcoesReserva } from "../componentes/useAcoesReserva.jsx";
import { ITENS_POR_PAGINA } from "../config.js";
import * as datas from "../util/datas.js";
import { useCarregar, useTitulo } from "../util/useCarregar.js";

function filtrosIniciais() {
  const hoje = datas.hojeEmSaoPaulo();
  return { de: hoje, ate: datas.somarDias(hoje, 7), sala_id: "", busca: "" };
}

export default function GerenciarReservas() {
  useTitulo("Gerenciar reservas");
  // "rascunho" = o que está no formulário; "filtros" = o que foi aplicado.
  const [rascunho, setRascunho] = useState(filtrosIniciais);
  const [filtros, setFiltros] = useState(rascunho);
  const [pagina, setPagina] = useState(1);
  const [erros, setErros] = useState({});

  const salas = useCarregar(() => api.get("/v1/salas", { limit: 100 }), []);
  const reservas = useCarregar(
    () =>
      api.pagina("/v1/reservas", {
        de: datas.isoSaoPaulo(filtros.de, "00:00"),
        ate: datas.isoSaoPaulo(datas.somarDias(filtros.ate, 1), "00:00"),
        sala_id: filtros.sala_id,
        busca: filtros.busca.trim() || undefined,
        status: "ativa",
        limit: ITENS_POR_PAGINA,
        offset: (pagina - 1) * ITENS_POR_PAGINA,
      }),
    [filtros, pagina],
  );
  const acoes = useAcoesReserva(reservas.recarregar);

  const mudar = (evento) => setRascunho((r) => ({ ...r, [evento.target.name]: evento.target.value }));

  function aplicar(evento) {
    evento.preventDefault();
    const e = {};
    if (!rascunho.de) e.de = "Escolha a data inicial.";
    if (!rascunho.ate) e.ate = "Escolha a data final.";
    if (rascunho.de && rascunho.ate && rascunho.ate < rascunho.de) e.ate = "A data final vem antes da inicial.";
    setErros(e);
    if (Object.keys(e).length) return;
    acoes.setAviso(null);
    setPagina(1);
    setFiltros({ ...rascunho });
  }

  const erro = reservas.erro ?? salas.erro;
  return (
    <>
      <h1>Gerenciar reservas</h1>
      <p className="discreto">Área do responsável pelas salas: consulte, altere ou cancele qualquer reserva.</p>
      <form className="filtros" onSubmit={aplicar} noValidate aria-label="Filtrar reservas">
        <Campo id="de" rotulo="De" type="date" name="de" value={rascunho.de} onChange={mudar} erro={erros.de} required />
        <Campo id="ate" rotulo="Até (inclusive)" type="date" name="ate" value={rascunho.ate} onChange={mudar} erro={erros.ate} required />
        <Campo id="sala" rotulo="Sala" como="select" name="sala_id" value={rascunho.sala_id} onChange={mudar}>
          <option value="">Todas</option>
          {(salas.dados ?? []).map((s) => (
            <option key={s.id} value={s.id}>
              {s.nome}
            </option>
          ))}
        </Campo>
        <Campo id="busca" rotulo="Finalidade" type="search" name="busca" placeholder="Ex.: daily" maxLength={100} value={rascunho.busca} onChange={mudar} />
        <div className="acoes">
          <button type="submit" className="primario">
            Filtrar
          </button>
        </div>
      </form>

      <Aviso aviso={erro ? { texto: mensagemDeErro(erro), tipo: "erro" } : acoes.aviso} />

      {reservas.carregando && !reservas.dados ? <Carregando texto="Carregando reservas…" /> : null}
      {reservas.dados?.total === 0 ? <p className="vazio">Não há reservas para o período.</p> : null}
      {reservas.dados?.total > 0 ? (
        <div aria-busy={reservas.carregando}>
          <p className="discreto" role="status">
            {reservas.dados.total} {reservas.dados.total === 1 ? "reserva" : "reservas"}
          </p>
          <TabelaReservas reservas={reservas.dados.itens} mostrarDono aoEditar={acoes.editar} aoCancelar={acoes.cancelar} />
          <Paginacao pagina={pagina} total={reservas.dados.total} porPagina={ITENS_POR_PAGINA} aoMudar={setPagina} rotulo="Páginas de reservas" />
        </div>
      ) : null}

      {acoes.dialogo(salas.dados ?? [])}
    </>
  );
}
