"""Fitness function de arquitetura: o núcleo de domínio continua PURO?

Lê o código-fonte de app/dominio com o módulo ast (sem executá-lo) e falha
se algum arquivo:
  - importar framework/infra (fastapi, sqlalchemy, pydantic) ou camadas de
    fora (app.api, app.db, app.models, app.repositorios, ...);
  - consultar o relógio (datetime.now / utcnow / date.today / time.time).

Se esta regra quebrar, o domínio passa a depender de detalhes e deixa de
ser testável sem banco/HTTP. O teste transforma a decisão do ADR-001 em
algo verificado a cada execução, não só escrito num documento.
"""

import ast
from pathlib import Path

import pytest

PASTA_DOMINIO = Path(__file__).resolve().parents[1] / "app" / "dominio"

IMPORTS_PROIBIDOS = (
    "fastapi",
    "starlette",
    "sqlalchemy",
    "pydantic",
    "pydantic_settings",
    "psycopg",
    "alembic",
    "app.api",
    "app.db",
    "app.models",
    "app.repositorios",
    "app.servicos",
    "app.schemas",
    "app.infra",
    "app.core",
)

# (objeto, método) que leem o relógio do sistema.
CHAMADAS_DE_RELOGIO = {
    ("datetime", "now"),
    ("datetime", "utcnow"),
    ("datetime", "today"),
    ("date", "today"),
    ("time", "time"),
}

# Testes puros: não precisam limpar o banco antes de cada caso.
pytestmark = pytest.mark.sem_banco


def _proibido(modulo: str) -> bool:
    return any(modulo == p or modulo.startswith(p + ".") for p in IMPORTS_PROIBIDOS)


def violacoes(codigo: str) -> list[str]:
    """Devolve a lista de violações encontradas num código-fonte."""
    problemas: list[str] = []
    for no in ast.walk(ast.parse(codigo)):
        if isinstance(no, ast.Import):
            problemas += [f"import {a.name}" for a in no.names if _proibido(a.name)]
        elif isinstance(no, ast.ImportFrom):
            if no.level > 1:
                # "from ..algo import x" sai de app/dominio: proibido.
                problemas.append(f"import relativo para fora do domínio (nível {no.level})")
            elif no.module and _proibido(no.module):
                problemas.append(f"from {no.module} import ...")
        elif isinstance(no, ast.Call) and isinstance(no.func, ast.Attribute):
            alvo = no.func.value
            # Pega tanto datetime.now() quanto datetime.datetime.now().
            nome_alvo = (
                alvo.id
                if isinstance(alvo, ast.Name)
                else alvo.attr
                if isinstance(alvo, ast.Attribute)
                else None
            )
            if (nome_alvo, no.func.attr) in CHAMADAS_DE_RELOGIO:
                problemas.append(f"chamada de relógio {nome_alvo}.{no.func.attr}()")
    return problemas


ARQUIVOS_DOMINIO = sorted(PASTA_DOMINIO.rglob("*.py"))


def test_a_pasta_de_dominio_existe_e_tem_codigo() -> None:
    # Protege contra um teste "verde" por não ter achado arquivo nenhum.
    assert len(ARQUIVOS_DOMINIO) >= 3


@pytest.mark.parametrize("arquivo", ARQUIVOS_DOMINIO, ids=lambda p: p.name)
def test_dominio_nao_depende_de_infra_nem_do_relogio(arquivo: Path) -> None:
    problemas = violacoes(arquivo.read_text(encoding="utf-8"))
    assert not problemas, f"{arquivo.name} viola a pureza do domínio: {problemas}"


@pytest.mark.parametrize(
    "codigo",
    [
        "import sqlalchemy",
        "from fastapi import HTTPException",
        "from pydantic import BaseModel",
        "from app.models.reserva import Reserva",
        "from app.repositorios import reservas",
        "from ..db import session",
        "from datetime import datetime\nagora = datetime.now()",
        "import datetime\nagora = datetime.datetime.now(datetime.UTC)",
    ],
)
def test_o_detector_pega_violacoes(codigo: str) -> None:
    # Testa o próprio teste: uma fitness function que nunca falha não protege nada.
    assert violacoes(codigo)


def test_o_detector_aceita_codigo_puro() -> None:
    codigo = (
        "from datetime import datetime, timedelta\n"
        "from app.dominio.enums import Papel\n"
        "def f(agora: datetime) -> datetime:\n"
        "    return agora + timedelta(hours=1)\n"
    )
    assert violacoes(codigo) == []
