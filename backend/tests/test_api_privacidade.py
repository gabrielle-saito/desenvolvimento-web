"""Privacidade: o colaborador acessa apenas os próprios dados.

Das reservas de outras pessoas ele vê só a OCUPAÇÃO (sala e horário), o que
basta para escolher outro horário. Quem reservou e a finalidade não saem da
API para ele. Responsável e admin gerenciam as reservas e veem tudo.
"""

from tests.conftest import horario

CAMPOS_PESSOAIS = ("usuario_id", "usuario", "finalidade", "cancelado_por_id")


def _agenda(client, pessoa, **params):
    params = {"de": horario(0), "ate": horario(23, 59), **params}
    r = client.get("/v1/reservas", params=params, headers=pessoa.headers)
    assert r.status_code == 200, r.text
    return r


def _por_id(itens):
    return {item["id"]: item for item in itens}


# ------------------------------------------------------------------- agenda
def test_colaborador_ve_reserva_alheia_so_como_ocupacao(
    client, criar_pessoa, colaborador, reservar
) -> None:
    outra_pessoa = criar_pessoa("colaborador", nome="Fulana Sigilosa")
    alheia = reservar(
        outra_pessoa, horario(9), horario(10), finalidade="Entrevista confidencial"
    ).json()["id"]
    propria = reservar(colaborador, horario(14), horario(15), finalidade="Minha daily").json()["id"]

    r = _agenda(client, colaborador)
    itens = _por_id(r.json())

    # A ocupação aparece: sala e horário.
    assert itens[alheia]["sala"]["nome"] == "Sala Azul"
    assert itens[alheia]["inicio"] and itens[alheia]["fim"]
    assert itens[alheia]["detalhes_ocultos"] is True
    # Os dados pessoais, não.
    for campo in CAMPOS_PESSOAIS:
        assert itens[alheia][campo] is None, campo
    assert "Fulana" not in r.text
    assert "confidencial" not in r.text
    assert outra_pessoa.email not in r.text

    # A própria reserva vem completa.
    assert itens[propria]["detalhes_ocultos"] is False
    assert itens[propria]["finalidade"] == "Minha daily"
    assert itens[propria]["usuario"]["id"] == colaborador.id


def test_responsavel_e_admin_veem_todas_as_reservas_completas(
    client, colaborador, responsavel, admin, reservar
) -> None:
    reservar(colaborador, horario(9), horario(10), finalidade="Planejamento")

    for gestor in (responsavel, admin):
        [item] = _agenda(client, gestor).json()
        assert item["detalhes_ocultos"] is False
        assert item["finalidade"] == "Planejamento"
        assert item["usuario"]["id"] == colaborador.id


def test_colaborador_nao_ve_reservas_canceladas_de_outras_pessoas(
    client, colaborador, outro_colaborador, responsavel, reservar
) -> None:
    alheia = reservar(outro_colaborador, horario(9), horario(10)).json()["id"]
    propria = reservar(colaborador, horario(11), horario(12)).json()["id"]
    for pessoa, reserva_id in ((outro_colaborador, alheia), (colaborador, propria)):
        r = client.post(f"/v1/reservas/{reserva_id}/cancelamento", headers=pessoa.headers)
        assert r.status_code == 200

    # A cancelada alheia não ocupa a sala: não é da conta dele.
    r = _agenda(client, colaborador)
    assert [i["id"] for i in r.json()] == [propria]
    assert r.headers["X-Total-Count"] == "1"
    r = _agenda(client, colaborador, status="cancelada")
    assert [i["id"] for i in r.json()] == [propria]

    # O responsável vê as duas.
    assert {i["id"] for i in _agenda(client, responsavel).json()} == {alheia, propria}


def test_busca_do_colaborador_procura_so_nas_proprias_reservas(
    client, colaborador, outro_colaborador, responsavel, reservar
) -> None:
    reservar(outro_colaborador, horario(9), horario(10), finalidade="Demissão do João")
    reservar(colaborador, horario(11), horario(12), finalidade="Daily")

    # Buscar no texto alheio revelaria o conteúdo ("existe uma reserva sobre
    # demissão"), mesmo com os campos ocultos.
    r = client.get("/v1/reservas", params={"busca": "demiss"}, headers=colaborador.headers)
    assert r.json() == []
    assert r.headers["X-Total-Count"] == "0"

    r = client.get("/v1/reservas", params={"busca": "demiss"}, headers=responsavel.headers)
    assert [i["finalidade"] for i in r.json()] == ["Demissão do João"]


# ------------------------------------------------------------------ detalhe
def test_detalhe_de_reserva_alheia_responde_404_para_colaborador(
    client, colaborador, outro_colaborador, responsavel, admin, reservar
) -> None:
    reserva_id = reservar(colaborador, horario(9), horario(10)).json()["id"]
    url = f"/v1/reservas/{reserva_id}"

    # 404 e não 403: não confirma nem que o id existe.
    r = client.get(url, headers=outro_colaborador.headers)
    assert r.status_code == 404
    assert r.json()["type"] == "/problemas/nao-encontrado"

    for quem_pode in (colaborador, responsavel, admin):
        r = client.get(url, headers=quem_pode.headers)
        assert r.status_code == 200
        assert r.json()["detalhes_ocultos"] is False


def test_responsavel_ao_alterar_reserva_alheia_recebe_ela_completa(
    client, colaborador, responsavel, reservar
) -> None:
    reserva_id = reservar(colaborador, horario(9), horario(10)).json()["id"]
    r = client.post(f"/v1/reservas/{reserva_id}/cancelamento", headers=responsavel.headers)
    assert r.status_code == 200
    assert r.json()["usuario"]["id"] == colaborador.id
    assert r.json()["cancelado_por_id"] == responsavel.id


# ----------------------------------------------------------- disponibilidade
def test_disponibilidade_mostra_ocupacao_sem_dados_pessoais(
    client, colaborador, outro_colaborador, responsavel, reservar
) -> None:
    reservar(outro_colaborador, horario(10), horario(11), finalidade="Assunto pessoal")
    params = {"inicio": horario(10), "fim": horario(11)}

    r = client.get("/v1/disponibilidade", params=params, headers=colaborador.headers)
    [situacao] = r.json()["salas"]
    assert situacao["livre"] is False
    [conflito] = situacao["reservas_conflitantes"]
    assert conflito["detalhes_ocultos"] is True
    assert conflito["usuario"] is None and conflito["finalidade"] is None
    assert "Assunto pessoal" not in r.text

    r = client.get("/v1/disponibilidade", params=params, headers=responsavel.headers)
    [conflito] = r.json()["salas"][0]["reservas_conflitantes"]
    assert conflito["finalidade"] == "Assunto pessoal"
    assert conflito["usuario"]["id"] == outro_colaborador.id
