import { useState } from "react";

import { api, ErroApi, errosPorCampo, mensagemDeErro } from "../api/cliente.js";
import * as datas from "../util/datas.js";
import Aviso from "./Aviso.jsx";
import Campo from "./Campo.jsx";
import Janela from "./Janela.jsx";

// Janela (<dialog>) de edição de uma reserva. Envia a "versao" lida
// (locking otimista): se outra pessoa salvou antes, a API responde 409
// "versao-desatualizada" e a tela recarrega a lista.
//
// aoConcluir({ texto, tipo }) é chamado ao salvar ou no conflito de versão.
export default function DialogoEditarReserva({ reserva, salas, aoFechar, aoConcluir }) {
  const inicio = datas.paraCampos(reserva.inicio);
  const fim = datas.paraCampos(reserva.fim);
  const [campos, setCampos] = useState({
    sala_id: String(reserva.sala_id),
    data: inicio.data,
    inicio: inicio.hora,
    fim: fim.hora,
    finalidade: reserva.finalidade,
  });
  const [erros, setErros] = useState({});
  const [aviso, setAviso] = useState(null);
  const [salvando, setSalvando] = useState(false);

  const mudar = (evento) => setCampos((c) => ({ ...c, [evento.target.name]: evento.target.value }));

  async function salvar(evento) {
    evento.preventDefault();
    const faltando = {};
    if (!campos.data) faltando.data = "Escolha a data.";
    if (!campos.inicio) faltando.inicio = "Informe o início.";
    if (!campos.fim) faltando.fim = "Informe o fim.";
    if (!campos.finalidade.trim()) faltando.finalidade = "Informe a finalidade.";
    setErros(faltando);
    if (Object.keys(faltando).length) return;

    setSalvando(true);
    try {
      await api.patch(`/v1/reservas/${reserva.id}`, {
        versao: reserva.versao,
        sala_id: Number(campos.sala_id),
        inicio: datas.isoSaoPaulo(campos.data, campos.inicio),
        fim: datas.isoSaoPaulo(campos.data, campos.fim),
        finalidade: campos.finalidade.trim(),
      });
      aoConcluir({ texto: "Reserva atualizada.", tipo: "sucesso" });
    } catch (erro) {
      if (erro instanceof ErroApi && erro.problema.type === "/problemas/versao-desatualizada") {
        aoConcluir({
          texto: "Outra pessoa alterou esta reserva enquanto você editava. A lista foi recarregada: confira e tente de novo.",
          tipo: "erro",
        });
        return;
      }
      setErros(errosPorCampo(erro));
      setAviso({ texto: mensagemDeErro(erro), tipo: "erro" });
    } finally {
      setSalvando(false);
    }
  }

  const opcoes = salas.filter((s) => s.ativa || s.id === reserva.sala_id);
  return (
    <Janela titulo="Editar reserva" aoFechar={aoFechar}>
      <form onSubmit={salvar} noValidate>
        <Aviso aviso={aviso} assertivo />
        <Campo id="ed-sala" rotulo="Sala" como="select" name="sala_id" value={campos.sala_id} onChange={mudar} erro={erros.sala_id}>
          {opcoes.map((s) => (
            <option key={s.id} value={s.id}>
              {s.nome} ({s.capacidade} pessoas)
            </option>
          ))}
        </Campo>
        <Campo id="ed-data" rotulo="Data" type="date" name="data" value={campos.data} onChange={mudar} erro={erros.data} required />
        <div className="linha">
          <Campo id="ed-inicio" rotulo="Início" type="time" step={300} name="inicio" value={campos.inicio} onChange={mudar} erro={erros.inicio} required />
          <Campo id="ed-fim" rotulo="Fim" type="time" step={300} name="fim" value={campos.fim} onChange={mudar} erro={erros.fim} required />
        </div>
        <Campo id="ed-finalidade" rotulo="Finalidade" name="finalidade" maxLength={500} value={campos.finalidade} onChange={mudar} erro={erros.finalidade} required />
        <div className="acoes">
          <button type="submit" className="primario" disabled={salvando}>
            {salvando ? "Salvando…" : "Salvar"}
          </button>
          <button type="button" onClick={aoFechar}>
            Fechar
          </button>
        </div>
      </form>
    </Janela>
  );
}
