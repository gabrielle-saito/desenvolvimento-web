import { useEffect, useState } from "react";

// Busca com espera (350 ms depois da última tecla) para listas do admin.
export function CampoBusca({ id, rotulo, placeholder, aoBuscar }) {
  const [texto, setTexto] = useState("");
  useEffect(() => {
    const espera = setTimeout(() => aoBuscar(texto.trim()), 350);
    return () => clearTimeout(espera);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [texto]);
  return (
    <div>
      <label htmlFor={id}>{rotulo}</label>
      <input id={id} type="search" placeholder={placeholder} maxLength={100} value={texto} onChange={(e) => setTexto(e.target.value)} />
    </div>
  );
}

// "Todas / Ativas / Inativas" -> true | false | undefined (para a API).
export function SeletorSituacao({ id, valor, aoMudar, rotulos = ["Todas", "Ativas", "Inativas"] }) {
  return (
    <div>
      <label htmlFor={id}>Situação</label>
      <select id={id} value={valor} onChange={(e) => aoMudar(e.target.value)}>
        <option value="">{rotulos[0]}</option>
        <option value="true">{rotulos[1]}</option>
        <option value="false">{rotulos[2]}</option>
      </select>
    </div>
  );
}
