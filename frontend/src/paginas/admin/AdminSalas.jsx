// Salas (caso de uso 6): cadastrar, listar com busca e paginação, editar
// (inclusive os recursos) e desativar/reativar. Não há "apagar": sala com
// reservas antigas é desativada (soft delete).

import { useState } from "react";

import { api, errosPorCampo, mensagemDeErro } from "../../api/cliente.js";
import Aviso from "../../componentes/Aviso.jsx";
import Carregando from "../../componentes/Carregando.jsx";
import { CampoBusca, SeletorSituacao } from "../../componentes/FiltroLista.jsx";
import FormSala from "../../componentes/FormSala.jsx";
import Janela from "../../componentes/Janela.jsx";
import Paginacao from "../../componentes/Paginacao.jsx";
import { ITENS_POR_PAGINA } from "../../config.js";
import { useCarregar } from "../../util/useCarregar.js";

export default function AdminSalas() {
  const [busca, setBusca] = useState("");
  const [situacao, setSituacao] = useState("");
  const [pagina, setPagina] = useState(1);
  const [aviso, setAviso] = useState(null);
  const [errosCriar, setErrosCriar] = useState({});
  const [editando, setEditando] = useState(null);
  const [errosEditar, setErrosEditar] = useState({});

  const recursos = useCarregar(() => api.get("/v1/recursos", { limit: 100 }), []);
  const salas = useCarregar(
    () =>
      api.pagina("/v1/salas", {
        busca: busca || undefined,
        ativas: situacao,
        limit: ITENS_POR_PAGINA,
        offset: (pagina - 1) * ITENS_POR_PAGINA,
      }),
    [busca, situacao, pagina],
  );

  async function criar(corpo) {
    try {
      await api.post("/v1/salas", corpo);
      setErrosCriar({});
      setAviso({ texto: `Sala "${corpo.nome}" cadastrada.`, tipo: "sucesso" });
      salas.recarregar();
      return true;
    } catch (erro) {
      setErrosCriar(errosPorCampo(erro));
      setAviso({ texto: mensagemDeErro(erro), tipo: "erro" });
      return false;
    }
  }

  async function salvarEdicao(corpo) {
    try {
      await api.patch(`/v1/salas/${editando.id}`, corpo);
      setAviso({ texto: `Sala "${corpo.nome}" atualizada.`, tipo: "sucesso" });
      setEditando(null);
      salas.recarregar();
      return true;
    } catch (erro) {
      setErrosEditar(errosPorCampo(erro));
      setAviso({ texto: mensagemDeErro(erro), tipo: "erro" });
      return false;
    }
  }

  async function alternarAtiva(sala) {
    if (sala.ativa && !window.confirm(`Desativar a ${sala.nome}? Ela deixa de receber reservas novas; as reservas existentes continuam valendo.`)) return;
    try {
      await api.patch(`/v1/salas/${sala.id}`, { ativa: !sala.ativa });
      setAviso({ texto: `Sala "${sala.nome}" ${sala.ativa ? "desativada" : "reativada"}.`, tipo: "sucesso" });
    } catch (erro) {
      setAviso({ texto: mensagemDeErro(erro), tipo: "erro" });
    }
    salas.recarregar();
  }

  const erro = salas.erro ?? recursos.erro;
  return (
    <section aria-labelledby="titulo-salas">
      <h2 id="titulo-salas" className="visualmente-oculto">
        Salas
      </h2>
      <Aviso aviso={erro ? { texto: mensagemDeErro(erro), tipo: "erro" } : aviso} />

      <div className="cartao">
        <h3>Cadastrar sala</h3>
        {recursos.dados ? (
          <FormSala idBase="nova-sala" recursos={recursos.dados} rotuloBotao="Cadastrar sala" aoEnviar={criar} erros={errosCriar} />
        ) : (
          <Carregando />
        )}
      </div>

      <div className="filtros">
        <CampoBusca id="busca-salas" rotulo="Buscar sala" placeholder="Nome ou andar" aoBuscar={(t) => (setBusca(t), setPagina(1))} />
        <SeletorSituacao id="situacao-salas" valor={situacao} aoMudar={(v) => (setSituacao(v), setPagina(1))} />
      </div>

      {salas.carregando && !salas.dados ? <Carregando texto="Carregando salas…" /> : null}
      {salas.dados?.total === 0 ? <p className="vazio">{busca || situacao ? "Nenhuma sala com esses filtros." : "Nenhuma sala cadastrada."}</p> : null}
      {salas.dados?.total > 0 ? (
        <div aria-busy={salas.carregando}>
          <div className="tabela-rolavel">
            <table>
              <thead>
                <tr>
                  <th scope="col">Nome</th>
                  <th scope="col">Capacidade</th>
                  <th scope="col">Localização</th>
                  <th scope="col">Recursos</th>
                  <th scope="col">Situação</th>
                  <th scope="col">
                    <span className="visualmente-oculto">Ações</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {salas.dados.itens.map((sala) => (
                  <tr key={sala.id} className={sala.ativa ? "" : "inativo"}>
                    <td>{sala.nome}</td>
                    <td>{sala.capacidade}</td>
                    <td>{sala.localizacao ?? "—"}</td>
                    <td>{sala.recursos.map((r) => r.nome).join(", ") || "—"}</td>
                    <td>
                      <span className="etiqueta">{sala.ativa ? "Ativa" : "Desativada"}</span>
                    </td>
                    <td className="acoes">
                      <button type="button" onClick={() => (setErrosEditar({}), setEditando(sala))} aria-label={`Editar ${sala.nome}`}>
                        Editar
                      </button>
                      <button type="button" className={sala.ativa ? "perigo" : ""} onClick={() => alternarAtiva(sala)} aria-label={`${sala.ativa ? "Desativar" : "Reativar"} ${sala.nome}`}>
                        {sala.ativa ? "Desativar" : "Reativar"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Paginacao pagina={pagina} total={salas.dados.total} porPagina={ITENS_POR_PAGINA} aoMudar={setPagina} rotulo="Páginas de salas" />
        </div>
      ) : null}

      {editando ? (
        <Janela titulo={`Editar ${editando.nome}`} aoFechar={() => setEditando(null)}>
          <FormSala
            idBase="editar-sala"
            inicial={editando}
            recursos={recursos.dados ?? []}
            rotuloBotao="Salvar"
            aoEnviar={salvarEdicao}
            aoCancelar={() => setEditando(null)}
            erros={errosEditar}
          />
        </Janela>
      ) : null}
    </section>
  );
}
