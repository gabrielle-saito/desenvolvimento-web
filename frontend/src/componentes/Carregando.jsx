export default function Carregando({ texto = "Carregando…" }) {
  return (
    <p className="carregando" role="status">
      <span className="carregando-ponto" aria-hidden="true" />
      {texto}
    </p>
  );
}
