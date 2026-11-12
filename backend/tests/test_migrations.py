"""As migrations são código: também precisam de teste.

1. Modelos (app/models) e migrations descrevem o MESMO schema
   (se alguém mudar um modelo e esquecer a migration, este teste falha).
2. O downgrade funciona de ponta a ponta e o upgrade volta ao head.
"""

from alembic import command

from tests.conftest import alembic_config


def test_modelos_e_migrations_estao_sincronizados() -> None:
    # Equivale a "alembic check": falha se o autogenerate detectaria mudança.
    command.check(alembic_config())


def test_downgrade_completo_e_upgrade_de_volta() -> None:
    cfg = alembic_config()
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    command.check(cfg)
