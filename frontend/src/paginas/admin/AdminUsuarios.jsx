// Usuários (caso de uso 7): cadastrar com qualquer papel, mudar o papel e
// desativar/reativar. Busca por nome/e-mail, filtro por papel e paginação.

import { useState } from "react";

import { api, errosPorCampo, mensagemDeErro } from "../../api/cliente.js";
import Aviso from "../../componentes/Aviso.jsx";
import Campo from "../../componentes/Campo.jsx";
import Carregando from "../../componentes/Carregando.jsx";
import { CampoBusca } from "../../componentes/FiltroLista.jsx";
import Paginacao from "../../componentes/Paginacao.jsx";
import { ITENS_POR_PAGINA } from "../../config.js";
import { useAuth } from "../../contexto/AuthContext.jsx";
import { useCarregar } from "../../util/useCarregar.js";

const PAPEIS = [
  ["colaborador", "Colaborador"],
  ["responsavel", "Responsável"],
  ["admin", "Admin"],
];
const VAZIO = { nome: "", email: "", senha: "", papel: "colaborador" };

function FormUsuario({ aoCriar }) {
  const [campos, setCampos] = useState(VAZIO);
  const [erros, setErros] = useState({});
  const [enviando, setEnviando] = useState(false);
  const mudar = (evento) => setCampos((c) => ({ ...c, [evento.target.name]: evento.target.value }));

  async function enviar(evento) {
    evento.preventDefault();
    const e = {};
    if (!campos.nome.trim()) e.nome = "Informe o nome.";
    if (!campos.email.trim()) e.email = "Informe o e-mail.";
    if (campos.senha.length < 8) e.senha = "A senha precisa ter pelo menos 8 caracteres.";
    setErros(e);
    if (Object.keys(e).length) return;
    setEnviando(true);
    const errosApi = await aoCriar({ ...campos, nome: campos.nome.trim(), email: campos.email.trim() });
    setEnviando(false);
    if (errosApi) setErros(errosApi);
    else setCampos(VAZIO);
  }

  return (
    <form onSubmit={enviar} noValidate>
      <div className="linha">
        <Campo id="usuario-nome" rotulo="Nome" name="nome" maxLength={120} value={campos.nome} onChange={mudar} erro={erros.nome} required />
        <Campo id="usuario-email" rotulo="E-mail" name="email" type="email" autoComplete="off" value={campos.email} onChange={mudar} erro={erros.email} required />
        <Campo id="usuario-senha" rotulo="Senha inicial" name="senha" type="password" autoComplete="new-password" maxLength={128} value={campos.senha} onChange={mudar} erro={erros.senha} required />
        <Campo id="usuario-papel" rotulo="Papel" como="select" name="papel" value={campos.papel} onChange={mudar} erro={erros.papel}>
          {PAPEIS.map(([valor, rotulo]) => (
            <option key={valor} value={valor}>
              {rotulo}
            </option>
          ))}
        </Campo>
      </div>
      <div className="acoes">
        <button type="submit" className="primario" disabled={enviando}>
          {enviando ? "Salvando…" : "Cadastrar usuário"}
        </button>
      </div>
    </form>
  );
}

export default function AdminUsuarios() {
  const { usuario: logado } = useAuth();
  const [busca, setBusca] = useState("");
  const [papel, setPapel] = useState("");
  const [pagina, setPagina] = useState(1);
  const [aviso, setAviso] = useState(null);

  const usuarios = useCarregar(
    () =>
      api.pagina("/v1/usuarios", {
        busca: busca || undefined,
        papel,
        limit: ITENS_POR_PAGINA,
        offset: (pagina - 1) * ITENS_POR_PAGINA,
      }),
    [busca, papel, pagina],
  );

  // Devolve null se deu certo, ou os erros por campo.
  async function criar(corpo) {
    try {
      await api.post("/v1/usuarios", corpo);
      setAviso({ texto: `Usuário ${corpo.email} cadastrado.`, tipo: "sucesso" });
      usuarios.recarregar();
      return null;
    } catch (erro) {
      setAviso({ texto: erro.status === 409 ? "Este e-mail já está cadastrado." : mensagemDeErro(erro), tipo: "erro" });
      return errosPorCampo(erro);
    }
  }

  async function alterar(u, corpo, sucesso) {
    try {
      await api.patch(`/v1/usuarios/${u.id}`, corpo);
      setAviso({ texto: sucesso, tipo: "sucesso" });
    } catch (erro) {
      setAviso({ texto: mensagemDeErro(erro), tipo: "erro" });
    }
    usuarios.recarregar();
  }

  function alternarAtivo(u) {
    if (u.is_active && !window.confirm(`Desativar ${u.nome}? A pessoa não conseguirá mais entrar.`)) return;
    alterar(u, { is_active: !u.is_active }, `${u.nome} ${u.is_active ? "desativado(a)" : "reativado(a)"}.`);
  }

  return (
    <section aria-labelledby="titulo-usuarios">
      <h2 id="titulo-usuarios" className="visualmente-oculto">
        Usuários
      </h2>
      <Aviso aviso={usuarios.erro ? { texto: mensagemDeErro(usuarios.erro), tipo: "erro" } : aviso} />

      <div className="cartao">
        <h3>Cadastrar usuário</h3>
        <FormUsuario aoCriar={criar} />
      </div>

      <div className="filtros">
        <CampoBusca id="busca-usuarios" rotulo="Buscar pessoa" placeholder="Nome ou e-mail" aoBuscar={(t) => (setBusca(t), setPagina(1))} />
        <div>
          <label htmlFor="filtro-papel">Papel</label>
          <select id="filtro-papel" value={papel} onChange={(e) => (setPapel(e.target.value), setPagina(1))}>
            <option value="">Todos</option>
            {PAPEIS.map(([valor, rotulo]) => (
              <option key={valor} value={valor}>
                {rotulo}
              </option>
            ))}
          </select>
        </div>
      </div>

      {usuarios.carregando && !usuarios.dados ? <Carregando texto="Carregando usuários…" /> : null}
      {usuarios.dados?.total === 0 ? <p className="vazio">Ninguém encontrado com esses filtros.</p> : null}
      {usuarios.dados?.total > 0 ? (
        <div aria-busy={usuarios.carregando}>
          <div className="tabela-rolavel">
            <table>
              <thead>
                <tr>
                  <th scope="col">Nome</th>
                  <th scope="col">E-mail</th>
                  <th scope="col">Papel</th>
                  <th scope="col">Situação</th>
                  <th scope="col">
                    <span className="visualmente-oculto">Ações</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {usuarios.dados.itens.map((u) => {
                  // Um admin não pode se desativar nem tirar o próprio papel
                  // (a API também recusa com 409; aqui só evitamos o clique).
                  const ehVoce = u.id === logado.id;
                  return (
                    <tr key={u.id} className={u.is_active ? "" : "inativo"}>
                      <td>
                        {u.nome}
                        {ehVoce ? <span className="discreto"> (você)</span> : null}
                      </td>
                      <td>{u.email}</td>
                      <td>
                        <select
                          aria-label={`Papel de ${u.nome}`}
                          value={u.papel}
                          disabled={ehVoce}
                          onChange={(e) => alterar(u, { papel: e.target.value }, `Papel de ${u.nome} alterado.`)}
                        >
                          {PAPEIS.map(([valor, rotulo]) => (
                            <option key={valor} value={valor}>
                              {rotulo}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td>{u.is_active ? "Ativo" : "Desativado"}</td>
                      <td className="acoes">
                        {ehVoce ? null : (
                          <button type="button" className={u.is_active ? "perigo" : ""} onClick={() => alternarAtivo(u)} aria-label={`${u.is_active ? "Desativar" : "Reativar"} ${u.nome}`}>
                            {u.is_active ? "Desativar" : "Reativar"}
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <Paginacao pagina={pagina} total={usuarios.dados.total} porPagina={ITENS_POR_PAGINA} aoMudar={setPagina} rotulo="Páginas de usuários" />
        </div>
      ) : null}
    </section>
  );
}
