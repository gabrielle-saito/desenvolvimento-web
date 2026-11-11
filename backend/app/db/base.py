from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Classe-mãe de todos os modelos. O Alembic lê Base.metadata para
    comparar o que está no código com o que está no banco."""
