# Cenários de qualidade

Formato: **fonte** → **estímulo** → **artefato** → **ambiente** → **resposta** → **medida**.
Cada cenário diz como foi verificado e o resultado obtido em 2026-11-11, no ambiente de
desenvolvimento (Docker Compose, 1 worker uvicorn com `--reload`, PostgreSQL 16, WSL2).

## QA-1 — Integridade: nenhuma reserva duplicada

| Elemento | Valor |
| --- | --- |
| Fonte | 2 a 10 colaboradores |
| Estímulo | pedem **ao mesmo tempo** a mesma sala no mesmo horário |
| Artefato | `POST /v1/reservas`, serviço de reservas e tabela `reservas` |
| Ambiente | operação normal, requisições concorrentes |
| Resposta | exatamente uma recebe 201; as outras recebem 409 com "Sala ocupada nesse horário" |
| Medida | **0 reservas duplicadas** no banco, mesmo com a checagem prévia do serviço desligada |

**Verificação:** `tests/test_concorrencia.py` (threads + `Barrier`). Com 2 e com 10 requisições
simultâneas, o resultado é **1 × 201** e **N−1 × 409**, com exatamente 1 linha no banco.
Contraprova: com a constraint removida do banco de teste, o mesmo teste gravou **10 reservas
de 10**. A constraint de exclusão é o que garante o resultado (ADR-003).

## QA-2 — Desempenho: consulta de disponibilidade

| Elemento | Valor |
| --- | --- |
| Fonte | 30 colaboradores |
| Estímulo | consultam a disponibilidade **simultaneamente**, 20 vezes cada (600 requisições) |
| Artefato | `GET /v1/disponibilidade` |
| Ambiente | operação normal, 4 salas e dados do seed |
| Resposta | lista de salas com livre/ocupada e as reservas que conflitam |
| Medida | **p95 ≤ 500 ms** e 0 erros |

**Verificação:** `docker compose exec api python -m app.scripts.carga_disponibilidade`

| Execução | Requisições | Erros | p50 | **p95** | p99 | Vazão |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 600 | 0 | 181 ms | **276 ms** | 324 ms | 151 req/s |
| 2 | 600 | 0 | 174 ms | **286 ms** | 387 ms | 156 req/s |

Meta atingida, com folga. A consulta faz **2 SELECTs** no total, independente do número de
salas, e a busca por sobreposição usa o índice GiST criado pela constraint de exclusão.

## QA-3 — Segurança: colaborador tentando cancelar reserva alheia

| Elemento | Valor |
| --- | --- |
| Fonte | colaborador autenticado (papel `colaborador`) |
| Estímulo | `POST /v1/reservas/{id}/cancelamento` de uma reserva de **outra** pessoa |
| Artefato | RBAC (`exigir_pode_alterar_reserva` no domínio) e serviço de reservas |
| Ambiente | operação normal; o botão não aparece no site, mas a chamada é feita direto na API |
| Resposta | **403** em Problem Details; a reserva continua **ativa**; o evento é registrado |
| Medida | 100% das tentativas → 403, **1 evento** `reserva.acesso_negado` em `eventos_auditoria` (com usuário, reserva e `request_id`) e 1 linha de log `warning` |

**Verificação:** `tests/test_api_reservas.py::test_colaborador_alterando_reserva_alheia_recebe_403_e_responsavel_consegue`
e `::test_acesso_negado_fica_registrado_na_auditoria`. No Postman, as requisições
"Bruno cancela reserva da Ana → 403" e "Histórico da reserva (responsável)" mostram o evento.

## QA-4 — Disponibilidade da demonstração

| Elemento | Valor |
| --- | --- |
| Fonte | quem apresenta o trabalho |
| Estímulo | (a) subir o sistema numa máquina com Docker; (b) a API ou o banco reiniciarem durante a apresentação |
| Artefato | `docker-compose.yml` (db + api + web), migrations, seed, `/health` |
| Ambiente | notebook de demonstração, sem depender de serviços externos |
| Resposta | (a) o sistema sobe com poucos comandos e já com dados de demonstração; (b) ele volta sozinho e os dados permanecem (volume `pgdata`) |
| Medida | (a) **4 comandos** do clone ao site com dados; (b) recuperação em **< 10 s**, `/health` respondendo `{"status":"ok","database":"ok"}` |

**Verificação (b), medida:**

| Evento | Tempo até `/health` = 200 |
| --- | --- |
| `docker compose restart api` | 2,8 s |
| `docker compose restart db` (a API reconecta sozinha com `pool_pre_ping`) | 1,3 s |

Comandos de (a), detalhados no README: `cp .env.example .env` (e editar), `docker compose up --build -d`,
`docker compose exec api alembic upgrade head` e `docker compose exec api python -m app.scripts.seed`.
O banco só aceita conexões depois do healthcheck (`depends_on: condition: service_healthy`).
