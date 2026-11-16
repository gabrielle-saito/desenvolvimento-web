// Catálogo de salas: busca por nome/localização, filtros (capacidade e
// recursos) e paginação. Os filtros ficam na URL (?busca=azul&pagina=2):
// o botão "voltar" funciona e o link pode ser compartilhado.

import { useEffect, useState } from "react";
import { useSearchParams } from "react-router";

import { api, mensagemDeErro } from "../api/cliente.js";
import Aviso from "../componentes/Aviso.jsx";
import Carregando from "../componentes/Carregando.jsx";
import CartaoSala from "../componentes/CartaoSala.jsx";
import Paginacao from "../componentes/Paginacao.jsx";
import SeletorRecursos from "../componentes/SeletorRecursos.jsx";
import { ITENS_POR_PAGINA } from "../config.js";
import { useCarregar, useTitulo } from "../util/useCarregar.js";

export default function Catalogo() {
  useTitulo("Salas");
  const [params, setParams] = useSearchParams();
  const busca = params.get("busca") ?? "";
  const capacidade = params.get("capacidade") ?? "";
  const recursosEscolhidos = params.getAll("recurso").map(Number);
  const pagina = Math.max(1, Number(params.get("pagina")) || 1);

  // O texto digitado vai para a URL 350 ms depois da última tecla (não
  // dispara uma busca por letra).
  const [textoBusca, setTextoBusca] = useState(busca);
  useEffect(() => {
    const espera = setTimeout(() => {
      if (textoBusca.trim() !== busca) mudarFiltros({ busca: textoBusca.trim() });
    }, 350);
    return () => clearTimeout(espera);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [textoBusca]);

  // Qualquer filtro novo volta para a página 1.
  function mudarFiltros(novos) {
    const atual = { busca, capacidade, recurso: recursosEscolhidos, pagina: 1, ...novos };
    const proximo = new URLSearchParams();
    if (atual.busca) proximo.set("busca", atual.busca);
    if (atual.capacidade) proximo.set("capacidade", atual.capacidade);
    for (const id of atual.recurso) proximo.append("recurso", id);
    if (atual.pagina > 1) proximo.set("pagina", atual.pagina);
    setParams(proximo, { replace: !("pagina" in novos) });
  }

  const recursos = useCarregar(() => api.get("/v1/recursos", { ativos: true, limit: 100 }), []);
  const salas = useCarregar(
    () =>
      api.pagina("/v1/salas", {
        ativas: true,
        busca: busca || undefined,
        capacidade_minima: capacidade || undefined,
        recurso: recursosEscolhidos,
        limit: ITENS_POR_PAGINA,
        offset: (pagina - 1) * ITENS_POR_PAGINA,
      }),
    [params.toString()],
  );

  const temFiltro = Boolean(busca || capacidade || recursosEscolhidos.length);
  const erro = salas.erro ?? recursos.erro;

  return (
    <>
      <h1>Salas</h1>
      <p className="discreto">Encontre a sala certa pelo nome, pelo tamanho ou pelos equipamentos.</p>

      <form className="cartao filtros-catalogo" role="search" aria-label="Filtrar salas" onSubmit={(e) => e.preventDefault()}>
        <div className="linha">
          <div>
            <label htmlFor="busca">Buscar</label>
            <input
              id="busca"
              type="search"
              placeholder="Nome ou andar. Ex.: azul, térreo"
              maxLength={100}
              value={textoBusca}
              onChange={(e) => setTextoBusca(e.target.value)}
            />
          </div>
          <div>
            <label htmlFor="capacidade">Pessoas (mínimo)</label>
            <input
              id="capacidade"
              type="number"
              min={1}
              inputMode="numeric"
              value={capacidade}
              onChange={(e) => mudarFiltros({ capacidade: e.target.value })}
            />
          </div>
        </div>
        {recursos.dados ? (
          <SeletorRecursos
            id="filtro-recursos"
            legenda="Precisa ter"
            recursos={recursos.dados}
            selecionados={recursosEscolhidos}
            aoMudar={(ids) => mudarFiltros({ recurso: ids })}
          />
        ) : null}
        {temFiltro ? (
          <div className="acoes">
            <button
              type="button"
              className="botao-fantasma"
              onClick={() => {
                setTextoBusca("");
                setParams(new URLSearchParams());
              }}
            >
              Limpar filtros
            </button>
          </div>
        ) : null}
      </form>

      <Aviso aviso={erro ? { texto: mensagemDeErro(erro), tipo: "erro" } : null} />

      {salas.carregando && !salas.dados ? <Carregando texto="Carregando salas…" /> : null}

      {salas.dados ? (
        <section aria-labelledby="titulo-resultado" aria-busy={salas.carregando}>
          <h2 id="titulo-resultado" className="visualmente-oculto">
            Resultado
          </h2>
          <p className="discreto" role="status">
            {salas.dados.total === 0
              ? ""
              : `${salas.dados.total} ${salas.dados.total === 1 ? "sala encontrada" : "salas encontradas"}`}
          </p>
          {salas.dados.total === 0 ? (
            <div className="agenda-sem-reservas">
              <h2>Nenhuma sala encontrada</h2>
              <p>{temFiltro ? "Tente buscar outro nome ou tirar algum filtro." : "Ainda não há salas cadastradas."}</p>
            </div>
          ) : (
            <div className="grade-salas">
              {salas.dados.itens.map((sala) => (
                <CartaoSala key={sala.id} sala={sala} />
              ))}
            </div>
          )}
          <Paginacao
            pagina={pagina}
            total={salas.dados.total}
            porPagina={ITENS_POR_PAGINA}
            aoMudar={(p) => {
              mudarFiltros({ pagina: p });
              window.scrollTo({ top: 0 });
            }}
            rotulo="Páginas de salas"
          />
        </section>
      ) : null}
    </>
  );
}
