# AGROEMERGIA — API base do projeto final

API em **FastAPI + PostgreSQL**, com migrations em **Alembic**, autenticação **JWT**
e autorização por dono de registro, tudo rodando em **Docker Compose**.

## Subir o ambiente (primeira vez)

```bash
# 1. Variáveis de ambiente
cp .env.example .env                 # Windows (PowerShell): copy .env.example .env

# 2. Gere uma SECRET_KEY e cole no .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
#   sem Python local? use o container:
#   docker compose run --rm --no-deps api python -c "import secrets; print(secrets.token_urlsafe(48))"

# 3. Suba banco + API
docker compose up --build

# 4. Em OUTRO terminal, crie as tabelas
docker compose exec api alembic upgrade head
```

Pronto:

- Health check: <http://localhost:8000/health>
- Documentação interativa (Swagger): <http://localhost:8000/docs>

## Rotas

| Método | Rota | Autenticação | O que faz |
| --- | --- | --- | --- |
| GET | `/health` | — | API e banco respondendo |
| POST | `/auth/register` | — | Cria usuário (JSON: `email`, `password`) |
| POST | `/auth/login` | — | Devolve o JWT (formulário: `username`, `password`) |
| GET | `/auth/me` | Bearer | Usuário dono do token |
| POST | `/items` | Bearer | Cria item do usuário logado |
| GET | `/items?limit=20&offset=0` | Bearer | Lista os itens do usuário logado |
| GET | `/items/{id}` | Bearer | Lê um item próprio (404 se for de outra pessoa) |
| PATCH | `/items/{id}` | Bearer | Altera um item próprio |
| DELETE | `/items/{id}` | Bearer | Apaga um item próprio |

A collection do Postman está em `postman/`. Importe os dois arquivos no Postman.

## Comandos do dia a dia

```bash
docker compose up                    # sobe (sem rebuild)
docker compose up --build            # sobe reconstruindo (mudou o requirements.txt)
docker compose down                  # derruba, MANTÉM os dados
docker compose down -v               # derruba e APAGA o banco
docker compose logs -f api           # acompanha os logs da API

# Banco
docker compose exec db psql -U agro -d agroemergia   # use o usuário/banco do seu .env

# Migrations
docker compose exec api alembic revision --autogenerate -m "descreva a mudança"
docker compose exec api alembic upgrade head
docker compose exec api alembic downgrade -1
docker compose exec api alembic history
```

> **Sempre leia a migration gerada antes de aplicar.** O autogenerate é um rascunho:
> ele não sabe lidar com dados já existentes nem dar nome a todas as constraints.

## Estrutura

```
backend/
├── alembic/versions/   migrations (histórico versionado do schema)
└── app/
    ├── main.py         cria a aplicação, CORS, registra as rotas
    ├── core/           config.py (variáveis de ambiente), security.py (hash + JWT)
    ├── db/             base.py (Base do ORM), session.py (conexão)
    ├── models/         tabelas (SQLAlchemy)
    ├── schemas/        contratos de entrada e saída (Pydantic)
    └── api/            deps.py (get_db, get_current_user), routes/
```

## Adaptando para o projeto do seu grupo

`Item` é uma entidade genérica. Para criar a sua (ex.: `Safra`):

1. Crie `app/models/safra.py` (use `item.py` como modelo, mantendo o `owner_id`).
2. **Importe o modelo em `app/models/__init__.py`**. Sem isso, a migration sai vazia.
3. Crie os schemas em `app/schemas/` e as rotas em `app/api/routes/`.
4. Registre o router em `app/main.py`.
5. Gere a migration, **leia**, aplique e teste no Postman.

## Checkpoints do laboratório

Se o seu ambiente quebrar durante a aula, volte para o último checkpoint:

```bash
git checkout cp2-items
```

| Tag | Estado |
| --- | --- |
| `cp1-health` | Docker Compose + `/health` |
| `cp2-items` | SQLAlchemy, Alembic, CRUD aberto |
| `cp3-auth` | Cadastro, login JWT, `/auth/me` |
| `cp4-authz` | Itens com dono, CORS restrito, collection do Postman |
