"""Testes de concorrência: o cenário que a checagem com SELECT não resolve.

Várias requisições disparadas AO MESMO TEMPO (threads + Barrier) para a
mesma sala e horário. Exatamente uma pode vencer.

O teste mais forte DESLIGA a checagem prévia do serviço (monkeypatch): assim
todas as requisições "acham" a sala livre, como aconteceria numa corrida
real, e a ÚNICA proteção que sobra é a constraint de exclusão do banco.
"""

import threading
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.models.reserva import Reserva
from app.servicos import reservas as servico_reservas
from tests.conftest import horario


def disparar_juntas(n: int, acao: Callable[[TestClient], int]) -> list[int]:
    """Roda `acao` em n threads que largam juntas (Barrier); devolve os status."""
    from app.main import app

    largada = threading.Barrier(n)
    resultados: list[int] = []
    trava = threading.Lock()

    def trabalho() -> None:
        client = TestClient(app)  # um cliente por thread
        largada.wait()  # todas esperam aqui e saem ao mesmo tempo
        status = acao(client)
        with trava:
            resultados.append(status)

    threads = [threading.Thread(target=trabalho) for _ in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    return resultados


def _corpo(sala: int) -> dict:
    return {"sala_id": sala, "inicio": horario(10), "fim": horario(11), "finalidade": "Corrida"}


def test_duas_reservas_simultaneas_exatamente_uma_vence(db, sala, colaborador) -> None:
    status = disparar_juntas(
        2,
        lambda c: c.post("/v1/reservas", json=_corpo(sala), headers=colaborador.headers).status_code,
    )
    assert sorted(status) == [201, 409]
    assert db.scalar(select(func.count()).select_from(Reserva)) == 1


@pytest.mark.parametrize("n", [2, 10])
def test_sem_checagem_previa_a_constraint_do_banco_garante_sozinha(
    db, sala, colaborador, monkeypatch, n
) -> None:
    # Simula a corrida no pior caso: TODAS passam pela checagem com SELECT.
    monkeypatch.setattr(servico_reservas, "_checar_conflito", lambda *a, **k: None)

    status = disparar_juntas(
        n,
        lambda c: c.post("/v1/reservas", json=_corpo(sala), headers=colaborador.headers).status_code,
    )
    assert status.count(201) == 1
    assert status.count(409) == n - 1
    assert db.scalar(select(func.count()).select_from(Reserva)) == 1


def test_edicoes_simultaneas_com_a_mesma_versao_so_uma_vence(
    client, db, sala, colaborador, monkeypatch
) -> None:
    """Lost update: duas pessoas leram a versão 1 e salvam juntas. Mesmo
    desligando a comparação de versão do serviço, o UPDATE ... WHERE
    versao = 1 (version_id_col) deixa só uma vencer."""
    reserva_id = client.post(
        "/v1/reservas", json=_corpo(sala), headers=colaborador.headers
    ).json()["id"]
    monkeypatch.setattr(servico_reservas, "verificar_versao", lambda *a, **k: None)

    status = disparar_juntas(
        2,
        lambda c: c.patch(
            f"/v1/reservas/{reserva_id}",
            json={"versao": 1, "finalidade": f"Edição {threading.get_ident()}"},
            headers=colaborador.headers,
        ).status_code,
    )
    assert sorted(status) == [200, 409]
    db.expire_all()
    assert db.get(Reserva, reserva_id).versao == 2
