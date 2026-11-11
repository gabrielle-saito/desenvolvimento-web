# ADR-003 — Concorrência e "tempo real"

- **Status:** aceito
- **Data:** 2026-11-11

## Contexto

Há três problemas de concorrência:

1. **Reserva dupla.** Duas pessoas pedem a mesma sala no mesmo horário ao mesmo tempo. A planilha
   Excel tinha exatamente esse defeito. Checar antes com `SELECT` **não resolve**: as duas
   requisições fazem o SELECT juntas, as duas veem a sala livre e as duas gravam. É o mesmo
   raciocínio do `/auth/register` da base, que confia a unicidade do e-mail à constraint do banco.
2. **Atualização perdida (lost update).** Duas abas abertas leem a reserva e as duas salvam. A
   segunda sobrescreve a primeira sem saber que ela existiu.
3. **Agenda desatualizada.** O site precisa mostrar reservas que outras pessoas acabaram de fazer.

## Decisão

### 1. Reserva dupla → constraint de exclusão no PostgreSQL

```sql
CREATE EXTENSION IF NOT EXISTS btree_gist;
ALTER TABLE reservas ADD CONSTRAINT ex_reservas_sala_sem_sobreposicao
  EXCLUDE USING gist (sala_id WITH =, tstzrange(inicio, fim, '[)') WITH &&)
  WHERE (status = 'ativa');
```

- O intervalo **`[)`** (fecha no início, abre no fim) permite reservas encostadas, como
  10h–11h seguida de 11h–12h.
- O `WHERE status = 'ativa'` faz uma reserva **cancelada** liberar o horário na hora.
- A mesma constraint aparece no modelo (`ExcludeConstraint`), para o autogenerate do Alembic não
  tentar removê-la. O `tests/test_migrations.py` confere que modelo e migration batem.
- O serviço **também** verifica antes (`ativas_que_conflitam`), usando a **mesma expressão**
  `tstzrange && tstzrange`. Isso serve só para dar uma resposta melhor, com os ids das reservas
  que conflitam. A garantia final é o banco: o `IntegrityError` com **SQLSTATE 23P01** vira
  `ConflitoDeHorario` → **409**.

### 2. Lost update → locking otimista em duas barreiras

- A coluna `versao` começa em 1, e o `PATCH /v1/reservas/{id}` **exige** a `versao` que o
  cliente leu.
- **Barreira 1 (serviço):** se a versão enviada for diferente da atual → 409
  `VersaoDesatualizada` com `versao_atual` no corpo.
- **Barreira 2 (banco):** `version_id_col` do SQLAlchemy. O UPDATE sai como
  `... WHERE id = :id AND versao = :lida` e incrementa a versão. Se outra transação salvou entre
  o SELECT e o UPDATE, nenhuma linha é afetada, o SQLAlchemy levanta `StaleDataError` e a API
  responde 409.

### 3. Agenda atualizada → polling de 30 s

- A tela de agenda refaz o `GET` a cada **30 s**, **só com a aba visível**
  (`document.visibilityState`), e atualiza na hora quando o usuário volta para a aba.
- A agenda pode ficar até 30 s atrasada, e isso é **aceitável** porque a correção não depende
  dela. Se alguém tentar reservar um horário que acabou de ser ocupado, o banco recusa e o site
  mostra "Sala ocupada nesse horário".

### Decisões menores registradas

- A edição revalida **período, sala ativa e conflito** só quando a sala ou o horário mudam.
  Corrigir só a finalidade de uma reserva numa sala que foi desativada depois continua permitido.
- O cancelamento não exige `versao`. Ele depende só do estado (`ativa` e ainda não iniciada) e
  continua protegido pelo `version_id_col` contra uma edição simultânea.
- Desativar uma sala **não** cancela as reservas que ela já tem (requisito). Só bloqueia as novas.

## Alternativas rejeitadas

| Alternativa | Motivo da rejeição |
| --- | --- |
| **Só `SELECT` antes do `INSERT`** | Tem condição de corrida. O teste `test_sem_checagem_previa...` prova isso: com a constraint removida, **10 de 10** requisições simultâneas gravaram reserva. |
| **`SELECT ... FOR UPDATE` na sala** | Funciona, mas serializa **todas** as reservas da sala (inclusive em horários diferentes), e qualquer caminho de código que esqueça o lock reabre a falha. A constraint vale para qualquer INSERT/UPDATE, até um feito pelo `psql`. |
| **Isolamento `SERIALIZABLE`** | Também resolve, mas gera falhas de serialização genéricas (40001) que precisam de retentativa, e a mensagem "sala ocupada" vira "tente de novo". |
| **Tabela de "slots"** (uma linha por sala e intervalo de 15 min, com `UNIQUE`) | Força uma granularidade fixa, multiplica linhas (32 por sala por dia útil) e complica reservas de duração livre. |
| **Lock pessimista na edição** (marcar a reserva como "em edição") | Uma aba esquecida aberta trava a reserva para todo mundo e exige expiração de locks. O conflito real de edição é raro, e o otimista só custa algo quando ele acontece. |
| **WebSocket** | Exige conexão persistente, reconexão, autenticação no canal e cuidado com vários workers (pub/sub, normalmente via Redis, que está fora do escopo). Para uma agenda que muda poucas vezes por hora, é infraestrutura demais. |
| **SSE (Server-Sent Events)** | É mais simples que WebSocket, mas ainda prende uma conexão por aba e, com vários workers, também precisa de um barramento de eventos. Fica como próximo passo natural (ver gatilhos). |
| **Long polling** | Tem a complexidade de manter requisições penduradas, com pouco ganho sobre polling curto nesta escala. |

## Consequências

**Boas**
- A integridade não depende da disciplina do código: nenhuma rota, script ou `psql` consegue
  gravar sobreposição. O teste de concorrência (`tests/test_concorrencia.py`) dispara 2 e 10
  requisições simultâneas e confere **exatamente 1** reserva gravada.
- O lost update vira um 409 explícito, e o front recarrega e pede para o usuário conferir.
- O polling é HTTP comum: funciona atrás de qualquer proxy, sem estado no servidor, com o mesmo
  JWT e os mesmos logs.

**Ruins**
- Depende de recursos específicos do PostgreSQL (`btree_gist`, `EXCLUDE`, `tstzrange`). Trocar
  de banco exigiria outra solução.
- Custo do polling, estimado: com **30** pessoas com a agenda aberta, são 2 requisições
  (salas + reservas) a cada 30 s, ou seja, **2 req/s**. Com 300 pessoas, 20 req/s. A medição
  da QA-2 mostrou cerca de 150 req/s num único worker de desenvolvimento.
- A agenda pode ficar até 30 s atrasada.

## Gatilhos de revisão

1. Mais de **500 pessoas** com a agenda aberta ao mesmo tempo (mais de **33 req/s** só de
   polling) → avaliar **SSE** com `LISTEN/NOTIFY` do PostgreSQL.
2. Mais de **5%** das tentativas de reserva terminando em 409 de conflito (medido pelo evento
   `reserva.conflito` nos logs) → sinal de que a agenda atrasada está atrapalhando: reduzir o
   intervalo ou ir para push.
3. `GET /v1/reservas` da agenda com **p95 > 300 ms** → índice por `(inicio)` e cache HTTP
   (`ETag`) antes de pensar em push.
4. Notificações em tempo real entrarem no escopo (hoje fora) → reavaliar WebSocket/SSE junto.
