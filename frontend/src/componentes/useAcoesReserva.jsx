import { useState } from "react";

import { mensagemDeErro } from "../api/cliente.js";
import { cancelarReserva } from "../util/reservas.js";
import DialogoEditarReserva from "./DialogoEditarReserva.jsx";

// Editar e cancelar reservas numa lista, com a mensagem de resultado.
// Usado em "Minhas reservas" e "Gerenciar reservas".
export function useAcoesReserva(recarregar) {
  const [aviso, setAviso] = useState(null);
  const [editando, setEditando] = useState(null);

  async function cancelar(reserva) {
    try {
      if (!(await cancelarReserva(reserva))) return;
      setAviso({ texto: "Reserva cancelada. O horário ficou livre.", tipo: "sucesso" });
    } catch (erro) {
      setAviso({ texto: mensagemDeErro(erro), tipo: "erro" });
    }
    recarregar();
  }

  const dialogo = (salas) =>
    editando ? (
      <DialogoEditarReserva
        reserva={editando}
        salas={salas}
        aoFechar={() => setEditando(null)}
        aoConcluir={(resultado) => {
          setEditando(null);
          setAviso(resultado);
          recarregar();
        }}
      />
    ) : null;

  return { aviso, setAviso, editar: setEditando, cancelar, dialogo };
}
