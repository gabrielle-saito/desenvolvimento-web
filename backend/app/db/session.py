from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# pool_pre_ping: testa a conexão antes de usar (evita erro se o banco reiniciou).
# options timezone=UTC: as datas (timestamptz) voltam do banco sempre em UTC,
# independente da configuração do servidor PostgreSQL.
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    connect_args={"options": "-c timezone=UTC"},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
