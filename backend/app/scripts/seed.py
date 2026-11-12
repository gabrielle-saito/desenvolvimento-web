"""Dados de demonstração: python -m app.scripts.seed

Cria (se ainda não existirem):
  - 1 admin (e-mail e senha das variáveis SEED_ADMIN_EMAIL / SEED_ADMIN_SENHA)
  - 1 responsável e 2 colaboradores (senha SEED_SENHA_DEMO)
  - 4 salas
  - algumas reservas para amanhã, para a agenda não começar vazia

Idempotente: pode rodar várias vezes; o que já existe é mantido.
Usa os SERVIÇOS (e não INSERT direto): as mesmas regras e a mesma auditoria
do sistema de verdade valem para os dados da demo.
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import structlog
from pydantic import EmailStr, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.dominio.enums import Papel
from app.dominio.excecoes import ConflitoDeHorario
from app.infra import relogio
from app.infra.logging_config import configurar_logging
from app.models.reserva import Reserva
from app.models.sala import Sala
from app.models.user import User
from app.repositorios import usuarios as repo_usuarios
from app.servicos import reservas as servico_reservas
from app.servicos import salas as servico_salas
from app.servicos import usuarios as servico_usuarios


class ConfigSeed(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Obrigatórias: o seed NÃO inventa a senha do admin.
    seed_admin_email: EmailStr
    seed_admin_senha: str = Field(min_length=8)
    seed_senha_demo: str = Field(min_length=8)


SALAS = [
    ("Sala Azul", 6, "2º andar", "TV 55\" e quadro branco"),
    ("Sala Verde", 4, "2º andar", "Ideal para 1:1 e entrevistas"),
    ("Auditório", 40, "Térreo", "Projetor e sistema de som"),
    ("Sala Laranja", 10, "3º andar", "Videoconferência"),
]

FUSO = ZoneInfo("America/Sao_Paulo")

log = structlog.get_logger()


def _usuario(db, ator, email: str, nome: str, senha: str, papel: Papel) -> User:
    existente = repo_usuarios.buscar_por_email(db, email)
    if existente:
        log.info("seed.usuario_ja_existe", email=email)
        return existente
    return servico_usuarios.criar(db, ator, email=email, nome=nome, senha=senha, papel=papel)


def main() -> None:
    # Mesmo formato de log da API (JSON). Cada criação já gera o seu evento
    # (usuario.criado, sala.criada, reserva.criada) dentro dos serviços.
    configurar_logging()
    cfg = ConfigSeed()
    db = SessionLocal()
    try:
        senha = cfg.seed_senha_demo
        admin = _usuario(
            db, None, cfg.seed_admin_email.lower(), "Administradora", cfg.seed_admin_senha, Papel.ADMIN
        )
        rita = _usuario(db, admin, "rita@empresa.com", "Rita Responsável", senha, Papel.RESPONSAVEL)
        ana = _usuario(db, admin, "ana@empresa.com", "Ana Colaboradora", senha, Papel.COLABORADOR)
        bruno = _usuario(db, admin, "bruno@empresa.com", "Bruno Colaborador", senha, Papel.COLABORADOR)

        salas: dict[str, Sala] = {}
        for nome, capacidade, localizacao, descricao in SALAS:
            sala = db.scalar(select(Sala).where(Sala.nome == nome))
            if sala:
                log.info("seed.sala_ja_existe", nome=nome)
            else:
                sala = servico_salas.criar(
                    db, admin, nome=nome, capacidade=capacidade,
                    localizacao=localizacao, descricao=descricao,
                )
            salas[nome] = sala

        # Reservas de exemplo para amanhã, só se o banco ainda não tiver nenhuma.
        if db.scalar(select(func.count()).select_from(Reserva)):
            log.info("seed.reservas_ja_existem")
            return
        amanha = (relogio.agora().astimezone(FUSO) + timedelta(days=1)).date()

        def em(hora: int, minuto: int = 0) -> datetime:
            return datetime(amanha.year, amanha.month, amanha.day, hora, minuto, tzinfo=FUSO)

        exemplos = [
            (ana, "Sala Azul", em(9), em(10), "Daily do time de produto"),
            (bruno, "Sala Azul", em(10), em(11), "Revisão de código"),  # encostada na anterior
            (rita, "Auditório", em(14), em(16), "Treinamento de integração"),
            (bruno, "Sala Verde", em(15), em(15, 30), "Entrevista"),
        ]
        for dono, sala_nome, inicio, fim, finalidade in exemplos:
            try:
                servico_reservas.criar(
                    db,
                    dono,
                    sala_id=salas[sala_nome].id,
                    inicio=inicio,
                    fim=fim,
                    finalidade=finalidade,
                )
            except ConflitoDeHorario:
                log.info("seed.horario_ja_ocupado", sala=sala_nome, inicio=inicio.isoformat())
    finally:
        db.close()
        log.info("seed.concluido")


if __name__ == "__main__":
    main()
