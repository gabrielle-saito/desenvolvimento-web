# ADR-001 — Monolito modular

- **Status:** aceito
- **Data:** 2026-11-11

## Contexto

O sistema substitui uma planilha Excel de reservas de salas de **uma** empresa. O uso esperado
é de dezenas a poucas centenas de colaboradores, com picos no início do expediente. A equipe é
pequena, o prazo é de um semestre e a entrega precisa rodar numa máquina de demonstração com um
único `docker compose up`.

O requisito mais crítico é a **integridade**: duas pessoas não podem reservar a mesma sala no
mesmo horário. Toda alteração também precisa deixar um rastro de auditoria **junto** com a
alteração, ou seja, as duas coisas gravadas ou nenhuma delas.

A base entregue pelo professor já é um processo FastAPI com PostgreSQL, Alembic e JWT.

## Decisão

Adotar um **monolito modular**: **1 processo FastAPI + 1 PostgreSQL 16**, com o código separado
em camadas e as dependências apontando para dentro:

```
api/v1  →  servicos  →  dominio  ←  (nada)
   │           │
schemas    repositorios → models → db
                 infra (relógio, logging, request_id)
```

| Camada | Responsabilidade | Pode importar |
| --- | --- | --- |
| `api/v1` | traduzir HTTP ↔ caso de uso; RBAC; DTOs | serviços, schemas, deps |
| `servicos` | casos de uso; **uma transação por caso de uso**; auditoria | domínio, repositórios, infra |
| `dominio` | regras puras, enums, exceções de domínio | **só a biblioteca padrão** |
| `repositorios` | consultas SQLAlchemy, sem regra de negócio, sem commit | models |

A regra "o domínio é puro" **não fica só no papel**: `tests/test_arquitetura.py` lê `app/dominio`
com `ast` e falha se algum módulo importar `fastapi`, `sqlalchemy`, `pydantic`, `app.db`,
`app.models`, `app.repositorios` (e as demais camadas externas) ou chamar `datetime.now`.
O "agora" entra como parâmetro e vem de `app/infra/relogio.py`, o único lugar que lê o relógio.

Também ficaram de fora, de propósito, filas, Redis, WebSocket e qualquer separação em serviços.

## Alternativas rejeitadas

| Alternativa | Motivo da rejeição |
| --- | --- |
| **Microsserviços** (ex.: serviço de salas + serviço de reservas + serviço de auditoria) | Reserva e auditoria precisariam de transação distribuída (saga/outbox) para manter o "tudo ou nada", e a checagem de sala ativa viraria chamada de rede. O custo de operação (vários deploys, rede, observabilidade distribuída) não se paga com centenas de usuários. |
| **Monolito sem camadas** (rotas falando direto com o ORM, como na base) | As regras de reserva ficariam espalhadas nas rotas, e testá-las exigiria banco e HTTP. A base funcionava assim porque tinha só um CRUD de `Item`. |
| **Hexagonal "completo"** (portas e adaptadores para tudo, repositórios como interfaces abstratas) | Ninguém pretende trocar o PostgreSQL: a garantia contra reserva dupla **depende** dele (constraint `EXCLUDE`). Abstrair o banco esconderia a peça mais importante do sistema e dobraria o código. |
| **Serverless / funções** | A conexão com o banco por requisição e o cold start atrapalham a demo local, e o problema não tem carga intermitente que justifique. |

## Consequências

**Boas**
- Um deploy, um processo, um `docker compose up`, e a demo não depende de rede externa.
- O caso de uso "reservar" grava a reserva **e** o evento de auditoria na **mesma transação
  ACID**. Não existe reserva sem evento nem evento de algo que não aconteceu.
- As regras de domínio são testadas em milissegundos e sem banco (`tests/test_dominio.py`).
- As camadas permitem, se algum dia for preciso, extrair um módulo (ex.: notificações) sem
  reescrever o domínio.

**Ruins**
- A escala é **vertical**: mais carga exige uma máquina maior ou mais workers do mesmo processo.
- Uma falha no processo derruba tudo (API e regras juntas).
- As camadas exigem disciplina, porque o Python não impede uma rota de importar um modelo. Só a
  pureza do domínio é verificada automaticamente. As outras regras dependem de revisão de código.

## Gatilhos de revisão

Reavaliar esta decisão se **qualquer** um destes acontecer:

1. `GET /v1/disponibilidade` passar de **p95 > 500 ms** na medição da QA-2 **mesmo depois** de
   subir para 4 workers uvicorn, sem o banco ser o gargalo. Hoje o p95 é de cerca de 280 ms
   com 1 worker.
2. O uso passar de **1.000 usuários ativos por dia** ou de **50 req/s sustentadas** no horário
   de pico.
3. Entrar no escopo um módulo com necessidade de disponibilidade **diferente** do resto, por
   exemplo notificações por WhatsApp/e-mail que não podem derrubar as reservas quando o
   provedor externo cair.
4. Mais de **3 equipes** passarem a trabalhar no mesmo código, com conflitos de merge
   frequentes (mais de 1 por semana) nas mesmas camadas.
