// Configuração do front-end. É o ÚNICO lugar com o endereço da API:
// para apontar para outro servidor, mude só esta linha.
export const API_URL = "http://localhost:8000";

// Fuso usado para EXIBIR e DIGITAR horários. A API sempre recebe/devolve
// ISO 8601 com fuso, então não há ambiguidade.
export const FUSO = "America/Sao_Paulo";

// Intervalo de atualização automática da agenda (polling). Ver ADR-003.
export const INTERVALO_ATUALIZACAO_MS = 30_000;
