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


@pytest.fixture(scope="session", autouse=True)
def banco_de_teste_migrado() -> None:
    """Uma vez por execução do pytest: cria o banco de teste e aplica as
    migrations de verdade (as mesmas da produção, não um create_all)."""
    assert NOME_BANCO_TESTE.endswith("_test"), "Recusando rodar fora do banco de teste"
    _criar_banco_de_teste_se_preciso()
    command.upgrade(alembic_config(), "head")
