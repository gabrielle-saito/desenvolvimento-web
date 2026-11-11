import structlog
from sqlalchemy.orm import Session

from app.dominio.excecoes import NaoEncontrado
from app.models.sala import Sala
from app.models.user import User
from app.repositorios import salas as repo_salas
from app.servicos import auditoria
from app.servicos._transacao import traduzindo_erros_do_banco

CAMPOS_EDITAVEIS = {"nome", "capacidade", "localizacao", "descricao", "ativa"}
MSG_NOME_DUPLICADO = "Já existe uma sala com esse nome."

log = structlog.get_logger()


def obter(db: Session, sala_id: int) -> Sala:
    sala = repo_salas.buscar(db, sala_id)
    if sala is None:
        raise NaoEncontrado("Sala não encontrada.")
    return sala


def listar(db: Session, *, ativas: bool | None, limit: int, offset: int) -> list[Sala]:
    return repo_salas.listar(db, ativas=ativas, limit=limit, offset=offset)


def criar(
    db: Session,
    ator: User,
    *,
    nome: str,
    capacidade: int,
    localizacao: str | None,
    descricao: str | None,
) -> Sala:
    sala = Sala(nome=nome, capacidade=capacidade, localizacao=localizacao, descricao=descricao)
    repo_salas.adicionar(db, sala)
    with traduzindo_erros_do_banco(db, mensagem_duplicado=MSG_NOME_DUPLICADO):
        db.flush()
        auditoria.registrar(
            db,
            tipo="sala.criada",
            ator_id=ator.id,
            entidade="sala",
            entidade_id=sala.id,
            depois=auditoria.instantaneo_sala(sala),
        )
        db.commit()
    db.refresh(sala)
    log.info("sala.criada", sala_id=sala.id, usuario_id=ator.id)
    return sala


def atualizar(db: Session, ator: User, sala_id: int, alteracoes: dict) -> Sala:
    """Inclui desativar (ativa=False). Desativar NÃO apaga nem cancela as
    reservas existentes: só impede reservas novas nesta sala."""
    sala = obter(db, sala_id)
    antes = auditoria.instantaneo_sala(sala)
    for campo, valor in alteracoes.items():
        if campo in CAMPOS_EDITAVEIS:
            setattr(sala, campo, valor)
    # O evento diz o que aconteceu de mais importante: desativar/reativar
    # é diferente de corrigir a capacidade.
    if antes["ativa"] and not sala.ativa:
        tipo = "sala.desativada"
    elif not antes["ativa"] and sala.ativa:
        tipo = "sala.reativada"
    else:
        tipo = "sala.editada"
    with traduzindo_erros_do_banco(db, mensagem_duplicado=MSG_NOME_DUPLICADO):
        db.flush()
        auditoria.registrar(
            db,
            tipo=tipo,
            ator_id=ator.id,
            entidade="sala",
            entidade_id=sala.id,
            antes=antes,
            depois=auditoria.instantaneo_sala(sala),
        )
        db.commit()
    db.refresh(sala)
    log.info(tipo, sala_id=sala.id, usuario_id=ator.id)
    return sala
