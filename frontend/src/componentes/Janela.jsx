import { useEffect, useId, useRef } from "react";

// Janela modal (<dialog> nativo): prende o foco dentro dela, fecha com Esc
// e devolve o foco para quem a abriu ao fechar. Quem manda é o estado do
// React: a janela existe enquanto o componente está na tela.
export default function Janela({ titulo, aoFechar, children }) {
  const dialogo = useRef(null);
  const idTitulo = useId();

  useEffect(() => {
    const d = dialogo.current;
    const anterior = document.activeElement;
    d.showModal();
    return () => {
      d.close();
      anterior?.focus?.();
    };
  }, []);

  return (
    <dialog
      ref={dialogo}
      aria-labelledby={idTitulo}
      onCancel={(evento) => {
        evento.preventDefault(); // Esc: fecha pelo estado, não pelo navegador
        aoFechar();
      }}
    >
      <h2 id={idTitulo}>{titulo}</h2>
      {children}
    </dialog>
  );
}
