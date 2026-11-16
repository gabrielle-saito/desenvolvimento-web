// Recursos de uma sala como etiquetas ("Projetor", "TV"...).
export default function EtiquetasRecursos({ recursos }) {
  if (!recursos?.length) return <p className="discreto bloco">Sem equipamentos</p>;
  return (
    <ul className="etiquetas" aria-label="Recursos">
      {recursos.map((r) => (
        <li key={r.id} className="etiqueta">
          {r.nome}
        </li>
      ))}
    </ul>
  );
}
