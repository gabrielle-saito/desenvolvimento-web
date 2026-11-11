// Datas e horários no fuso de São Paulo.
//
// O usuário digita "10/03 às 14:00" pensando no horário de São Paulo. A API
// exige ISO 8601 COM fuso. Estas funções fazem a ponte nos dois sentidos,
// sem depender do fuso configurado no computador de quem está usando.

import { FUSO } from "../config.js";

const formatoHora = new Intl.DateTimeFormat("pt-BR", {
  timeZone: FUSO,
  hour: "2-digit",
  minute: "2-digit",
});
const formatoData = new Intl.DateTimeFormat("pt-BR", {
  timeZone: FUSO,
  weekday: "short",
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
});
const partesFormato = new Intl.DateTimeFormat("en-CA", {
  timeZone: FUSO,
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});

export const hora = (iso) => formatoHora.format(new Date(iso));
export const data = (iso) => formatoData.format(new Date(iso));

// Partes (ano, mês, dia, hora, minuto) de um instante, vistas em São Paulo.
function partesEmSaoPaulo(instante) {
  const p = Object.fromEntries(partesFormato.formatToParts(instante).map((x) => [x.type, x.value]));
  return { ano: p.year, mes: p.month, dia: p.day, hora: p.hour, minuto: p.minute };
}

// "2030-03-10" de hoje em São Paulo (valor para <input type="date">).
export function hojeEmSaoPaulo() {
  const p = partesEmSaoPaulo(new Date());
  return `${p.ano}-${p.mes}-${p.dia}`;
}

// Valores de <input type="date"> e <input type="time"> de um instante ISO.
export function paraCampos(iso) {
  const p = partesEmSaoPaulo(new Date(iso));
  return { data: `${p.ano}-${p.mes}-${p.dia}`, hora: `${p.hora}:${p.minuto}` };
}

// Diferença (em minutos) entre São Paulo e UTC num dado instante.
function deslocamentoMinutos(instante) {
  const p = partesEmSaoPaulo(instante);
  const comoUtc = Date.UTC(p.ano, p.mes - 1, p.dia, p.hora, p.minuto);
  return Math.round((comoUtc - instante.getTime()) / 60000);
}

// ("2030-03-10", "14:00") -> "2030-03-10T14:00:00-03:00"
export function isoSaoPaulo(dataTexto, horaTexto) {
  const [ano, mes, dia] = dataTexto.split("-").map(Number);
  const [h, m] = horaTexto.split(":").map(Number);
  const palpite = new Date(Date.UTC(ano, mes - 1, dia, h, m));
  const desloc = deslocamentoMinutos(palpite);
  const sinal = desloc <= 0 ? "-" : "+";
  const abs = Math.abs(desloc);
  const hh = String(Math.floor(abs / 60)).padStart(2, "0");
  const mm = String(abs % 60).padStart(2, "0");
  return `${dataTexto}T${horaTexto}:00${sinal}${hh}:${mm}`;
}

// Janela [00:00 do dia, 00:00 do dia seguinte) em São Paulo.
export function somarDias(dataTexto, dias) {
  const [ano, mes, dia] = dataTexto.split("-").map(Number);
  const d = new Date(Date.UTC(ano, mes - 1, dia + dias));
  return d.toISOString().slice(0, 10);
}

export function janelaDoDia(dataTexto) {
  return { de: isoSaoPaulo(dataTexto, "00:00"), ate: isoSaoPaulo(somarDias(dataTexto, 1), "00:00") };
}
