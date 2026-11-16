import { api } from "../api/cliente.js";
import * as datas from "./datas.js";

export const periodo = (r) => `${datas.hora(r.inicio)}–${datas.hora(r.fim)}`;

// Reserva que já começou não pode ser alterada (regra do domínio; a API
// também recusa com 409). Aqui só decide se os botões aparecem.
export const jaComecou = (r) => new Date(r.inicio) <= new Date();

// Pede confirmação e cancela. Devolve true se cancelou, false se a pessoa
// desistiu. Erros da API sobem para a tela tratar.
export async function cancelarReserva(reserva) {
  const texto = `Cancelar a reserva da ${reserva.sala.nome} em ${datas.data(reserva.inicio)}, ${periodo(reserva)}?`;
  if (!window.confirm(texto)) return false;
  await api.post(`/v1/reservas/${reserva.id}/cancelamento`);
  return true;
}
