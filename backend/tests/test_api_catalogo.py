"""Recursos (N:N com salas), catálogo de salas com busca/filtro/paginação
e cadastro público."""

import pytest
from fastapi.testclient import TestClient

PROBLEMA = "application/problem+json"


@pytest.fixture
def recursos(client: TestClient, admin) -> dict[str, int]:
    ids = {}
    for nome in ("Projetor", "TV", "Videoconferência"):
        r = client.post("/v1/recursos", json={"nome": nome}, headers=admin.headers)
        assert r.status_code == 201
        ids[nome] = r.json()["id"]
    return ids


def criar_sala(client, admin, nome, capacidade=6, recurso_ids=(), **extra):
    corpo = {"nome": nome, "capacidade": capacidade, "recurso_ids": list(recurso_ids), **extra}
    r = client.post("/v1/salas", json=corpo, headers=admin.headers)
    assert r.status_code == 201, r.text
    return r.json()


# ------------------------------------------------------------------ recursos
def test_admin_cria_recurso_com_201_e_location(client, admin) -> None:
    r = client.post(
        "/v1/recursos", json={"nome": "Projetor", "descricao": "Full HD"}, headers=admin.headers
    )
    assert r.status_code == 201
    assert r.headers["Location"] == f"/v1/recursos/{r.json()['id']}"
    assert r.json()["ativo"] is True


def test_nome_de_recurso_duplicado_retorna_409(client, admin, recursos) -> None:
    r = client.post("/v1/recursos", json={"nome": "Projetor"}, headers=admin.headers)
    assert r.status_code == 409
    assert r.json()["type"] == "/problemas/ja-existe"


def test_colaborador_lista_e_le_recursos(client, colaborador, recursos) -> None:
    r = client.get("/v1/recursos", headers=colaborador.headers)
    assert r.status_code == 200
    assert [x["nome"] for x in r.json()] == ["Projetor", "TV", "Videoconferência"]
    assert r.headers["X-Total-Count"] == "3"
    um = client.get(f"/v1/recursos/{recursos['TV']}", headers=colaborador.headers)
    assert um.json()["nome"] == "TV"


def test_recursos_sem_token_retorna_401(client) -> None:
    assert client.get("/v1/recursos").status_code == 401


def test_recurso_inexistente_retorna_404(client, colaborador) -> None:
    r = client.get("/v1/recursos/999", headers=colaborador.headers)
    assert r.status_code == 404
    assert r.headers["content-type"] == PROBLEMA


def test_admin_edita_e_desativa_recurso_e_a_sala_continua_com_ele(client, admin, recursos) -> None:
    sala = criar_sala(client, admin, "Sala Azul", recurso_ids=[recursos["TV"]])
    url = f"/v1/recursos/{recursos['TV']}"
    r = client.patch(url, json={"nome": "TV 55 polegadas"}, headers=admin.headers)
    assert r.json()["nome"] == "TV 55 polegadas"
    r = client.patch(url, json={"ativo": False}, headers=admin.headers)
    assert r.json()["ativo"] is False

    ativos = client.get("/v1/recursos", params={"ativos": "true"}, headers=admin.headers).json()
    assert recursos["TV"] not in [x["id"] for x in ativos]
    lida = client.get(f"/v1/salas/{sala['id']}", headers=admin.headers).json()
    assert [x["id"] for x in lida["recursos"]] == [recursos["TV"]]


# ------------------------------------------------------- sala <-> recurso (N:N)
def test_sala_criada_com_recursos_mostra_os_recursos(client, admin, recursos) -> None:
    sala = criar_sala(
        client, admin, "Sala Azul", recurso_ids=[recursos["TV"], recursos["Projetor"]]
    )
    assert [x["nome"] for x in sala["recursos"]] == ["Projetor", "TV"]  # ordem alfabética


def test_recurso_ids_repetidos_contam_uma_vez(client, admin, recursos) -> None:
    sala = criar_sala(client, admin, "Sala Azul", recurso_ids=[recursos["TV"]] * 3)
    assert len(sala["recursos"]) == 1


def test_patch_com_recurso_ids_substitui_a_lista(client, admin, recursos) -> None:
    sala = criar_sala(client, admin, "Sala Azul", recurso_ids=[recursos["TV"], recursos["Projetor"]])
    url = f"/v1/salas/{sala['id']}"
    r = client.patch(url, json={"recurso_ids": [recursos["Videoconferência"]]}, headers=admin.headers)
    assert [x["nome"] for x in r.json()["recursos"]] == ["Videoconferência"]

    # PATCH sem recurso_ids não mexe nos recursos.
    r = client.patch(url, json={"capacidade": 9}, headers=admin.headers)
    assert [x["nome"] for x in r.json()["recursos"]] == ["Videoconferência"]

    r = client.patch(url, json={"recurso_ids": []}, headers=admin.headers)
    assert r.json()["recursos"] == []


def test_sala_com_recurso_inexistente_retorna_422_e_nao_grava(client, admin, db) -> None:
    from app.models.sala import Sala

    r = client.post(
        "/v1/salas", json={"nome": "X", "capacidade": 2, "recurso_ids": [999]}, headers=admin.headers
    )
    assert r.status_code == 422
    assert r.json()["type"] == "/problemas/recurso-invalido"
    assert db.query(Sala).count() == 0


def test_recurso_desativado_nao_entra_em_sala_nova(client, admin, recursos) -> None:
    client.patch(f"/v1/recursos/{recursos['TV']}", json={"ativo": False}, headers=admin.headers)
    r = client.post(
        "/v1/salas",
        json={"nome": "X", "capacidade": 2, "recurso_ids": [recursos["TV"]]},
        headers=admin.headers,
    )
    assert r.status_code == 422


def test_sala_mantem_recurso_desativado_ao_ser_editada(client, admin, recursos) -> None:
    sala = criar_sala(client, admin, "Sala Azul", recurso_ids=[recursos["TV"]])
    client.patch(f"/v1/recursos/{recursos['TV']}", json={"ativo": False}, headers=admin.headers)
    r = client.patch(
        f"/v1/salas/{sala['id']}",
        json={"recurso_ids": [recursos["TV"], recursos["Projetor"]]},
        headers=admin.headers,
    )
    assert r.status_code == 200
    assert len(r.json()["recursos"]) == 2


def test_alterar_recursos_da_sala_gera_auditoria(client, admin, responsavel, recursos) -> None:
    sala = criar_sala(client, admin, "Sala Azul")
    client.patch(
        f"/v1/salas/{sala['id']}", json={"recurso_ids": [recursos["TV"]]}, headers=admin.headers
    )
    eventos = client.get(
        "/v1/auditoria",
        params={"entidade": "sala", "entidade_id": sala["id"]},
        headers=responsavel.headers,
    ).json()
    editado = next(e for e in eventos if e["tipo"] == "sala.editada")
    assert editado["dados"]["antes"]["recurso_ids"] == []
    assert editado["dados"]["depois"]["recurso_ids"] == [recursos["TV"]]


# ------------------------------------------- catálogo: busca, filtro, paginação
@pytest.fixture
def catalogo(client, admin, recursos) -> None:
    criar_sala(client, admin, "Sala Azul", 6, [recursos["TV"]], localizacao="2º andar")
    criar_sala(client, admin, "Sala Verde", 4, [], localizacao="2º andar")
    criar_sala(client, admin, "Auditório", 40, [recursos["Projetor"]], localizacao="Térreo")
    criar_sala(
        client, admin, "Sala Laranja", 10,
        [recursos["Videoconferência"], recursos["TV"]], localizacao="3º andar",
    )
    criar_sala(client, admin, "Sala Azul Clara", 2, [], localizacao="Térreo")


def nomes(r) -> list[str]:
    return [s["nome"] for s in r.json()]


def test_busca_por_parte_do_nome_sem_diferenciar_maiusculas(client, colaborador, catalogo) -> None:
    r = client.get("/v1/salas", params={"busca": "AZUL"}, headers=colaborador.headers)
    assert nomes(r) == ["Sala Azul", "Sala Azul Clara"]
    assert r.headers["X-Total-Count"] == "2"


def test_busca_tambem_olha_a_localizacao(client, colaborador, catalogo) -> None:
    r = client.get("/v1/salas", params={"busca": "térreo"}, headers=colaborador.headers)
    assert nomes(r) == ["Auditório", "Sala Azul Clara"]


def test_busca_com_curinga_do_like_e_texto_literal(client, colaborador, catalogo) -> None:
    r = client.get("/v1/salas", params={"busca": "%"}, headers=colaborador.headers)
    assert r.status_code == 200
    assert r.json() == []


def test_filtro_por_recurso_exige_todos_os_recursos(client, colaborador, recursos, catalogo) -> None:
    so_tv = client.get("/v1/salas", params={"recurso": recursos["TV"]}, headers=colaborador.headers)
    assert nomes(so_tv) == ["Sala Azul", "Sala Laranja"]
    tv_e_video = client.get(
        "/v1/salas",
        params=[("recurso", recursos["TV"]), ("recurso", recursos["Videoconferência"])],
        headers=colaborador.headers,
    )
    assert nomes(tv_e_video) == ["Sala Laranja"]


def test_filtro_por_capacidade_minima(client, colaborador, catalogo) -> None:
    r = client.get("/v1/salas", params={"capacidade_minima": 6}, headers=colaborador.headers)
    assert nomes(r) == ["Auditório", "Sala Azul", "Sala Laranja"]


def test_paginacao_com_total_no_cabecalho(client, colaborador, catalogo) -> None:
    pag1 = client.get("/v1/salas", params={"limit": 2, "offset": 0}, headers=colaborador.headers)
    pag2 = client.get("/v1/salas", params={"limit": 2, "offset": 2}, headers=colaborador.headers)
    pag3 = client.get("/v1/salas", params={"limit": 2, "offset": 4}, headers=colaborador.headers)
    assert nomes(pag1) == ["Auditório", "Sala Azul"]
    assert nomes(pag2) == ["Sala Azul Clara", "Sala Laranja"]
    assert nomes(pag3) == ["Sala Verde"]
    assert pag1.headers["X-Total-Count"] == pag3.headers["X-Total-Count"] == "5"


def test_total_respeita_os_filtros(client, colaborador, catalogo) -> None:
    r = client.get(
        "/v1/salas", params={"busca": "sala", "limit": 1}, headers=colaborador.headers
    )
    assert len(r.json()) == 1
    assert r.headers["X-Total-Count"] == "4"


def test_total_pode_ser_lido_pelo_navegador_via_cors(client, colaborador) -> None:
    from app.core.config import settings

    origem = settings.cors_origins[0]
    r = client.get("/v1/salas", headers={**colaborador.headers, "Origin": origem})
    assert "X-Total-Count" in r.headers["access-control-expose-headers"]


def test_usuarios_com_busca_filtro_de_papel_e_total(client, admin, criar_pessoa) -> None:
    criar_pessoa("colaborador", nome="Ana Souza")
    criar_pessoa("colaborador", nome="Bruno Lima")
    criar_pessoa("responsavel", nome="Rita Ana")
    r = client.get("/v1/usuarios", params={"busca": "ana"}, headers=admin.headers)
    assert sorted(u["nome"] for u in r.json()) == ["Ana Souza", "Rita Ana"]
    assert r.headers["X-Total-Count"] == "2"
    r = client.get("/v1/usuarios", params={"papel": "colaborador"}, headers=admin.headers)
    assert sorted(u["nome"] for u in r.json()) == ["Ana Souza", "Bruno Lima"]


def test_reservas_com_busca_na_finalidade_e_total(client, colaborador, reservar) -> None:
    from tests.conftest import horario

    reservar(colaborador, horario(9), horario(10), finalidade="Daily do time")
    reservar(colaborador, horario(10), horario(11), finalidade="Revisão de código")
    r = client.get("/v1/reservas", params={"busca": "daily"}, headers=colaborador.headers)
    assert [x["finalidade"] for x in r.json()] == ["Daily do time"]
    assert r.headers["X-Total-Count"] == "1"


# ------------------------------------------------------------ cadastro público
def test_registro_publico_cria_colaborador_que_consegue_logar(client) -> None:
    r = client.post(
        "/v1/auth/registro",
        json={"email": " Nova@Empresa.com ", "nome": "Nova Pessoa", "senha": "senha-forte-123"},
    )
    assert r.status_code == 201
    assert r.headers["Location"] == "/v1/auth/me"
    assert r.json()["email"] == "nova@empresa.com"
    assert r.json()["papel"] == "colaborador"
    assert "senha" not in r.json() and "hashed_password" not in r.json()

    login = client.post(
        "/v1/auth/login", data={"username": "nova@empresa.com", "password": "senha-forte-123"}
    )
    assert login.status_code == 200


def test_registro_nao_aceita_escolher_o_papel(client, db) -> None:
    from app.models.user import User

    r = client.post(
        "/v1/auth/registro",
        json={"email": "x@empresa.com", "nome": "X", "senha": "senha-forte-123", "papel": "admin"},
    )
    assert r.status_code == 422
    assert db.query(User).count() == 0


def test_registro_com_email_ja_usado_retorna_409(client, colaborador) -> None:
    r = client.post(
        "/v1/auth/registro",
        json={"email": colaborador.email, "nome": "Repetido", "senha": "senha-forte-123"},
    )
    assert r.status_code == 409


@pytest.mark.parametrize(
    "corpo",
    [
        {"email": "nao-e-email", "nome": "X", "senha": "senha-forte-123"},
        {"email": "x@empresa.com", "nome": "X", "senha": "curta"},
        {"email": "x@empresa.com", "senha": "senha-forte-123"},
    ],
)
def test_registro_com_dados_invalidos_retorna_422(client, corpo) -> None:
    assert client.post("/v1/auth/registro", json=corpo).status_code == 422


def test_registro_fica_na_auditoria_feito_pela_propria_pessoa(client, responsavel) -> None:
    r = client.post(
        "/v1/auth/registro",
        json={"email": "nova@empresa.com", "nome": "Nova", "senha": "senha-forte-123"},
    )
    novo_id = r.json()["id"]
    eventos = client.get(
        "/v1/auditoria",
        params={"entidade": "usuario", "entidade_id": novo_id},
        headers=responsavel.headers,
    ).json()
    assert [(e["tipo"], e["usuario_id"]) for e in eventos] == [("usuario.registrado", novo_id)]


# ------------------------------------------------------------------- Swagger
def test_swagger_tem_exemplos_nas_rotas_principais(client) -> None:
    schemas = client.get("/openapi.json").json()["components"]["schemas"]
    for nome in ("ReservaCriar", "SalaCriar", "RecursoCriar", "UsuarioRegistro", "UsuarioCriar"):
        assert schemas[nome].get("examples"), nome
