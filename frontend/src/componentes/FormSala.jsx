import { useState } from "react";

import Campo from "./Campo.jsx";
import SeletorRecursos from "./SeletorRecursos.jsx";

// Campos opcionais vazios viram null (e não "").
const textoOuNulo = (valor) => String(valor ?? "").trim() || null;

// Formulário de sala: o mesmo para cadastrar e para editar.
// aoEnviar(corpo) devolve uma Promise; se ela falhar com { erros }, os
// erros aparecem embaixo dos campos.
export default function FormSala({ idBase, inicial, recursos, rotuloBotao, aoEnviar, aoCancelar, erros = {} }) {
  const [campos, setCampos] = useState(() => ({
    nome: inicial?.nome ?? "",
    capacidade: inicial ? String(inicial.capacidade) : "",
    localizacao: inicial?.localizacao ?? "",
    descricao: inicial?.descricao ?? "",
    recurso_ids: inicial?.recursos?.map((r) => r.id) ?? [],
  }));
  const [errosLocais, setErrosLocais] = useState({});
  const [enviando, setEnviando] = useState(false);
  const mudar = (evento) => setCampos((c) => ({ ...c, [evento.target.name]: evento.target.value }));

  // Os recursos desativados só aparecem se a sala já os tem.
  const opcoes = recursos.filter((r) => r.ativo || campos.recurso_ids.includes(r.id));

  async function enviar(evento) {
    evento.preventDefault();
    const e = {};
    if (!campos.nome.trim()) e.nome = "Informe o nome.";
    if (!(Number(campos.capacidade) > 0)) e.capacidade = "Informe quantas pessoas cabem (1 ou mais).";
    setErrosLocais(e);
    if (Object.keys(e).length) return;
    setEnviando(true);
    const ok = await aoEnviar({
      nome: campos.nome.trim(),
      capacidade: Number(campos.capacidade),
      localizacao: textoOuNulo(campos.localizacao),
      descricao: textoOuNulo(campos.descricao),
      recurso_ids: campos.recurso_ids,
    });
    setEnviando(false);
    if (ok && !inicial) setCampos({ nome: "", capacidade: "", localizacao: "", descricao: "", recurso_ids: [] });
  }

  const erro = (campo) => errosLocais[campo] ?? erros[campo];
  return (
    <form onSubmit={enviar} noValidate>
      <div className="linha">
        <Campo id={`${idBase}-nome`} rotulo="Nome" name="nome" maxLength={120} value={campos.nome} onChange={mudar} erro={erro("nome")} required />
        <Campo
          id={`${idBase}-capacidade`}
          rotulo="Capacidade"
          name="capacidade"
          type="number"
          min={1}
          inputMode="numeric"
          value={campos.capacidade}
          onChange={mudar}
          erro={erro("capacidade")}
          required
        />
        <Campo id={`${idBase}-localizacao`} rotulo="Localização" name="localizacao" maxLength={200} value={campos.localizacao} onChange={mudar} erro={erro("localizacao")} />
      </div>
      <Campo id={`${idBase}-descricao`} rotulo="Descrição" name="descricao" maxLength={2000} value={campos.descricao} onChange={mudar} erro={erro("descricao")} />
      <SeletorRecursos
        id={`${idBase}-recursos`}
        legenda="Recursos da sala"
        recursos={opcoes}
        selecionados={campos.recurso_ids}
        aoMudar={(ids) => setCampos((c) => ({ ...c, recurso_ids: ids }))}
        erro={erro("recurso_ids")}
      />
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
