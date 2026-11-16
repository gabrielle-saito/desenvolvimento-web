// Caixas de seleção dos recursos (usado no cadastro e na edição de salas e
// no filtro do catálogo). selecionados = lista de ids.
export default function SeletorRecursos({ id, legenda, recursos, selecionados, aoMudar, erro }) {
  const alternar = (recursoId) =>
    aoMudar(
      selecionados.includes(recursoId)
        ? selecionados.filter((x) => x !== recursoId)
        : [...selecionados, recursoId],
    );
  return (
    <fieldset className="seletor-recursos" aria-describedby={erro ? `${id}-erro` : undefined}>
      <legend>{legenda}</legend>
      {recursos.length === 0 ? <p className="discreto">Nenhum recurso cadastrado.</p> : null}
      <div className="opcoes-recursos">
        {recursos.map((r) => (
          <label key={r.id} className="opcao-recurso">
            <input
              type="checkbox"
              checked={selecionados.includes(r.id)}
              onChange={() => alternar(r.id)}
            />
            {r.nome}
            {r.ativo === false ? <span className="discreto"> (desativado)</span> : null}
          </label>
        ))}
      </div>
      {erro ? (
        <span className="erro-campo" id={`${id}-erro`}>
          {erro}
        </span>
      ) : null}
    </fieldset>
  );
}
