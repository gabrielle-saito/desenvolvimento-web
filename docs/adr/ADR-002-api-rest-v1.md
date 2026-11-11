# ADR-002 — API REST nível 2, versionada em `/v1`

- **Status:** aceito
- **Data:** 2026-11-11

## Contexto

A API atende hoje um front-end próprio (HTML + JS) e o Postman da disciplina. Ela deve ser
previsível para quem nunca a viu: os mesmos padrões de URL, de status e de erro em todas as
rotas. A base do professor usava rotas sem versão (`/auth`, `/items`), um `POST /auth/register`
público e erros no formato padrão do FastAPI (`{"detail": ...}`).

## Decisão

**REST nível 2** do modelo de maturidade de Richardson (recursos + verbos HTTP + status corretos),
com todas as rotas sob **`/v1`**.

| Tema | Decisão |
| --- | --- |
| Recursos | substantivos no plural: `/v1/salas`, `/v1/reservas`, `/v1/usuarios`, `/v1/auditoria` |
| Criação | `POST` → **201 Created + header `Location`** com a URL do novo recurso |
| Alteração | `PATCH` parcial (`exclude_unset`); o PATCH de reserva **exige `versao`** (ver ADR-003) |
| Cancelamento | `POST /v1/reservas/{id}/cancelamento` → 200 com a reserva cancelada. É **mudança de estado**, não `DELETE`: o histórico fica |
| Paginação | `limit`/`offset` com teto (100 a 500 conforme a rota), como na base |
| Autenticação | OAuth2 password flow → JWT (`POST /v1/auth/login`); `tokenUrl` atualizado para `/v1/auth/login` |
| Cadastro de usuários | `POST /v1/usuarios` **só para admin**; o `POST /auth/register` público foi **removido** (sistema interno) |
| Erros | **Problem Details (RFC 9457)**, `application/problem+json`, um handler por família de exceção de domínio |
| Datas | ISO 8601 **com fuso** na entrada (`AwareDatetime`; sem fuso → 422), sempre UTC na saída |
| Contrato | `contrato/openapi.json` exportado por script e commitado |

Mapa de status:

| Situação | Status |
| --- | --- |
| JSON ilegível | 400 |
| sem token / token inválido / usuário desativado | 401 (+ `WWW-Authenticate: Bearer`) |
| papel insuficiente; colaborador alterando reserva alheia | 403 |
| recurso inexistente | 404 |
| horário ocupado, versão desatualizada, nome/e-mail duplicado, reserva cancelada ou já iniciada, sala inativa, admin se rebaixando | 409 |
| validação do Pydantic (com a lista `erros`) e período inválido | 422 |

**403 e não 404 para reserva alheia.** A base respondia 404 para esconder itens de outras
pessoas. Aqui a agenda é **pública dentro da empresa** (caso de uso 3), então esconder a
existência da reserva não protege nada, e o 403 diz a verdade: "existe, mas você não pode".

### Decisões menores registradas (ambiguidades resolvidas pela opção mais simples)

- Os `type` do Problem Details são referências relativas (`/problemas/conflito-de-horario`).
  Elas identificam o tipo do erro, mas não apontam para uma página que exista.
- `GET /v1/reservas` não filtra por status por padrão. O front pede `status=ativa`.
  A lista vazia é `200 []`, e o front mostra "Não há reservas para o período".
- Um admin que tenta se desativar ou tirar o próprio papel recebe **409**
  (`/problemas/operacao-proibida`). Ele tem permissão (não é 403), mas o estado não permite.
- O PATCH com `"campo": null` explícito em reserva é recusado (422). Para manter um valor, basta
  omitir o campo.
- A consulta de disponibilidade e a agenda aceitam no máximo **31 dias** por chamada.

## Alternativas rejeitadas

| Alternativa | Motivo da rejeição |
| --- | --- |
| **GraphQL** | Há só um cliente (o nosso front) e as consultas são poucas e conhecidas. GraphQL acrescentaria schema, resolvers e cuidado com consultas caras, sem ganho real. |
| **RPC/ações na URL** (`/criarReserva`, `/cancelarReserva`) | Perde a semântica do HTTP (cache, idempotência, status) que o Postman e os navegadores entendem de graça. |
| **REST nível 3 (HATEOAS)** | Nenhum cliente navega por links. O custo de manter os links não teria uso. |
| **Versão em header** (`Accept: application/vnd...v1+json`) | É mais difícil de testar no navegador e no Postman. Versão na URL é visível e explícita. |
| **`DELETE /v1/reservas/{id}` para cancelar** | `DELETE` sugere que o recurso deixa de existir, mas a reserva cancelada continua existindo, e o histórico é requisito. |
| **Erros como `200 {"erro": ...}`** ou `{"detail": ...}` livre | O cliente teria que inspecionar o corpo para saber se deu certo. A RFC 9457 é padrão e permite extensões (`erros`, `versao_atual`, `reservas_conflitantes`). |

## Consequências

**Boas**
- O front trata erros por status, em um lugar só (`frontend/js/api.js`): 401 volta ao login,
  403 mostra "acesso negado", 409 mostra o `detail` e 422 mostra o erro em cada campo.
- A `/v1` permite publicar uma `/v2` incompatível convivendo com a `/v1`.
- O contrato commitado mostra mudanças de API como diff na revisão.

**Ruins**
- Cancelar via `POST` num sub-recurso é menos "óbvio" do que `DELETE` para quem espera CRUD.
- O `offset` fica lento em listas muito grandes (o banco percorre as linhas puladas).
- O JWT não pode ser revogado antes de expirar. O efeito é parcialmente compensado porque o
  token de um usuário **desativado** é recusado em toda requisição.

## Gatilhos de revisão

1. Uma mudança que **quebre** clientes (renomear ou remover campo, mudar tipo) → criar `/v2` e
   manter a `/v1` por pelo menos **1 semestre**.
2. Listagens com `offset > 1.000` frequentes, ou a tabela `reservas` passando de **100 mil
   linhas** → trocar para paginação por cursor (keyset: `inicio`, `id`).
3. Surgir um **segundo cliente** com necessidades de dados muito diferentes (ex.: app mobile
   nativo, hoje fora do escopo) → reavaliar GraphQL ou um BFF.
4. Exigência de **logout imediato** (revogar sessões) → token curto + refresh token ou lista de
   revogação.
