"""RBAC das rotas administrativas, salas, usuários, auth e formato de erro."""

import pytest
from fastapi.testclient import TestClient

PROBLEMA = "application/problem+json"


# ----------------------------------------------------------- RBAC (403 / 401)
ROTAS_DE_ADMIN = [
    ("get", "/v1/usuarios", None),
    ("post", "/v1/usuarios", {"email": "x@x.com", "nome": "X", "senha": "senha-forte-123"}),
    ("patch", "/v1/usuarios/1", {"nome": "Y"}),
    ("post", "/v1/salas", {"nome": "Nova", "capacidade": 4}),
    ("patch", "/v1/salas/1", {"ativa": False}),
]


@pytest.mark.parametrize(("metodo", "url", "corpo"), ROTAS_DE_ADMIN)
def test_rotas_de_admin_chamadas_por_colaborador_retornam_403(
    client, colaborador, sala, metodo, url, corpo
) -> None:
    r = client.request(metodo, url, json=corpo, headers=colaborador.headers)
    assert r.status_code == 403
    assert r.headers["content-type"] == PROBLEMA


@pytest.mark.parametrize(("metodo", "url", "corpo"), ROTAS_DE_ADMIN)
def test_rotas_de_admin_chamadas_por_responsavel_retornam_403(
    client, responsavel, sala, metodo, url, corpo
) -> None:
    assert client.request(metodo, url, json=corpo, headers=responsavel.headers).status_code == 403


@pytest.mark.parametrize(("metodo", "url", "corpo"), ROTAS_DE_ADMIN)
def test_rotas_de_admin_sem_token_retornam_401(client, sala, metodo, url, corpo) -> None:
    assert client.request(metodo, url, json=corpo).status_code == 401


def test_auditoria_e_so_para_responsavel_e_admin(client, colaborador, responsavel, admin) -> None:
    assert client.get("/v1/auditoria", headers=colaborador.headers).status_code == 403
    assert client.get("/v1/auditoria", headers=responsavel.headers).status_code == 200
    assert client.get("/v1/auditoria", headers=admin.headers).status_code == 200


def test_token_invalido_retorna_401(client) -> None:
    r = client.get("/v1/auth/me", headers={"Authorization": "Bearer isto-nao-e-um-jwt"})
    assert r.status_code == 401


# --------------------------------------------------------------------- salas
def test_admin_cria_sala_com_201_e_location(client, admin) -> None:
    r = client.post(
        "/v1/salas",
        json={"nome": "Sala Laranja", "capacidade": 6, "localizacao": "3º andar"},
        headers=admin.headers,
    )
    assert r.status_code == 201
    assert r.headers["Location"] == f"/v1/salas/{r.json()['id']}"
    assert r.json()["ativa"] is True


def test_nome_de_sala_duplicado_retorna_409(client, admin, sala) -> None:
    r = client.post("/v1/salas", json={"nome": "Sala Azul", "capacidade": 6}, headers=admin.headers)
    assert r.status_code == 409
    assert r.json()["type"] == "/problemas/ja-existe"


@pytest.mark.parametrize("corpo", [{"nome": "X"}, {"nome": "X", "capacidade": 0}, {"capacidade": 3}])
def test_sala_sem_nome_ou_capacidade_valida_retorna_422(client, admin, corpo) -> None:
    assert client.post("/v1/salas", json=corpo, headers=admin.headers).status_code == 422


def test_listar_salas_ativas(client, db, colaborador, sala) -> None:
    from app.models.sala import Sala

    db.add(Sala(nome="Desativada", capacidade=2, ativa=False))
    db.commit()
    todas = client.get("/v1/salas", headers=colaborador.headers).json()
    ativas = client.get("/v1/salas", params={"ativas": "true"}, headers=colaborador.headers).json()
    assert len(todas) == 2
    assert [s["nome"] for s in ativas] == ["Sala Azul"]


def test_desativar_sala_gera_evento_sala_desativada(client, admin, sala) -> None:
    client.patch(f"/v1/salas/{sala}", json={"ativa": False}, headers=admin.headers)
    eventos = client.get(
        "/v1/auditoria", params={"entidade": "sala", "entidade_id": sala}, headers=admin.headers
    ).json()
    assert eventos[0]["tipo"] == "sala.desativada"


# ------------------------------------------------------------------ usuários
def test_admin_cria_usuario_que_consegue_logar(client, admin) -> None:
    r = client.post(
        "/v1/usuarios",
        json={"email": "Nova@Empresa.com", "nome": "Nova", "senha": "senha-forte-123"},
        headers=admin.headers,
    )
    assert r.status_code == 201
    assert r.headers["Location"] == f"/v1/usuarios/{r.json()['id']}"
    assert r.json()["email"] == "nova@empresa.com"  # normalizado
    assert r.json()["papel"] == "colaborador"  # padrão: menor poder
    assert "senha" not in r.json() and "hashed_password" not in r.json()

    login = client.post(
        "/v1/auth/login", data={"username": "nova@empresa.com", "password": "senha-forte-123"}
    )
    assert login.status_code == 200
    me = client.get(
        "/v1/auth/me", headers={"Authorization": f"Bearer {login.json()['access_token']}"}
    ).json()
    assert me == {"id": r.json()["id"], "nome": "Nova", "email": "nova@empresa.com", "papel": "colaborador"}


def test_email_duplicado_retorna_409(client, admin, colaborador) -> None:
    r = client.post(
        "/v1/usuarios",
        json={"email": colaborador.email, "nome": "Repetido", "senha": "senha-forte-123"},
        headers=admin.headers,
    )
    assert r.status_code == 409


def test_admin_define_papel_e_desativa_usuario(client, admin, colaborador) -> None:
    url = f"/v1/usuarios/{colaborador.id}"
    r = client.patch(url, json={"papel": "responsavel"}, headers=admin.headers)
    assert r.json()["papel"] == "responsavel"

    r = client.patch(url, json={"is_active": False}, headers=admin.headers)
    assert r.json()["is_active"] is False
    # Usuário desativado: o token que ele já tinha deixa de valer.
    assert client.get("/v1/auth/me", headers=colaborador.headers).status_code == 401


def test_admin_nao_pode_se_desativar_nem_tirar_o_proprio_papel(client, admin) -> None:
    url = f"/v1/usuarios/{admin.id}"
    r1 = client.patch(url, json={"is_active": False}, headers=admin.headers)
    r2 = client.patch(url, json={"papel": "colaborador"}, headers=admin.headers)
    for r in (r1, r2):
        assert r.status_code == 409
        assert r.json()["type"] == "/problemas/operacao-proibida"


def test_register_publico_nao_existe_mais(client) -> None:
    r = client.post("/v1/auth/register", json={"email": "a@a.com", "password": "12345678"})
    assert r.status_code in (404, 405)
    assert client.post("/auth/register", json={}).status_code == 404


# ---------------------------------------------------------------------- auth
def test_login_errado_retorna_401_com_mensagem_generica(client, colaborador) -> None:
    errada = client.post("/v1/auth/login", data={"username": colaborador.email, "password": "x"})
    inexistente = client.post("/v1/auth/login", data={"username": "nao@existe.com", "password": "x"})
    assert errada.status_code == inexistente.status_code == 401
    assert errada.json()["detail"] == inexistente.json()["detail"]


# ----------------------------------------------------------- formato de erro
def test_problem_details_tem_os_campos_da_rfc(client) -> None:
    r = client.get("/v1/rota-que-nao-existe")
    assert r.status_code == 404
    assert r.headers["content-type"] == PROBLEMA
    assert set(r.json()) >= {"type", "title", "status", "detail", "instance"}
    assert r.json()["instance"] == "/v1/rota-que-nao-existe"


def test_request_id_do_cliente_e_devolvido(client) -> None:
    r = client.get("/health", headers={"X-Request-ID": "meu-id-123"})
    assert r.headers["X-Request-ID"] == "meu-id-123"


def test_request_id_malicioso_e_substituido(client) -> None:
    r = client.get("/health", headers={"X-Request-ID": "x\" injetado {"})
    assert r.headers["X-Request-ID"] != "x\" injetado {"
    assert len(r.headers["X-Request-ID"]) == 32  # uuid4().hex


def test_erro_inesperado_retorna_500_sem_stack_trace(colaborador) -> None:
    from app.main import app

    def rota_quebrada() -> None:
        raise RuntimeError("detalhe interno secreto")

    app.add_api_route("/v1/_teste/quebra", rota_quebrada)
    try:
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get("/v1/_teste/quebra")
    finally:
        app.router.routes.pop()  # remove a rota de teste

    assert r.status_code == 500
    assert r.headers["content-type"] == PROBLEMA
    assert "secreto" not in r.text and "Traceback" not in r.text
    assert r.json()["request_id"] == r.headers["X-Request-ID"]
