import { useState } from "react";

// Campo de senha com o botão "Mostrar"/"Ocultar" dentro.
export default function CampoSenha({ id, rotulo = "Senha", erro, ...props }) {
  const [visivel, setVisivel] = useState(false);
  const idErro = `${id}-erro`;
  return (
    <div>
      <label htmlFor={id}>{rotulo}</label>
      <div className="campo-senha">
        <input
          id={id}
          type={visivel ? "text" : "password"}
          aria-invalid={erro ? "true" : undefined}
          aria-describedby={erro ? idErro : undefined}
          {...props}
        />
        <button
          type="button"
          className="mostrar-senha"
          aria-controls={id}
          aria-pressed={visivel}
          // Sem isto o foco pula para o botão e volta, e a borda do campo "pisca".
          onMouseDown={(evento) => evento.preventDefault()}
          onClick={() => setVisivel((v) => !v)}
        >
          {visivel ? "Ocultar" : "Mostrar"}
        </button>
      </div>
      {erro ? (
        <span className="erro-campo" id={idErro}>
          {erro}
        </span>
      ) : null}
    </div>
  );
}
