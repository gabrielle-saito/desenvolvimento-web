// Configuração do front-end.
//
// O endereço da API vem da variável VITE_API_URL (definida no
// docker-compose.yml ou num frontend/.env). Sem ela, usa a API local.
export const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

// Fuso usado para EXIBIR e DIGITAR horários. A API sempre recebe/devolve
// ISO 8601 com fuso, então não há ambiguidade.
export const FUSO = "America/Sao_Paulo";

// Intervalo de atualização automática da agenda (polling). Ver ADR-003.
export const INTERVALO_ATUALIZACAO_MS = 30_000;

// Itens por página nas listagens paginadas.
export const ITENS_POR_PAGINA = 10;
