// Região aria-live: leitores de tela anunciam a mensagem quando ela muda.
// aviso = { texto, tipo: "info" | "sucesso" | "erro" } ou null.
export default function Aviso({ aviso, assertivo = false }) {
  return (
    <div aria-live={assertivo ? "assertive" : "polite"}>
      {aviso?.texto ? <p className={`aviso aviso-${aviso.tipo ?? "info"}`}>{aviso.texto}</p> : null}
    </div>
  );
}
