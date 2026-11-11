"""Casos de uso de reserva: realizar, editar, cancelar, consultar."""

from datetime import datetime

import structlog
from sqlalchemy.orm import Session

from app.dominio.enums import StatusReserva
from app.dominio.excecoes import (
    AcessoNegado,
    ConflitoDeHorario,
    NaoEncontrado,
    VersaoDesatualizada,
)
from app.dominio.permissoes import exigir_pode_alterar_reserva
from app.dominio.reservas import (
    garantir_reserva_alteravel,
    garantir_sala_ativa,
    validar_periodo,
    verificar_versao,
)
from app.infra import relogio
from app.models.reserva import Reserva
from app.models.user import User
from app.repositorios import reservas as repo_reservas
from app.servicos import auditoria
from app.servicos import salas as servico_salas
from app.servicos._transacao import traduzindo_erros_do_banco

log = structlog.get_logger()


def obter(db: Session, reserva_id: int) -> Reserva:
    reserva = repo_reservas.buscar(db, reserva_id)
    if reserva is None:
        raise NaoEncontrado("Reserva não encontrada.")
    return reserva


def listar(
    db: Session,
    ator: User,
    *,
    sala_id: int | None,
    de: datetime | None,
    ate: datetime | None,
    minhas: bool,
    status: StatusReserva | None,
    limit: int,
    offset: int,
) -> list[Reserva]:
    # A agenda é visível para a empresa toda; "minhas" só filtra.
    return repo_reservas.listar(
        db,
        sala_id=sala_id,
        de=de,
        ate=ate,
        usuario_id=ator.id if minhas else None,
        status=status,
        limit=limit,
        offset=offset,
    )


def _checar_conflito(
    db: Session, sala_id: int, inicio: datetime, fim: datetime, ignorar_id: int | None = None
) -> None:
    """Checagem PRÉVIA, só para dar uma mensagem boa (com os ids que
    conflitam). Ela NÃO é a garantia: entre este SELECT e o INSERT outra
    requisição pode reservar o mesmo horário. Quem garante é a constraint
    de exclusão no banco (ver traduzindo_erros_do_banco)."""
    conflitos = repo_reservas.ativas_que_conflitam(db, [sala_id], inicio, fim, ignorar_id)
    if conflitos:
        raise ConflitoDeHorario(reservas_conflitantes=[r.id for r in conflitos])


def _exigir_permissao(db: Session, ator: User, reserva: Reserva, acao: str) -> None:
    """Tentativa negada também deixa rastro (log + auditoria): é o tipo de
    evento que um responsável quer conseguir investigar depois."""
    try:
        exigir_pode_alterar_reserva(ator.papel, ator.id, reserva)
    except AcessoNegado:
        log.warning("reserva.acesso_negado", reserva_id=reserva.id, usuario_id=ator.id, acao=acao)
        auditoria.registrar(
            db,
            tipo="reserva.acesso_negado",
            ator_id=ator.id,
            entidade="reserva",
            entidade_id=reserva.id,
            acao=acao,
        )
        db.commit()
        raise


def criar(
    db: Session, ator: User, *, sala_id: int, inicio: datetime, fim: datetime, finalidade: str
) -> Reserva:
    agora = relogio.agora()
    validar_periodo(inicio, fim, agora)
    sala = servico_salas.obter(db, sala_id)
    garantir_sala_ativa(sala.ativa)

    # O dono é quem está logado (vem do token), nunca um campo do corpo.
    reserva = Reserva(
        sala_id=sala_id, usuario_id=ator.id, inicio=inicio, fim=fim, finalidade=finalidade
    )
    try:
        _checar_conflito(db, sala_id, inicio, fim)
        repo_reservas.adicionar(db, reserva)
        with traduzindo_erros_do_banco(db):
            db.flush()  # INSERT: aqui a constraint de exclusão pode disparar (23P01)
            auditoria.registrar(
                db,
                tipo="reserva.criada",
                ator_id=ator.id,
                entidade="reserva",
                entidade_id=reserva.id,
                depois=auditoria.instantaneo_reserva(reserva),
            )
            db.commit()
    except ConflitoDeHorario as exc:
        log.info(
            "reserva.conflito",
            sala_id=sala_id,
            usuario_id=ator.id,
            reservas_conflitantes=exc.reservas_conflitantes,
        )
        raise
    db.refresh(reserva)
    log.info("reserva.criada", reserva_id=reserva.id, sala_id=sala_id, usuario_id=ator.id)
    return reserva


def editar(
    db: Session, ator: User, reserva_id: int, *, versao: int, alteracoes: dict
) -> Reserva:
    reserva = obter(db, reserva_id)
    _exigir_permissao(db, ator, reserva, acao="editar")
    agora = relogio.agora()
    garantir_reserva_alteravel(reserva, agora)
    # Locking otimista, 1ª barreira: a versão que o cliente leu é a atual?
    verificar_versao(versao, reserva.versao)

    antes = auditoria.instantaneo_reserva(reserva)
    nova_sala_id = alteracoes.get("sala_id", reserva.sala_id)
    novo_inicio = alteracoes.get("inicio", reserva.inicio)
    novo_fim = alteracoes.get("fim", reserva.fim)
    mudou_sala_ou_horario = (nova_sala_id, novo_inicio, novo_fim) != (
        reserva.sala_id,
        reserva.inicio,
        reserva.fim,
    )
    try:
        if mudou_sala_ou_horario:
            # Mudar sala/horário é como reservar de novo: revalida tudo.
            validar_periodo(novo_inicio, novo_fim, agora)
            sala = servico_salas.obter(db, nova_sala_id)
            garantir_sala_ativa(sala.ativa)
            _checar_conflito(db, nova_sala_id, novo_inicio, novo_fim, ignorar_id=reserva.id)

        reserva.sala_id = nova_sala_id
        reserva.inicio = novo_inicio
        reserva.fim = novo_fim
        if "finalidade" in alteracoes:
            reserva.finalidade = alteracoes["finalidade"]

        # Locking otimista, 2ª barreira: o UPDATE leva "AND versao = :lida".
        # Se outra transação salvou entre o SELECT e aqui, nenhuma linha é
        # atualizada e o SQLAlchemy levanta StaleDataError -> VersaoDesatualizada.
        with traduzindo_erros_do_banco(db):
            db.flush()
            auditoria.registrar(
                db,
                tipo="reserva.editada",
                ator_id=ator.id,
                entidade="reserva",
                entidade_id=reserva.id,
                antes=antes,
                depois=auditoria.instantaneo_reserva(reserva),
            )
            db.commit()
    except ConflitoDeHorario as exc:
        db.rollback()  # desfaz as alterações em memória
        log.info(
            "reserva.conflito",
            reserva_id=reserva_id,
            sala_id=nova_sala_id,
            usuario_id=ator.id,
            reservas_conflitantes=exc.reservas_conflitantes,
        )
        raise
    except VersaoDesatualizada:
        atual = repo_reservas.versao_atual(db, reserva_id)
        raise VersaoDesatualizada(versao_atual=atual) from None
    db.refresh(reserva)
    log.info("reserva.editada", reserva_id=reserva.id, usuario_id=ator.id, versao=reserva.versao)
    return reserva


def cancelar(db: Session, ator: User, reserva_id: int) -> Reserva:
    """Cancelar é MUDANÇA DE ESTADO, não DELETE: a linha (e o histórico) fica.
    A constraint de exclusão só vale para status='ativa', então o horário
    volta a ficar livre na hora."""
    reserva = obter(db, reserva_id)
    _exigir_permissao(db, ator, reserva, acao="cancelar")
    agora = relogio.agora()
    garantir_reserva_alteravel(reserva, agora)

    antes = auditoria.instantaneo_reserva(reserva)
    reserva.status = StatusReserva.CANCELADA
    reserva.cancelado_em = agora
    reserva.cancelado_por_id = ator.id
    try:
        with traduzindo_erros_do_banco(db):
            db.flush()
            auditoria.registrar(
                db,
                tipo="reserva.cancelada",
                ator_id=ator.id,
                entidade="reserva",
                entidade_id=reserva.id,
                antes=antes,
                depois=auditoria.instantaneo_reserva(reserva),
            )
            db.commit()
    except VersaoDesatualizada:
        atual = repo_reservas.versao_atual(db, reserva_id)
        raise VersaoDesatualizada(versao_atual=atual) from None
    db.refresh(reserva)
    log.info("reserva.cancelada", reserva_id=reserva.id, usuario_id=ator.id)
    return reserva
