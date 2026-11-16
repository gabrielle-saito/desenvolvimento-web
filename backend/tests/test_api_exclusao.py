"""Exclusão: DELETE é soft delete (desativa e responde 204), e o banco
recusa apagar fisicamente o que tem histórico (FKs com ON DELETE RESTRICT)."""

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from app.models.evento_auditoria import EventoAuditoria
from tests.conftest import horario


def _eventos(db, tipo: str) -> int:
    return db.scalar(
        select(func.count()).select_from(EventoAuditoria).where(EventoAuditoria.tipo == tipo)
    )


# -------------------------------------------------------------------- salas
def test_delete_desativa_a_sala_e_responde_204(
    client, db, admin, colaborador, reservar, sala
) -> None:
    reserva_id = reservar(colaborador, horario(10), horario(11)).json()["id"]

    r = client.delete(f"/v1/salas/{sala}", headers=admin.headers)
    assert r.status_code == 204
    assert r.content == b""
    assert "content-type" not in r.headers

    # Soft delete: a sala continua existindo, só que inativa...
    r = client.get(f"/v1/salas/{sala}", headers=admin.headers)
    assert r.status_code == 200
    assert r.json()["ativa"] is False
    # ...sai do catálogo de salas ativas...
    r = client.get("/v1/salas", params={"ativas": "true"}, headers=colaborador.headers)
    assert r.json() == []
    # ...as reservas dela continuam no histórico...
    r = client.get(f"/v1/reservas/{reserva_id}", headers=colaborador.headers)
    assert r.status_code == 200
    # ...e reservas novas são recusadas.
    assert reservar(colaborador, horario(14), horario(15)).status_code == 409
    assert _eventos(db, "sala.desativada") == 1


def test_delete_de_sala_e_idempotente(client, db, admin, sala) -> None:
    assert client.delete(f"/v1/salas/{sala}", headers=admin.headers).status_code == 204
    assert client.delete(f"/v1/salas/{sala}", headers=admin.headers).status_code == 204
    # Desativar de novo não muda nada: um evento só.
    assert _eventos(db, "sala.desativada") == 1


def test_sala_desativada_pelo_delete_pode_ser_reativada(client, admin, sala) -> None:
    client.delete(f"/v1/salas/{sala}", headers=admin.headers)
    r = client.patch(f"/v1/salas/{sala}", json={"ativa": True}, headers=admin.headers)
    assert r.status_code == 200
    assert r.json()["ativa"] is True


@pytest.mark.parametrize("url", ["/v1/salas/{id}", "/v1/recursos/{id}"])
def test_delete_exige_admin(client, admin, responsavel, colaborador, sala, url) -> None:
    if "recursos" in url:
        alvo = client.post("/v1/recursos", json={"nome": "TV"}, headers=admin.headers).json()["id"]
    else:
        alvo = sala
    url = url.format(id=alvo)

    assert client.delete(url).status_code == 401
    assert client.delete(url, headers=colaborador.headers).status_code == 403
    assert client.delete(url, headers=responsavel.headers).status_code == 403


@pytest.mark.parametrize("url", ["/v1/salas/9999", "/v1/recursos/9999"])
def test_delete_de_inexistente_responde_404(client, admin, url) -> None:
    assert client.delete(url, headers=admin.headers).status_code == 404


# ----------------------------------------------------------------- recursos
def test_delete_desativa_o_recurso_e_a_sala_continua_com_ele(client, db, admin) -> None:
    recurso_id = client.post(
        "/v1/recursos", json={"nome": "Projetor"}, headers=admin.headers
    ).json()["id"]
    sala = client.post(
        "/v1/salas",
        json={"nome": "Auditório", "capacidade": 40, "recurso_ids": [recurso_id]},
        headers=admin.headers,
    ).json()

    r = client.delete(f"/v1/recursos/{recurso_id}", headers=admin.headers)
    assert r.status_code == 204

    assert client.get(f"/v1/recursos/{recurso_id}", headers=admin.headers).json()["ativo"] is False
    r = client.get(f"/v1/salas/{sala['id']}", headers=admin.headers)
    assert [x["id"] for x in r.json()["recursos"]] == [recurso_id]
    assert client.delete(f"/v1/recursos/{recurso_id}", headers=admin.headers).status_code == 204
    assert _eventos(db, "recurso.desativado") == 1


# ------------------------------------------------- chaves estrangeiras no banco
FKS_RESTRICT = {
    "fk_reservas_sala_id_salas",
    "fk_reservas_usuario_id_users",
    "fk_reservas_cancelado_por_id_users",
    "fk_eventos_auditoria_usuario_id_users",
    "fk_sala_recursos_recurso_id_recursos",
}


def test_todas_as_chaves_estrangeiras_tem_acao_de_exclusao_definida(db) -> None:
    # confdeltype: a = NO ACTION (padrão, nada declarado), r = RESTRICT, c = CASCADE
    acoes = dict(
        db.execute(
            text("SELECT conname, confdeltype FROM pg_constraint WHERE contype = 'f'")
        ).all()
    )
    assert "a" not in acoes.values(), acoes
    assert {nome for nome, acao in acoes.items() if acao == "r"} == FKS_RESTRICT
    assert acoes["fk_sala_recursos_sala_id_salas"] == "c"


def test_banco_recusa_apagar_sala_com_reservas(db, colaborador, reservar, sala) -> None:
    reservar(colaborador, horario(10), horario(11))
    with pytest.raises(IntegrityError, match="fk_reservas_sala_id_salas"):
        db.execute(text("DELETE FROM salas WHERE id = :id"), {"id": sala})
    db.rollback()


def test_banco_recusa_apagar_usuario_com_reservas(db, colaborador, reservar) -> None:
    reservar(colaborador, horario(10), horario(11))
    with pytest.raises(IntegrityError, match="fk_"):
        db.execute(text("DELETE FROM users WHERE id = :id"), {"id": colaborador.id})
    db.rollback()
