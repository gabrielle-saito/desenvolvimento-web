# Reserva de Salas

[![CI](https://github.com/gabrielle-saito/desenvolvimento-web/actions/workflows/ci.yml/badge.svg)](https://github.com/gabrielle-saito/desenvolvimento-web/actions/workflows/ci.yml)

Sistema web de **reserva de salas de reunião** de uma empresa. Ele substitui a planilha Excel
que causava conflitos de horário, informação desatualizada e dificuldade de ver a
disponibilidade.

- **Back-end:** FastAPI + PostgreSQL 16 + SQLAlchemy 2 + Alembic, com JWT (pyjwt + Argon2)
- **Front-end:** React 19 + Vite + React Router, em `frontend/`. Sessão compartilhada com Context API
- **Arquitetura:** monolito modular (1 processo + 1 banco). Ver [ADR-001](docs/adr/ADR-001-monolito-modular.md)
- **Garantia contra reserva dupla:** constraint de exclusão no PostgreSQL. Ver [ADR-003](docs/adr/ADR-003-concorrencia-e-tempo-real.md)

## O que o sistema faz

| Papel | Pode |
| --- | --- |
| **colaborador** | consultar disponibilidade, ver a agenda de todos, reservar e editar/cancelar **as próprias** reservas |
| **responsável** | tudo do colaborador + editar/cancelar **qualquer** reserva e ver a auditoria |
| **admin** | tudo do responsável + cadastrar/editar/desativar **salas**, **recursos** e **usuários** (inclusive o papel) |

Qualquer pessoa pode criar a própria conta (`POST /v1/auth/registro`): ela entra sempre como
**colaborador**. Só o admin promove alguém a responsável ou admin.

Regras principais:
- Duas reservas ativas da mesma sala não podem se sobrepor. Reservas encostadas
  (10h–11h e 11h–12h) são permitidas.
- Uma reserva dura de 15 min a 8 h e não pode começar no passado.
- Reserva cancelada ou que já começou não pode ser editada nem cancelada.
- Sala desativada não recebe reservas novas, mas as que ela já tem continuam valendo.
- Um admin não pode se desativar nem tirar o próprio papel de admin.

## Subir o ambiente (primeira vez)

Pré-requisito: Docker com Compose.

```bash
# 1. Variáveis de ambiente
cp .env.example .env            # Windows (PowerShell): copy .env.example .env

# 2. Edite o .env:
#    - SECRET_KEY: gere uma chave (mínimo 32 caracteres; a API NÃO sobe sem ela)
#        python -c "import secrets; print(secrets.token_urlsafe(48))"
#        sem Python local: docker compose run --rm --no-deps api python -c "import secrets; print(secrets.token_urlsafe(48))"
#    - POSTGRES_PASSWORD, SEED_ADMIN_SENHA: troque os valores de exemplo

# 3. Suba banco + API + site
docker compose up --build -d
```

Ao subir, a API **aplica as migrations e roda o seed sozinha** (o seed é idempotente: não
duplica nada). Não há passo manual de banco. Se quiser rodar de novo à mão:
`npm run setup` (ou `docker compose exec api alembic upgrade head` e
`docker compose exec api python -m app.scripts.seed`).

Pronto:

| O quê | Onde |
| --- | --- |
| **Site** | <http://localhost:5173> |
| API (Swagger) | <http://localhost:8000/docs> |
| Health check | <http://localhost:8000/health> |

### Atalhos com npm (opcional)

Quem preferir o `npm` pode usar os atalhos do `package.json`. Eles só chamam o
Docker Compose, então não há `npm install` nem dependências Node.

| Comando | Equivale a |
| --- | --- |
| `npm run dev` | `docker compose up --build` (fica no terminal mostrando os logs; Ctrl+C para) |
| `npm run setup` | migrations + seed (rode em outro terminal, na primeira vez) |
| `npm test` | `docker compose exec api pytest` |
| `npm run logs` | logs da API |
| `npm run down` | derruba os containers (mantém os dados) |
| `npm run openapi` | regera `contrato/openapi.json` |

### Usuários criados pelo seed

O seed é idempotente: pode rodar de novo sem duplicar nada.

| E-mail | Papel | Senha |
| --- | --- | --- |
| valor de `SEED_ADMIN_EMAIL` (padrão `admin@empresa.com`) | admin | `SEED_ADMIN_SENHA` do `.env` |
| `rita@empresa.com` | responsável | `SEED_SENHA_DEMO` do `.env` |
| `ana@empresa.com` | colaborador | `SEED_SENHA_DEMO` do `.env` |
| `bruno@empresa.com` | colaborador | `SEED_SENHA_DEMO` do `.env` |

O seed também cria **6 recursos** (projetor, TV, videoconferência, quadro branco, sistema de
som, ar-condicionado), **15 salas** ligadas aos seus recursos e **15 reservas** para
**amanhã**, para a agenda não começar vazia. As reservas só são criadas se o banco ainda não
tiver nenhuma. Outros usuários: cadastro público (`POST /v1/auth/registro`, sempre
colaborador) ou, pelo admin, **Administração** no site (`POST /v1/usuarios`, qualquer papel).

## Testes

```bash
docker compose exec api pytest
```

Os testes rodam num banco **separado**, `<POSTGRES_DB>_test`, que é criado e migrado com o
Alembic automaticamente. O banco de desenvolvimento nunca é tocado.

| Arquivo | O que cobre |
| --- | --- |
| `tests/test_dominio.py` | regras puras: sobreposição, bordas encostadas, período, duração, permissões (sem banco, sem HTTP, sem relógio) |
| `tests/test_arquitetura.py` | *fitness function*: `app/dominio` não pode importar fastapi/sqlalchemy/pydantic/camadas externas nem chamar `datetime.now` |
| `tests/test_migrations.py` | modelos e migrations batem (`alembic check`); downgrade e upgrade completos |
| `tests/test_api_reservas.py` | 201 + Location, 409 de sobreposição, encostadas, cancelar libera, 403/responsável, versão velha, 422 sem fuso e com campo extra, sala inativa, agenda, disponibilidade, auditoria |
| `tests/test_api_admin.py` | RBAC das rotas de admin (403/401), salas, usuários, login, Problem Details, request_id, 500 sem stack trace |
| `tests/test_api_catalogo.py` | recursos (CRUD, 409, desativar), sala ↔ recurso (N:N), busca/filtros/paginação com `X-Total-Count`, cadastro público, exemplos no Swagger |
| `tests/test_concorrencia.py` | 2 e 10 requisições **simultâneas** → exatamente uma 201; edições simultâneas → só uma vence |

### Integração contínua (GitHub Actions)

A cada push na `main` e a cada pull request, o workflow
[`.github/workflows/ci.yml`](.github/workflows/ci.yml) roda dois jobs:

| Job | O que faz |
| --- | --- |
| **API (pytest)** | sobe um PostgreSQL 16 temporário, instala o `requirements.txt` e roda todos os testes (as migrations do Alembic incluídas) |
| **Front-end (build)** | `npm ci` e `npm run build` do React: falha se o código não compila |

Nenhum segredo fica no workflow: o banco do CI é temporário e sem senha, e a `SECRET_KEY` é
gerada a cada execução. O resultado aparece como ✅/❌ no commit e no PR, e na aba
**Actions** do GitHub. Para rodar de novo à mão: Actions → CI → **Run workflow**.

## Rotas

Todas sob `/v1`, exceto `/health`. Os erros saem em **Problem Details** (`application/problem+json`).

| Método | Rota | Quem | O que faz |
| --- | --- | --- | --- |
| GET | `/health` | — | API e banco respondendo |
| POST | `/v1/auth/registro` | — | cadastro público (`email`, `nome`, `senha`) → 201, sempre colaborador; e-mail repetido → 409 |
| POST | `/v1/auth/login` | — | formulário OAuth2 (`username`, `password`) → JWT |
| GET | `/v1/auth/me` | logado | id, nome, email, papel |
| GET | `/v1/usuarios?busca=&papel=&ativos=` | admin | lista usuários (busca no nome e no e-mail) |
| POST | `/v1/usuarios` | admin | cria usuário → 201 + Location |
| GET | `/v1/usuarios/{id}` | admin | lê um usuário |
| PATCH | `/v1/usuarios/{id}` | admin | `nome`, `papel`, `is_active` |
| GET | `/v1/salas?busca=&ativas=&capacidade_minima=&recurso=` | logado | catálogo de salas: busca no nome e na localização; `recurso` pode repetir (a sala precisa ter todos) |
| GET | `/v1/salas/{id}` | logado | lê uma sala (com os recursos) |
| POST | `/v1/salas` | admin | cria sala, com `recurso_ids` → 201 + Location; nome repetido → 409; recurso inexistente/desativado → 422 |
| PATCH | `/v1/salas/{id}` | admin | edita; `ativa=false` desativa; `recurso_ids` substitui a lista de recursos |
| GET | `/v1/recursos?busca=&ativos=` | logado | lista recursos (projetor, TV...) |
| GET | `/v1/recursos/{id}` | logado | lê um recurso |
| POST | `/v1/recursos` | admin | cria recurso → 201 + Location; nome repetido → 409 |
| PATCH | `/v1/recursos/{id}` | admin | edita; `ativo=false` desativa (as salas que já têm continuam com ele) |
| GET | `/v1/disponibilidade?inicio=&fim=&capacidade_minima=` | logado | cada sala ativa: livre ou não, e as reservas que conflitam |
| GET | `/v1/reservas?sala_id=&de=&ate=&minhas=true&status=&busca=` | logado | agenda (todos veem), ordenada por início; busca na finalidade |
| GET | `/v1/reservas/{id}` | logado | lê uma reserva |
| POST | `/v1/reservas` | logado | reserva → 201 + Location; 409 conflito; 422 período inválido |
| PATCH | `/v1/reservas/{id}` | dono, responsável, admin | edita; corpo **exige `versao`** (locking otimista) |
| POST | `/v1/reservas/{id}/cancelamento` | dono, responsável, admin | cancela (mudança de estado, não DELETE) → 200 |
| GET | `/v1/auditoria?entidade=&entidade_id=` | responsável, admin | trilha de auditoria |

**Paginação:** toda listagem aceita `limit` e `offset`, e devolve o total de itens (já com
os filtros) no cabeçalho **`X-Total-Count`**. Ex.: `GET /v1/salas?limit=10&offset=10` é a
página 2; com `X-Total-Count: 15`, são 2 páginas.

Datas: **ISO 8601 com fuso** (ex.: `2030-01-31T14:00:00-03:00`). Data sem fuso → 422.
As respostas vêm em UTC (`...Z`). Na query string, codifique o `+` do fuso como `%2B`.

O contrato completo está em [`contrato/openapi.json`](contrato/openapi.json). Para regerar:

```bash
docker compose exec -T api python -m app.scripts.exportar_openapi > contrato/openapi.json
```

### Formato de erro (RFC 9457)

```json
{
  "type": "/problemas/conflito-de-horario",
  "title": "Conflito de horário",
  "status": 409,
  "detail": "Sala ocupada nesse horário. Escolha outro horário ou outra sala.",
  "instance": "/v1/reservas",
  "reservas_conflitantes": [7]
}
```

O 422 de validação traz `"erros": [{"campo": "inicio", "local": "body", "mensagem": "..."}]`.

## Postman

Importe os dois arquivos de [`postman/`](postman/) e selecione o environment
**Reserva de Salas local**. Ajuste `admin_senha` e `senha_demo` para os valores do seu `.env`
e rode a collection inteira no Runner. São 44 requisições e 94 testes: o fluxo completo e os
casos de erro. A collection limpa as próprias reservas no fim, então pode rodar de novo.

## Observabilidade e auditoria

- **Logs** em JSON no stdout (`docker compose logs -f api`): uma linha por evento, com
  `timestamp` UTC, `level`, `event` (ex.: `reserva.criada`, `reserva.conflito`,
  `auth.login_falhou`) e `request_id`.
- **`X-Request-ID`**: lido do cliente ou gerado, e devolvido em toda resposta. O mesmo id está
  nos logs e nos eventos de auditoria.
- **`eventos_auditoria`**: toda alteração grava um evento (com `antes`/`depois`) **na mesma
  transação**. A tabela é append-only: um trigger recusa UPDATE e DELETE.

## Comandos do dia a dia

```bash
docker compose up -d                 # sobe (sem rebuild)
docker compose up --build -d         # sobe reconstruindo (mudou o requirements.txt)
docker compose down                  # derruba, MANTÉM os dados
docker compose down -v               # derruba e APAGA o banco
docker compose logs -f api           # logs da API (JSON)

# Banco
docker compose exec db psql -U reserva -d reserva_salas   # use o usuário/banco do seu .env

# Migrations
docker compose exec api alembic revision --autogenerate -m "descreva a mudança"
docker compose exec api alembic upgrade head
docker compose exec api alembic downgrade -1
docker compose exec api alembic check            # modelos x banco

# Medir o cenário de desempenho (docs/cenarios-qualidade.md, QA-2)
docker compose exec api python -m app.scripts.carga_disponibilidade
```

> **Sempre leia a migration gerada antes de aplicar.** O autogenerate é um rascunho: ele não
> sabe lidar com dados já existentes, não cria a extensão `btree_gist` e não dá nome a todas
> as constraints. Todas as migrations deste projeto foram revisadas à mão.

## Estrutura

```
backend/
├── alembic/versions/   migrations revisadas à mão
├── app/
│   ├── main.py         cria a app: handlers de erro, CORS, request_id, rotas
│   ├── api/
│   │   ├── v1/         rotas (auth, usuarios, salas, recursos, disponibilidade, reservas, auditoria)
│   │   ├── paginacao.py  cabeçalho X-Total-Count
│   │   ├── deps.py     get_db, get_current_user, exigir_papel(...)
│   │   └── erros.py    Problem Details: um handler por família de exceção
│   ├── schemas/        DTOs Pydantic (entrada extra="forbid", saída from_attributes)
│   ├── servicos/       casos de uso: domínio + repositório + auditoria, 1 transação cada
│   ├── dominio/        NÚCLEO PURO: enums, regras, exceções (sem framework, sem relógio)
│   ├── repositorios/   consultas SQLAlchemy
│   ├── models/         tabelas ORM
│   ├── infra/          relogio.py, logging_config.py, request_id.py
│   ├── core/ db/       configuração, segurança (Argon2, JWT), sessão
│   └── scripts/        seed, exportar_openapi, carga_disponibilidade
└── tests/
frontend/               React + Vite (ver "Front-end" abaixo)
contrato/openapi.json   contrato exportado
docs/adr/               decisões de arquitetura
docs/cenarios-qualidade.md
postman/                collection + environment
```

## Front-end

React 19 + Vite + React Router, sem biblioteca de componentes (o CSS é próprio, em
`src/estilo.css`). No Docker, o serviço `web` roda o Vite com recarga automática; o endereço
da API vem de `VITE_API_URL` (padrão `http://localhost:8000`).

| Tela | Rota | Quem |
| --- | --- | --- |
| Entrar / Criar conta | `/login`, `/cadastro` | público |
| Agenda do dia (linha do tempo, atualiza a cada 30 s) | `/agenda` | logado |
| Catálogo de salas: busca, filtro por capacidade e recursos, paginação | `/salas` | logado |
| Consultar disponibilidade e reservar | `/reservar` | logado |
| Minhas reservas (editar/cancelar, paginada) | `/minhas` | logado |
| Gerenciar qualquer reserva (filtros, busca, paginada) | `/gerenciar` | responsável, admin |
| Administração: salas, recursos, usuários | `/admin/salas`, `/admin/recursos`, `/admin/usuarios` | admin |

```
frontend/src/
├── main.jsx            BrowserRouter + AuthProvider + App
├── App.jsx             rotas (React Router) e o papel mínimo de cada grupo
├── contexto/           AuthContext: usuário logado para todas as telas (useAuth)
├── api/                cliente.js (fetch, token, erros RFC 9457, X-Total-Count) e sessao.js
├── componentes/        Layout, RotaProtegida, Campo, Paginacao, Janela, TabelaReservas,
│                       CartaoSala, FormSala, SeletorRecursos, Aviso, Carregando...
├── paginas/            uma tela por arquivo (admin/ tem as abas da administração)
└── util/               datas (fuso de São Paulo), useCarregar (carregando/erro/dados)
```

- **Rotas protegidas nos dois lados:** `RotaProtegida` leva quem não entrou para o login e
  mostra "Acesso negado" a quem não tem o papel. É só conforto: quem bloqueia é a API (401/403).
- **Estados de tela:** toda tela que chama a API trata carregando, erro e lista vazia.
- **Erros da API:** o 422 aparece embaixo de cada campo; 409 e os demais, num aviso no topo.
- **Sessão:** o token fica no `sessionStorage` (some ao fechar a aba). Um 401 volta ao login.

Para rodar fora do Docker: `cd frontend && npm install && npm run dev`.

## Documentação

- [ADR-001 — Monolito modular](docs/adr/ADR-001-monolito-modular.md)
- [ADR-002 — API REST v1](docs/adr/ADR-002-api-rest-v1.md)
- [ADR-003 — Concorrência e tempo real](docs/adr/ADR-003-concorrencia-e-tempo-real.md)
- [Cenários de qualidade](docs/cenarios-qualidade.md)

Fora do escopo: integração com Outlook/Google Calendar, notificações, controle de acesso
físico, reserva de veículos/equipamentos, app mobile nativo e
relatórios avançados.
