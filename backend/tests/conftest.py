"""Configuração compartilhada dos testes.

REGRA DE OURO: os testes NUNCA rodam no banco de desenvolvimento.
Este arquivo troca DATABASE_URL para "<banco>_test" ANTES de qualquer
"import app...", porque app.core.config lê a variável no momento do import.
"""

import os

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

_url_dev = make_url(os.environ["DATABASE_URL"])
# Idempotente: se o módulo for importado de novo, não vira "<banco>_test_test".
_base = (_url_dev.database or "").removesuffix("_test")
NOME_BANCO_TESTE = f"{_base}_test"
URL_TESTE = _url_dev.set(database=NOME_BANCO_TESTE)
os.environ["DATABASE_URL"] = URL_TESTE.render_as_string(hide_password=False)

# Daqui para baixo já é seguro importar a aplicação.
import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402


def _criar_banco_de_teste_se_preciso() -> None:
    # CREATE DATABASE não roda dentro de transação: conecta no banco
    # "postgres" (que sempre existe) em modo AUTOCOMMIT.
    engine = create_engine(_url_dev.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        existe = conn.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :nome"),
            {"nome": NOME_BANCO_TESTE},
        )
        if not existe:
            # Nome vem da nossa própria config (não do usuário), mas mesmo assim
            # usamos aspas de identificador.
            conn.execute(text(f'CREATE DATABASE "{NOME_BANCO_TESTE}"'))
    engine.dispose()


def alembic_config() -> Config:
    # O env.py lê DATABASE_URL de app.core.config -> já aponta para o teste.
    return Config("alembic.ini")


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "sem_banco: teste que não precisa limpar o banco")


@pytest.fixture(scope="session", autouse=True)
def banco_de_teste_migrado() -> None:
    """Uma vez por execução do pytest: cria o banco de teste e aplica as
    migrations de verdade (as mesmas da produção, não um create_all)."""
    assert NOME_BANCO_TESTE.endswith("_test"), "Recusando rodar fora do banco de teste"
    _criar_banco_de_teste_se_preciso()
    command.upgrade(alembic_config(), "head")


# =============================================================================
# Fixtures dos testes de API
# =============================================================================
from collections.abc import Callable, Iterator  # noqa: E402
from dataclasses import dataclass  # noqa: E402
from datetime import UTC, datetime, timedelta  # noqa: E402
from zoneinfo import ZoneInfo  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

FUSO_SP = ZoneInfo("America/Sao_Paulo")
TABELAS = "eventos_auditoria, reservas, salas, users"


@pytest.fixture
def db() -> Iterator[Session]:
    """Sessão direta no banco de TESTE, para preparar cenários e conferir
    o resultado (ex.: "só existe 1 reserva no banco")."""
    from app.db.session import SessionLocal

    sessao = SessionLocal()
    try:
        yield sessao
    finally:
        sessao.close()


@pytest.fixture(autouse=True)
def banco_limpo(request: pytest.FixtureRequest) -> Iterator[None]:
    """Cada teste de API começa com o banco vazio. TRUNCATE (e não DELETE):
    é rápido, zera os ids e não dispara o trigger append-only da auditoria."""
    if "sem_banco" in request.keywords:
        yield
        return
    from app.db.session import engine

    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {TABELAS} RESTART IDENTITY CASCADE"))
    yield


@pytest.fixture
def client() -> TestClient:
    from app.main import app

    return TestClient(app)


@dataclass
class Pessoa:
    id: int
    email: str
    papel: str
    headers: dict[str, str]


@pytest.fixture
def criar_pessoa(db: Session) -> Callable[..., Pessoa]:
    """Cria um usuário direto no banco e devolve os headers com o token."""
    from app.core.security import create_access_token, hash_password
    from app.models.user import User

    contador = {"n": 0}

    def _criar(papel: str = "colaborador", nome: str | None = None) -> Pessoa:
        contador["n"] += 1
        email = f"{papel}{contador['n']}@teste.com"
        usuario = User(
            email=email,
            nome=nome or f"{papel.title()} {contador['n']}",
            papel=papel,
            hashed_password=hash_password("senha-forte-123"),
        )
        db.add(usuario)
        db.commit()
        token = create_access_token(str(usuario.id))
        return Pessoa(usuario.id, email, papel, {"Authorization": f"Bearer {token}"})

    return _criar


@pytest.fixture
def colaborador(criar_pessoa) -> Pessoa:
    return criar_pessoa("colaborador")


@pytest.fixture
def outro_colaborador(criar_pessoa) -> Pessoa:
    return criar_pessoa("colaborador")


@pytest.fixture
def responsavel(criar_pessoa) -> Pessoa:
    return criar_pessoa("responsavel")


@pytest.fixture
def admin(criar_pessoa) -> Pessoa:
    return criar_pessoa("admin")


@pytest.fixture
def sala(db: Session) -> int:
    from app.models.sala import Sala

    s = Sala(nome="Sala Azul", capacidade=8, localizacao="2º andar")
    db.add(s)
    db.commit()
    return s.id


def horario(hora: int, minuto: int = 0, dias: int = 1) -> str:
    """ISO 8601 COM fuso de São Paulo, N dias no futuro. Ex.: horario(10)
    -> '2030-01-02T10:00:00-03:00'. Futuro relativo ao relógio real, porque
    a API recusa reservas no passado."""
    base = datetime.now(UTC).astimezone(FUSO_SP) + timedelta(days=dias)
    return base.replace(hour=hora, minute=minuto, second=0, microsecond=0).isoformat()


@pytest.fixture
def reservar(client: TestClient, sala: int) -> Callable[..., object]:
    def _reservar(pessoa: Pessoa, inicio: str, fim: str, sala_id: int | None = None, **extra):
        corpo = {
            "sala_id": sala_id or sala,
            "inicio": inicio,
            "fim": fim,
            "finalidade": "Reunião de teste",
            **extra,
        }
        return client.post("/v1/reservas", json=corpo, headers=pessoa.headers)

    return _reservar
