"""Dados de demonstração: python -m app.scripts.seed

Cria (se ainda não existirem):
  - 1 admin (e-mail e senha das variáveis SEED_ADMIN_EMAIL / SEED_ADMIN_SENHA)
  - 1 responsável e 2 colaboradores (senha SEED_SENHA_DEMO)
  - 6 recursos (projetor, TV, videoconferência...)
  - 15 salas, cada uma ligada aos seus recursos (relação N:N)
  - 15 reservas para amanhã, para a agenda não começar vazia

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
from app.models.recurso import Recurso
from app.models.reserva import Reserva
from app.models.sala import Sala
from app.models.user import User
from app.repositorios import usuarios as repo_usuarios
from app.servicos import recursos as servico_recursos
from app.servicos import reservas as servico_reservas
from app.servicos import salas as servico_salas
from app.servicos import usuarios as servico_usuarios


class ConfigSeed(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Obrigatórias: o seed NÃO inventa a senha do admin.
    seed_admin_email: EmailStr
    seed_admin_senha: str = Field(min_length=8)
    seed_senha_demo: str = Field(min_length=8)


RECURSOS = [
    ("Projetor", "Projetor Full HD com entrada HDMI"),
    ("TV", "TV de 55\" para apresentar pelo notebook"),
    ("Videoconferência", "Câmera, microfone de mesa e caixa de som"),
    ("Quadro branco", None),
    ("Sistema de som", "Microfones sem fio e caixas de som"),
    ("Ar-condicionado", None),
]

# (nome, capacidade, localização, descrição, recursos)
SALAS = [
    ("Sala Azul", 6, "2º andar", "TV 55\" e quadro branco", ["TV", "Quadro branco", "Ar-condicionado"]),
    ("Sala Verde", 4, "2º andar", "Ideal para 1:1 e entrevistas", ["Quadro branco"]),
    ("Auditório", 40, "Térreo", "Projetor e sistema de som", ["Projetor", "Sistema de som", "Ar-condicionado"]),
    ("Sala Laranja", 10, "3º andar", "Videoconferência", ["Videoconferência", "TV", "Ar-condicionado"]),
    ("Sala Amarela", 8, "3º andar", "Mesa redonda", ["Projetor", "Quadro branco"]),
    ("Sala Roxa", 12, "4º andar", "Boa para workshops", ["Projetor", "Videoconferência", "Ar-condicionado"]),
    ("Sala Vermelha", 6, "2º andar", None, ["TV", "Quadro branco"]),
    ("Sala Rosa", 6, "4º andar", None, ["TV"]),
    ("Sala Cinza", 2, "1º andar", "Para conversas rápidas", ["Videoconferência"]),
    ("Sala Branca", 4, "5º andar", "Sala simples, sem equipamentos", []),
    ("Sala de Treinamento", 20, "Térreo", "Carteiras e bancadas", ["Projetor", "Quadro branco", "Sistema de som", "Ar-condicionado"]),
    ("Sala do Conselho", 14, "5º andar", "Mesa grande de reunião", ["Videoconferência", "TV", "Ar-condicionado"]),
    ("Espaço Criativo", 8, "3º andar", "Paredes de quadro branco e pufes", ["Quadro branco", "TV"]),
    ("Cabine 1", 1, "1º andar", "Cabine individual para chamadas", ["Videoconferência"]),
    ("Cabine 2", 1, "1º andar", "Cabine individual para chamadas", ["Videoconferência"]),
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

        recursos: dict[str, Recurso] = {}
        for nome, descricao in RECURSOS:
            recurso = db.scalar(select(Recurso).where(Recurso.nome == nome))
            if recurso:
                log.info("seed.recurso_ja_existe", nome=nome)
            else:
                recurso = servico_recursos.criar(db, admin, nome=nome, descricao=descricao)
            recursos[nome] = recurso

        salas: dict[str, Sala] = {}
        for nome, capacidade, localizacao, descricao, nomes_recursos in SALAS:
            recurso_ids = [recursos[r].id for r in nomes_recursos]
            sala = db.scalar(select(Sala).where(Sala.nome == nome))
            if sala is None:
                sala = servico_salas.criar(
                    db, admin, nome=nome, capacidade=capacidade,
                    localizacao=localizacao, descricao=descricao, recurso_ids=recurso_ids,
                )
            elif not sala.recursos and recurso_ids:
                # Sala criada antes de existirem recursos: liga os dela agora.
                sala = servico_salas.atualizar(db, admin, sala.id, {"recurso_ids": recurso_ids})
            else:
                log.info("seed.sala_ja_existe", nome=nome)
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
            # Mais reservas da Ana: quem entra com ela vê "Suas reservas" na agenda.
            (ana, "Sala Laranja", em(13), em(14), "Planejamento da sprint"),
            (ana, "Auditório", em(16, 30), em(17, 30), "Apresentação de resultados"),
            (ana, "Cabine 1", em(11), em(11, 30), "Ligação com fornecedor"),
            (ana, "Sala Verde", em(17), em(18), "1:1 com a liderança"),
            (rita, "Sala de Treinamento", em(8, 30), em(12), "Onboarding de novos colaboradores"),
            (rita, "Sala do Conselho", em(9), em(11), "Reunião de diretoria"),
            (rita, "Sala Laranja", em(15), em(16), "Call com cliente"),
            (bruno, "Sala Roxa", em(10, 30), em(12), "Workshop de UX"),
            (bruno, "Sala Amarela", em(14), em(15), "Revisão de arquitetura"),
            (bruno, "Espaço Criativo", em(16), em(17, 30), "Brainstorm de produto"),
            (admin, "Sala Vermelha", em(10), em(10, 30), "Entrevista de candidato"),
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
