import { Link } from "react-router";

import { useTitulo } from "../util/useCarregar.js";

export default function NaoEncontrada() {
  useTitulo("Página não encontrada");
  return (
    <div className="agenda-sem-reservas">
      <h1>Página não encontrada</h1>
      <p>O endereço pode ter mudado ou estar digitado errado.</p>
      <Link className="botao primario" to="/agenda">
        Ir para a agenda
      </Link>
    </div>
  );
}
