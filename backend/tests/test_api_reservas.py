"""Testes de API das reservas: HTTP de verdade (TestClient) contra o banco
de TESTE migrado com Alembic. Cada teste começa com o banco vazio."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.models.evento_auditoria import EventoAuditoria
from app.models.reserva import Reserva
from app.models.sala import Sala
from tests.conftest import horario

PROBLEMA = "application/problem+json"


# ------------------------------------------------------------- criar reserva
def test_criar_reserva_retorna_201_com_location(client, colaborador, reservar) -> None:
    r = reservar(colaborador, horario(10), horario(11))

    assert r.status_code == 201
    corpo = r.json()
    assert r.headers["Location"] == f"/v1/reservas/{corpo['id']}"
    # O Location aponta para um recurso que existe de verdade.
    assert client.get(r.headers["Location"], headers=colaborador.headers).status_code == 200
    # Dono vem do token; datas voltam em UTC; versão começa em 1.
    assert corpo["usuario_id"] == colaborador.id
    assert corpo["usuario"]["id"] == colaborador.id
    assert corpo["inicio"].endswith("Z")
    assert corpo["status"] == "ativa"
    assert corpo["versao"] == 1
    assert r.headers["X-Request-ID"]


def test_sobreposicao_retorna_409(colaborador, outro_colaborador, reservar) -> None:
    primeira = reservar(colaborador, horario(10), horario(11))
    r = reservar(outro_colaborador, horario(10, 30), horario(11, 30))

    assert r.status_code == 409
    assert r.headers["content-type"] == PROBLEMA
    problema = r.json()
    assert problema["type"] == "/problemas/conflito-de-horario"
    assert "ocupada" in problema["detail"]
    assert problema["reservas_conflitantes"] == [primeira.json()["id"]]


def test_reservas_encostadas_retornam_201(colaborador, reservar) -> None:
    assert reservar(colaborador, horario(10), horario(11)).status_code == 201
    # Começa exatamente quando a outra termina: intervalo [inicio, fim).
    assert reservar(colaborador, horario(11), horario(12)).status_code == 201
    # E uma que termina exatamente quando a primeira começa.
    assert reservar(colaborador, horario(9), horario(10)).status_code == 201


def test_mesmo_horario_em_salas_diferentes_e_permitido(db, colaborador, reservar) -> None:
    outra = Sala(nome="Sala Verde", capacidade=4)
    db.add(outra)
    db.commit()
    assert reservar(colaborador, horario(10), horario(11)).status_code == 201
    assert reservar(colaborador, horario(10), horario(11), sala_id=outra.id).status_code == 201


def test_data_sem_fuso_retorna_422(colaborador, reservar) -> None:
    sem_fuso = horario(10)[:19]  # corta o "-03:00"
    r = reservar(colaborador, sem_fuso, horario(11))

    assert r.status_code == 422
    assert r.headers["content-type"] == PROBLEMA
    erros = r.json()["erros"]
    assert [e["campo"] for e in erros] == ["inicio"]
    assert "fuso" in erros[0]["mensagem"]


def test_campo_extra_retorna_422(colaborador, outro_colaborador, reservar) -> None:
    # Tentar reservar em nome de outra pessoa: o campo nem é aceito.
    r = reservar(colaborador, horario(10), horario(11), usuario_id=outro_colaborador.id)

    assert r.status_code == 422
    assert r.json()["erros"][0]["campo"] == "usuario_id"


def test_periodo_invalido_retorna_422(colaborador, reservar) -> None:
    curta = reservar(colaborador, horario(10), horario(10, 10))
    invertida = reservar(colaborador, horario(11), horario(10))
    passado = reservar(colaborador, horario(10, dias=-1), horario(11, dias=-1))

    for r in (curta, invertida, passado):
        assert r.status_code == 422
        assert r.json()["type"] == "/problemas/periodo-invalido"


def test_json_ilegivel_retorna_400(client, colaborador) -> None:
    r = client.post(
        "/v1/reservas",
        content=b'{"sala_id": ',
        headers={**colaborador.headers, "Content-Type": "application/json"},
    )
    assert r.status_code == 400
    assert r.json()["type"] == "/problemas/corpo-ilegivel"


def test_sala_inativa_retorna_409(db, sala, colaborador, reservar) -> None:
    db.get(Sala, sala).ativa = False
    db.commit()

    r = reservar(colaborador, horario(10), horario(11))
    assert r.status_code == 409
    assert r.json()["type"] == "/problemas/sala-inativa"


def test_sala_inexistente_retorna_404(colaborador, reservar) -> None:
    r = reservar(colaborador, horario(10), horario(11), sala_id=999)
    assert r.status_code == 404


def test_sem_token_retorna_401(client) -> None:
    r = client.get("/v1/reservas")
    assert r.status_code == 401
    assert r.headers["WWW-Authenticate"] == "Bearer"
    assert r.headers["content-type"] == PROBLEMA


def test_desativar_sala_nao_apaga_reservas_existentes(
    client, db, admin, colaborador, reservar, sala
) -> None:
    reserva_id = reservar(colaborador, horario(10), horario(11)).json()["id"]
    r = client.patch(f"/v1/salas/{sala}", json={"ativa": False}, headers=admin.headers)
    assert r.status_code == 200
    reserva = client.get(f"/v1/reservas/{reserva_id}", headers=colaborador.headers).json()
    assert reserva["status"] == "ativa"


# ------------------------------------------------------------------ cancelar
def test_cancelar_libera_o_horario(client, colaborador, outro_colaborador, reservar) -> None:
    reserva_id = reservar(colaborador, horario(10), horario(11)).json()["id"]
    assert reservar(outro_colaborador, horario(10), horario(11)).status_code == 409

    r = client.post(f"/v1/reservas/{reserva_id}/cancelamento", headers=colaborador.headers)
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["status"] == "cancelada"
    assert corpo["cancelado_por_id"] == colaborador.id
    assert corpo["cancelado_em"] is not None

    # O horário voltou a ficar livre...
    assert reservar(outro_colaborador, horario(10), horario(11)).status_code == 201
    # ...e a reserva cancelada continua existindo (histórico, não DELETE).
    antiga = client.get(f"/v1/reservas/{reserva_id}", headers=colaborador.headers)
    assert antiga.json()["status"] == "cancelada"


def test_cancelar_duas_vezes_retorna_409(client, colaborador, reservar) -> None:
    reserva_id = reservar(colaborador, horario(10), horario(11)).json()["id"]
    url = f"/v1/reservas/{reserva_id}/cancelamento"
    assert client.post(url, headers=colaborador.headers).status_code == 200

    r = client.post(url, headers=colaborador.headers)
    assert r.status_code == 409
    assert r.json()["type"] == "/problemas/reserva-nao-alteravel"


def test_reserva_ja_iniciada_nao_pode_ser_cancelada_nem_editada(
    client, db, sala, colaborador
) -> None:
    # A API não deixa criar reserva no passado, então montamos direto no banco.
    agora = datetime.now(UTC)
    reserva = Reserva(
        sala_id=sala,
        usuario_id=colaborador.id,
        inicio=agora - timedelta(minutes=30),
        fim=agora + timedelta(minutes=30),
        finalidade="Em andamento",
    )
    db.add(reserva)
    db.commit()

    r1 = client.post(f"/v1/reservas/{reserva.id}/cancelamento", headers=colaborador.headers)
    r2 = client.patch(
        f"/v1/reservas/{reserva.id}",
        json={"versao": 1, "finalidade": "x"},
        headers=colaborador.headers,
    )
    for r in (r1, r2):
        assert r.status_code == 409
        assert "começou" in r.json()["detail"]


# --------------------------------------------------------------- permissões
def test_colaborador_alterando_reserva_alheia_recebe_403_e_responsavel_consegue(
    client, colaborador, outro_colaborador, responsavel, reservar
) -> None:
    reserva_id = reservar(colaborador, horario(10), horario(11)).json()["id"]
    url = f"/v1/reservas/{reserva_id}"

    r = client.patch(url, json={"versao": 1, "finalidade": "x"}, headers=outro_colaborador.headers)
    assert r.status_code == 403
    assert r.json()["type"] == "/problemas/acesso-negado"
    r = client.post(f"{url}/cancelamento", headers=outro_colaborador.headers)
    assert r.status_code == 403

    r = client.patch(url, json={"versao": 1, "finalidade": "Ajustada"}, headers=responsavel.headers)
    assert r.status_code == 200
    assert r.json()["finalidade"] == "Ajustada"
    r = client.post(f"{url}/cancelamento", headers=responsavel.headers)
    assert r.status_code == 200
    assert r.json()["cancelado_por_id"] == responsavel.id


def test_admin_tambem_altera_reserva_alheia(client, colaborador, admin, reservar) -> None:
    reserva_id = reservar(colaborador, horario(10), horario(11)).json()["id"]
    r = client.post(f"/v1/reservas/{reserva_id}/cancelamento", headers=admin.headers)
    assert r.status_code == 200


def test_acesso_negado_fica_registrado_na_auditoria(
    client, db, colaborador, outro_colaborador, reservar
) -> None:
    reserva_id = reservar(colaborador, horario(10), horario(11)).json()["id"]
    client.post(f"/v1/reservas/{reserva_id}/cancelamento", headers=outro_colaborador.headers)

    evento = db.scalar(
        select(EventoAuditoria).where(EventoAuditoria.tipo == "reserva.acesso_negado")
    )
    assert evento is not None
    assert evento.usuario_id == outro_colaborador.id
    assert evento.entidade_id == reserva_id
    assert evento.dados["acao"] == "cancelar"


# ------------------------------------------------- editar + locking otimista
def test_editar_incrementa_a_versao(client, colaborador, reservar) -> None:
    reserva_id = reservar(colaborador, horario(10), horario(11)).json()["id"]
    r = client.patch(
        f"/v1/reservas/{reserva_id}",
        json={"versao": 1, "inicio": horario(14), "fim": horario(15), "finalidade": "Nova"},
        headers=colaborador.headers,
    )
    assert r.status_code == 200
    assert r.json()["versao"] == 2
    assert r.json()["finalidade"] == "Nova"


def test_patch_com_versao_velha_retorna_409(client, colaborador, reservar) -> None:
    reserva_id = reservar(colaborador, horario(10), horario(11)).json()["id"]
    url = f"/v1/reservas/{reserva_id}"
    # Duas abas abertas leram a versão 1. A primeira salva...
    assert client.patch(
        url, json={"versao": 1, "finalidade": "Aba 1"}, headers=colaborador.headers
    ).status_code == 200
    # ...a segunda tenta salvar por cima com a versão que leu antes.
    r = client.patch(url, json={"versao": 1, "finalidade": "Aba 2"}, headers=colaborador.headers)

    assert r.status_code == 409
    assert r.json()["type"] == "/problemas/versao-desatualizada"
    assert r.json()["versao_atual"] == 2
    # A alteração da primeira aba NÃO foi perdida (lost update evitado).
    assert client.get(url, headers=colaborador.headers).json()["finalidade"] == "Aba 1"


def test_patch_sem_versao_retorna_422(client, colaborador, reservar) -> None:
    reserva_id = reservar(colaborador, horario(10), horario(11)).json()["id"]
    r = client.patch(
        f"/v1/reservas/{reserva_id}", json={"finalidade": "x"}, headers=colaborador.headers
    )
    assert r.status_code == 422
    assert r.json()["erros"][0]["campo"] == "versao"


def test_editar_para_horario_ocupado_retorna_409(client, colaborador, reservar) -> None:
    reservar(colaborador, horario(10), horario(11))
    segunda_id = reservar(colaborador, horario(14), horario(15)).json()["id"]
    r = client.patch(
        f"/v1/reservas/{segunda_id}",
        json={"versao": 1, "inicio": horario(10, 30), "fim": horario(11, 30)},
        headers=colaborador.headers,
    )
    assert r.status_code == 409
    assert r.json()["type"] == "/problemas/conflito-de-horario"


def test_editar_a_propria_reserva_para_horario_sobreposto_a_ela_mesma(
    client, colaborador, reservar
) -> None:
    # Esticar 10h-11h para 10h-12h: sobrepõe a SI MESMA, não pode dar conflito.
    reserva_id = reservar(colaborador, horario(10), horario(11)).json()["id"]
    r = client.patch(
        f"/v1/reservas/{reserva_id}",
        json={"versao": 1, "fim": horario(12)},
        headers=colaborador.headers,
    )
    assert r.status_code == 200


# --------------------------------------------------------- agenda / consulta
def test_agenda_filtra_por_data_e_sala_e_ordena_por_inicio(
    client, db, colaborador, outro_colaborador, reservar, sala
) -> None:
    outra = Sala(nome="Sala Verde", capacidade=4)
    db.add(outra)
    db.commit()
    reservar(colaborador, horario(14), horario(15))
    reservar(outro_colaborador, horario(9), horario(10))
    reservar(colaborador, horario(9), horario(10), sala_id=outra.id)
    reservar(colaborador, horario(9), horario(10, dias=2))  # outro dia

    params = {"de": horario(0), "ate": horario(23, 59)}
    todas = client.get("/v1/reservas", params=params, headers=colaborador.headers).json()
    assert len(todas) == 3
    assert [r["inicio"] for r in todas] == sorted(r["inicio"] for r in todas)

    so_azul = client.get(
        "/v1/reservas", params={**params, "sala_id": sala}, headers=colaborador.headers
    ).json()
    assert {r["sala"]["nome"] for r in so_azul} == {"Sala Azul"}

    minhas = client.get(
        "/v1/reservas", params={**params, "minhas": "true"}, headers=colaborador.headers
    ).json()
    assert {r["usuario_id"] for r in minhas} == {colaborador.id}


def test_agenda_vazia_retorna_lista_vazia(client, colaborador) -> None:
    r = client.get(
        "/v1/reservas", params={"de": horario(0), "ate": horario(23)}, headers=colaborador.headers
    )
    assert r.status_code == 200
    assert r.json() == []


def test_disponibilidade_mostra_livres_e_ocupadas(client, db, colaborador, reservar, sala) -> None:
    grande = Sala(nome="Auditório", capacidade=50)
    inativa = Sala(nome="Sala Antiga", capacidade=50, ativa=False)
    db.add_all([grande, inativa])
    db.commit()
    reserva_id = reservar(colaborador, horario(10), horario(11)).json()["id"]

    r = client.get(
        "/v1/disponibilidade",
        params={"inicio": horario(10, 30), "fim": horario(11, 30)},
        headers=colaborador.headers,
    )
    assert r.status_code == 200
    corpo = r.json()
    situacao = {s["sala"]["nome"]: s for s in corpo["salas"]}
    assert set(situacao) == {"Sala Azul", "Auditório"}  # inativa não aparece
    assert situacao["Sala Azul"]["livre"] is False
    assert situacao["Sala Azul"]["reservas_conflitantes"][0]["id"] == reserva_id
    assert situacao["Auditório"]["livre"] is True
    assert corpo["total_livres"] == 1
    assert corpo["mensagem"] is None

    # Ninguém comporta 60 pessoas -> nenhuma livre, com mensagem clara.
    r = client.get(
        "/v1/disponibilidade",
        params={"inicio": horario(10), "fim": horario(11), "capacidade_minima": 60},
        headers=colaborador.headers,
    )
    assert r.json()["total_livres"] == 0
    assert "Nenhuma sala disponível" in r.json()["mensagem"]


# ------------------------------------------------------------------ auditoria
def test_operacoes_gravam_evento_de_auditoria(client, db, colaborador, reservar) -> None:
    r = reservar(colaborador, horario(10), horario(11))
    reserva_id = r.json()["id"]
    client.patch(
        f"/v1/reservas/{reserva_id}", json={"versao": 1, "finalidade": "x"},
        headers=colaborador.headers,
    )
    client.post(f"/v1/reservas/{reserva_id}/cancelamento", headers=colaborador.headers)

    eventos = db.scalars(
        select(EventoAuditoria)
        .where(EventoAuditoria.entidade == "reserva", EventoAuditoria.entidade_id == reserva_id)
        .order_by(EventoAuditoria.id)
    ).all()
    assert [e.tipo for e in eventos] == ["reserva.criada", "reserva.editada", "reserva.cancelada"]
    assert eventos[0].request_id == r.headers["X-Request-ID"]
    assert eventos[1].dados["antes"]["finalidade"] == "Reunião de teste"
    assert eventos[1].dados["depois"]["finalidade"] == "x"


def test_conflito_nao_grava_reserva_nem_evento(db, colaborador, reservar) -> None:
    reservar(colaborador, horario(10), horario(11))
    reservar(colaborador, horario(10), horario(11))

    assert db.scalar(select(func.count()).select_from(Reserva)) == 1
    assert db.scalar(select(func.count()).select_from(EventoAuditoria)) == 1
