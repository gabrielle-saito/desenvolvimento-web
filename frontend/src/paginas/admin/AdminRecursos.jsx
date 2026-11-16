// Recursos das salas (projetor, TV...): cadastrar, editar, desativar.
// Recurso desativado some das opções para salas, mas as salas que já o
// têm continuam com ele.

import { useState } from "react";

import { api, errosPorCampo, mensagemDeErro } from "../../api/cliente.js";
import Aviso from "../../componentes/Aviso.jsx";
import Campo from "../../componentes/Campo.jsx";
import Carregando from "../../componentes/Carregando.jsx";
import { CampoBusca, SeletorSituacao } from "../../componentes/FiltroLista.jsx";
import Janela from "../../componentes/Janela.jsx";
import Paginacao from "../../componentes/Paginacao.jsx";
import { ITENS_POR_PAGINA } from "../../config.js";
import { useCarregar } from "../../util/useCarregar.js";

function FormRecurso({ idBase, inicial, rotuloBotao, aoEnviar, aoCancelar, erros }) {
  const [nome, setNome] = useState(inicial?.nome ?? "");
  const [descricao, setDescricao] = useState(inicial?.descricao ?? "");
  const [erroNome, setErroNome] = useState(null);
  const [enviando, setEnviando] = useState(false);

  async function enviar(evento) {
    evento.preventDefault();
    if (!nome.trim()) {
      setErroNome("Informe o nome.");
      return;
    }
    setErroNome(null);
    setEnviando(true);
    const ok = await aoEnviar({ nome: nome.trim(), descricao: descricao.trim() || null });
    setEnviando(false);
    if (ok && !inicial) {
      setNome("");
      setDescricao("");
    }
  }

  return (
    <form onSubmit={enviar} noValidate>
      <div className="linha">
        <Campo id={`${idBase}-nome`} rotulo="Nome" maxLength={80} value={nome} onChange={(e) => setNome(e.target.value)} erro={erroNome ?? erros.nome} required />
        <Campo id={`${idBase}-descricao`} rotulo="Descrição" maxLength={2000} value={descricao} onChange={(e) => setDescricao(e.target.value)} erro={erros.descricao} />
      </div>
      <div className="acoes">
        <button type="submit" className="primario" disabled={enviando}>
          {enviando ? "Salvando…" : rotuloBotao}
        </button>
        {aoCancelar ? (
          <button type="button" onClick={aoCancelar}>
            Cancelar
          </button>
        ) : null}
      </div>
    </form>
  );
}

export default function AdminRecursos() {
  const [busca, setBusca] = useState("");
  const [situacao, setSituacao] = useState("");
  const [pagina, setPagina] = useState(1);
  const [aviso, setAviso] = useState(null);
  const [errosCriar, setErrosCriar] = useState({});
  const [editando, setEditando] = useState(null);
  const [errosEditar, setErrosEditar] = useState({});

  const recursos = useCarregar(
    () =>
      api.pagina("/v1/recursos", {
        busca: busca || undefined,
        ativos: situacao,
        limit: ITENS_POR_PAGINA,
        offset: (pagina - 1) * ITENS_POR_PAGINA,
      }),
    [busca, situacao, pagina],
  );

  async function criar(corpo) {
    try {
      await api.post("/v1/recursos", corpo);
      setErrosCriar({});
      setAviso({ texto: `Recurso "${corpo.nome}" cadastrado.`, tipo: "sucesso" });
      recursos.recarregar();
      return true;
    } catch (erro) {
      setErrosCriar(errosPorCampo(erro));
      setAviso({ texto: mensagemDeErro(erro), tipo: "erro" });
      return false;
    }
  }

  async function salvarEdicao(corpo) {
    try {
      await api.patch(`/v1/recursos/${editando.id}`, corpo);
      setAviso({ texto: `Recurso "${corpo.nome}" atualizado.`, tipo: "sucesso" });
      setEditando(null);
      recursos.recarregar();
      return true;
    } catch (erro) {
      setErrosEditar(errosPorCampo(erro));
      setAviso({ texto: mensagemDeErro(erro), tipo: "erro" });
      return false;
    }
  }

  async function alternarAtivo(recurso) {
    if (recurso.ativo && !window.confirm(`Desativar "${recurso.nome}"? Ele deixa de aparecer como opção para as salas; as que já o têm continuam com ele.`)) return;
    try {
      // Desativar = DELETE (soft delete na API, responde 204).
      // Reativar = PATCH {ativo: true}.
      if (recurso.ativo) await api.delete(`/v1/recursos/${recurso.id}`);
      else await api.patch(`/v1/recursos/${recurso.id}`, { ativo: true });
      setAviso({ texto: `Recurso "${recurso.nome}" ${recurso.ativo ? "desativado" : "reativado"}.`, tipo: "sucesso" });
    } catch (erro) {
      setAviso({ texto: mensagemDeErro(erro), tipo: "erro" });
    }
    recursos.recarregar();
  }

  return (
    <section aria-labelledby="titulo-recursos">
      <h2 id="titulo-recursos" className="visualmente-oculto">
        Recursos
      </h2>
      <Aviso aviso={recursos.erro ? { texto: mensagemDeErro(recursos.erro), tipo: "erro" } : aviso} />

      <div className="cartao">
        <h3>Cadastrar recurso</h3>
        <FormRecurso idBase="novo-recurso" rotuloBotao="Cadastrar recurso" aoEnviar={criar} erros={errosCriar} />
      </div>

      <div className="filtros">
        <CampoBusca id="busca-recursos" rotulo="Buscar recurso" placeholder="Ex.: projetor" aoBuscar={(t) => (setBusca(t), setPagina(1))} />
        <SeletorSituacao id="situacao-recursos" valor={situacao} aoMudar={(v) => (setSituacao(v), setPagina(1))} rotulos={["Todos", "Ativos", "Inativos"]} />
      </div>

      {recursos.carregando && !recursos.dados ? <Carregando texto="Carregando recursos…" /> : null}
      {recursos.dados?.total === 0 ? <p className="vazio">{busca || situacao ? "Nenhum recurso com esses filtros." : "Nenhum recurso cadastrado."}</p> : null}
      {recursos.dados?.total > 0 ? (
        <div aria-busy={recursos.carregando}>
          <div className="tabela-rolavel">
            <table>
              <thead>
                <tr>
                  <th scope="col">Nome</th>
                  <th scope="col">Descrição</th>
                  <th scope="col">Situação</th>
                  <th scope="col">
                    <span className="visualmente-oculto">Ações</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {recursos.dados.itens.map((r) => (
                  <tr key={r.id} className={r.ativo ? "" : "inativo"}>
                    <td>{r.nome}</td>
                    <td>{r.descricao ?? "—"}</td>
                    <td>
                      <span className="etiqueta">{r.ativo ? "Ativo" : "Desativado"}</span>
                    </td>
                    <td className="acoes">
                      <button type="button" onClick={() => (setErrosEditar({}), setEditando(r))} aria-label={`Editar ${r.nome}`}>
                        Editar
                      </button>
                      <button type="button" className={r.ativo ? "perigo" : ""} onClick={() => alternarAtivo(r)} aria-label={`${r.ativo ? "Desativar" : "Reativar"} ${r.nome}`}>
                        {r.ativo ? "Desativar" : "Reativar"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Paginacao pagina={pagina} total={recursos.dados.total} porPagina={ITENS_POR_PAGINA} aoMudar={setPagina} rotulo="Páginas de recursos" />
        </div>
      ) : null}

      {editando ? (
        <Janela titulo={`Editar ${editando.nome}`} aoFechar={() => setEditando(null)}>
          <FormRecurso
            idBase="editar-recurso"
            inicial={editando}
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
