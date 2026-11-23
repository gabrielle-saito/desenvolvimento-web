"""Dados de demonstração: python -m app.scripts.seed

Cria (se ainda não existirem):
  - 4 contas de demonstração, todas com a senha da variável SEED_SENHA (.env):
    gabi (admin), manu (responsável), ste e colaborador (colaboradores)
  - 5 recursos (projetor, TV, quadro branco...)
  - 15 salas, cada uma ligada aos seus recursos (relação N:N)
  - reservas espalhadas pelos dias úteis de novembro/2026 a janeiro/2027,
    das quatro contas, algumas já canceladas (para o histórico)

A senha NÃO fica no código: vem de SEED_SENHA (o .env.example sugere um valor,
para todo o grupo entrar com as mesmas contas). Sem ela, o seed não roda.

Idempotente: pode rodar várias vezes; o que já existe é mantido.
Usa os SERVIÇOS (e não INSERT direto): as mesmas regras e a mesma auditoria
do sistema de verdade valem para os dados da demo.
"""

import random
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import structlog
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.dominio.enums import Papel
from app.dominio.excecoes import ConflitoDeHorario, PeriodoInvalido
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

    # Obrigatória e sem valor padrão: o seed NÃO inventa senha.
    # Uma senha curta só é possível aqui: o seed chama o serviço direto, e o
    # mínimo de 8 caracteres é regra da API (cadastro e criação de usuário).
    seed_senha: str = Field(min_length=1)


# Contas de demonstração: (e-mail, nome, papel). Todas com a senha SEED_SENHA.
CONTAS = [
    ("gabi@veritas.com", "Gabi", Papel.ADMIN),
    ("manu@veritas.com", "Manu", Papel.RESPONSAVEL),
    ("ste@veritas.com", "Ste", Papel.COLABORADOR),
    ("colaborador@veritas.com", "Colaborador", Papel.COLABORADOR),
]


RECURSOS = [
    ("Projetor", "Projetor Full HD com entrada HDMI"),
    ("TV", "TV de 55\" para apresentar pelo notebook"),
    ("Quadro branco", None),
    ("Sistema de som", "Microfones sem fio e caixas de som"),
    ("Ar-condicionado", None),
]

# (nome, capacidade, localização, descrição, recursos)
SALAS = [
    ("Sala Azul", 6, "2º andar", "TV 55\" e quadro branco", ["TV", "Quadro branco", "Ar-condicionado"]),
    ("Sala Verde", 4, "2º andar", "Ideal para 1:1 e entrevistas", ["Quadro branco"]),
    ("Auditório", 40, "Térreo", "Projetor e sistema de som", ["Projetor", "Sistema de som", "Ar-condicionado"]),
    ("Sala Laranja", 10, "3º andar", "TV para apresentações", ["TV", "Ar-condicionado"]),
    ("Sala Amarela", 8, "3º andar", "Mesa redonda", ["Projetor", "Quadro branco"]),
    ("Sala Roxa", 12, "4º andar", "Boa para workshops", ["Projetor", "Ar-condicionado"]),
    ("Sala Vermelha", 6, "2º andar", None, ["TV", "Quadro branco"]),
    ("Sala Rosa", 6, "4º andar", None, ["TV"]),
    ("Sala Cinza", 2, "1º andar", "Para conversas rápidas", []),
    ("Sala Branca", 4, "5º andar", "Sala simples, sem equipamentos", []),
    ("Sala de Treinamento", 20, "Térreo", "Carteiras e bancadas", ["Projetor", "Quadro branco", "Sistema de som", "Ar-condicionado"]),
    ("Sala do Conselho", 14, "5º andar", "Mesa grande de reunião", ["TV", "Ar-condicionado"]),
    ("Espaço Criativo", 8, "3º andar", "Paredes de quadro branco e pufes", ["Quadro branco", "TV"]),
    ("Cabine 1", 1, "1º andar", "Cabine individual para chamadas", []),
    ("Cabine 2", 1, "1º andar", "Cabine individual para chamadas", []),
]

FUSO = ZoneInfo("America/Sao_Paulo")

log = structlog.get_logger()


def _usuario(db, ator, email: str, nome: str, senha: str, papel: Papel) -> User:
    existente = repo_usuarios.buscar_por_email(db, email)
    if existente:
        log.info("seed.usuario_ja_existe", email=email)
        return existente
    return servico_usuarios.criar(db, ator, email=email, nome=nome, senha=senha, papel=papel)


# Reservas de demonstração: dias úteis de novembro/2026 a janeiro/2027, menos
# Finados, Consciência Negra, véspera e dia de Natal, véspera e dia de Ano-Novo.
# Dias que já passaram são pulados (a API não aceita reserva no passado).
PERIODO = (date(2026, 11, 1), date(2027, 1, 29))
SEM_EXPEDIENTE = {
    date(2026, 11, 2), date(2026, 11, 20),
    date(2026, 12, 24), date(2026, 12, 25), date(2026, 12, 31), date(2027, 1, 1),
}
HORARIOS = [((8, 30), (9, 30)), ((10, 0), (11, 0)), ((11, 0), (12, 0)), ((14, 0), (15, 30)), ((16, 0), (17, 0))]
FINALIDADES = [
    "Daily do time de produto", "Revisão de código", "Planejamento da sprint",
    "Reunião com cliente", "Entrevista de candidato", "Treinamento interno",
    "Alinhamento semanal", "Apresentação de resultados", "Workshop de UX",
    "Revisão de arquitetura", "1:1 com a liderança", "Brainstorm de produto",
    "Reunião de diretoria", "Onboarding de novos colaboradores", "Retrospectiva",
]
# Uma em cada CANCELAR_A_CADA reservas é cancelada pelo próprio dono.
CANCELAR_A_CADA = 9  # sem divisor comum com 4 (contas): as canceladas se dividem entre todas


def _dias_uteis():
    dia, fim = PERIODO
    while dia <= fim:
        if dia.weekday() < 5 and dia not in SEM_EXPEDIENTE:
            yield dia
        dia += timedelta(days=1)


def _reservas_de_demonstracao(db, donos: list[User], salas: dict[str, Sala]) -> None:
    # Sorteio com semente fixa: todo mundo do grupo recebe exatamente as
    # mesmas reservas. Salas diferentes no mesmo dia: nunca há choque.
    sorteio = random.Random(2026)
    # Fora do sorteio: as cabines (1 pessoa, não são sala de reunião) e a
    # Sala Laranja, que a collection do Postman reserva daqui a 3 dias às 16h.
    pool = [s for nome, s in salas.items() if not nome.startswith("Cabine") and nome != "Sala Laranja"]
    n = 0
    for dia in _dias_uteis():
        quantas = sorteio.choice([2, 3, 3, 4])
        for (h_ini, h_fim), sala in zip(
            sorteio.sample(HORARIOS, quantas), sorteio.sample(pool, quantas), strict=True
        ):
            dono = donos[n % len(donos)]
            inicio = datetime.combine(dia, datetime.min.time(), FUSO).replace(hour=h_ini[0], minute=h_ini[1])
            fim = inicio.replace(hour=h_fim[0], minute=h_fim[1])
            finalidade = sorteio.choice(FINALIDADES)
            n += 1
            try:
                reserva = servico_reservas.criar(
                    db, dono, sala_id=sala.id, inicio=inicio, fim=fim, finalidade=finalidade
                )
            except (ConflitoDeHorario, PeriodoInvalido) as erro:
                # PeriodoInvalido: a data já passou (seed rodado depois de jan/2027).
                log.info("seed.reserva_ignorada", sala=sala.nome, inicio=inicio.isoformat(), motivo=str(erro))
                continue
            if n % CANCELAR_A_CADA == 0:
                servico_reservas.cancelar(db, dono, reserva.id)


def main() -> None:
    # Mesmo formato de log da API (JSON). Cada criação já gera o seu evento
    # (usuario.criado, sala.criada, reserva.criada) dentro dos serviços.
    configurar_logging()
    senha = ConfigSeed().seed_senha
    db = SessionLocal()
    try:
        # A primeira conta (admin) é criada sem ator; ela cria as demais.
        contas: list[User] = []
        for email, nome, papel in CONTAS:
            ator = contas[0] if contas else None
            contas.append(_usuario(db, ator, email, nome, senha, papel))
        admin = contas[0]

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

        # Reservas só se o banco ainda não tiver nenhuma.
        if db.scalar(select(func.count()).select_from(Reserva)):
            log.info("seed.reservas_ja_existem")
            return
        _reservas_de_demonstracao(db, contas, salas)
    finally:
        db.close()
        log.info("seed.concluido")


if __name__ == "__main__":
    main()
