// "Anterior · Página 2 de 4 · Próxima". pagina começa em 1.
export default function Paginacao({ pagina, total, porPagina, aoMudar, rotulo = "Paginação" }) {
  const paginas = Math.max(1, Math.ceil(total / porPagina));
  if (total <= porPagina && pagina === 1) return null;
  return (
    <nav className="paginacao" aria-label={rotulo}>
      <button type="button" onClick={() => aoMudar(pagina - 1)} disabled={pagina <= 1}>
        ← Anterior
      </button>
      <p aria-live="polite">
        Página <strong>{pagina}</strong> de {paginas}
      </p>
      <button type="button" onClick={() => aoMudar(pagina + 1)} disabled={pagina >= paginas}>
        Próxima →
      </button>
    </nav>
  );
}
