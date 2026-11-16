"""Recursos das salas (projetor, TV, videoconferência). Escrita: admin."""

from collections.abc import Sequence

import structlog
from sqlalchemy.orm import Session

from app.dominio.excecoes import NaoEncontrado, RecursoInvalido
from app.models.recurso import Recurso
from app.models.user import User
from app.repositorios import recursos as repo_recursos
from app.servicos import auditoria
from app.servicos._transacao import traduzindo_erros_do_banco

CAMPOS_EDITAVEIS = {"nome", "descricao", "ativo"}
MSG_NOME_DUPLICADO = "Já existe um recurso com esse nome."

log = structlog.get_logger()


def obter(db: Session, recurso_id: int) -> Recurso:
    recurso = repo_recursos.buscar(db, recurso_id)
    if recurso is None:
        raise NaoEncontrado("Recurso não encontrado.")
    return recurso


def listar(
    db: Session, *, busca: str | None, ativos: bool | None, limit: int, offset: int
) -> tuple[list[Recurso], int]:
    """Uma página da listagem e o total de itens (para a paginação)."""
    itens = repo_recursos.listar(db, busca=busca, ativos=ativos, limit=limit, offset=offset)
    return itens, repo_recursos.contar(db, busca=busca, ativos=ativos)


def para_sala(db: Session, recurso_ids: Sequence[int], *, atuais: Sequence[Recurso] = ()) -> list[Recurso]:
    """Converte os ids enviados no cadastro/edição de uma sala em recursos.

    Recusa id inexistente e recurso DESATIVADO, a não ser que a sala já o
    tenha (editar o nome de uma sala não obriga a tirar um recurso antigo)."""
    ids = list(dict.fromkeys(recurso_ids))  # sem repetidos, na ordem enviada
    encontrados = {r.id: r for r in repo_recursos.buscar_varios(db, ids)}
    faltando = [i for i in ids if i not in encontrados]
    if faltando:
        raise RecursoInvalido(f"Recurso não encontrado: {', '.join(map(str, faltando))}.")
    ja_tinha = {r.id for r in atuais}
    inativos = [r.nome for r in encontrados.values() if not r.ativo and r.id not in ja_tinha]
    if inativos:
        raise RecursoInvalido(f"Recurso desativado não pode ser adicionado: {', '.join(inativos)}.")
    return [encontrados[i] for i in ids]


def criar(db: Session, ator: User, *, nome: str, descricao: str | None) -> Recurso:
    recurso = Recurso(nome=nome, descricao=descricao)
    repo_recursos.adicionar(db, recurso)
    with traduzindo_erros_do_banco(db, mensagem_duplicado=MSG_NOME_DUPLICADO):
        db.flush()
        auditoria.registrar(
            db,
            tipo="recurso.criado",
            ator_id=ator.id,
            entidade="recurso",
            entidade_id=recurso.id,
            depois=auditoria.instantaneo_recurso(recurso),
        )
        db.commit()
    db.refresh(recurso)
    log.info("recurso.criado", recurso_id=recurso.id, usuario_id=ator.id)
    return recurso


def atualizar(db: Session, ator: User, recurso_id: int, alteracoes: dict) -> Recurso:
    """Inclui desativar (ativo=False): o recurso some das opções para salas,
    mas as salas que já o têm continuam com ele."""
    recurso = obter(db, recurso_id)
    antes = auditoria.instantaneo_recurso(recurso)
    for campo, valor in alteracoes.items():
        if campo in CAMPOS_EDITAVEIS:
            setattr(recurso, campo, valor)
    if antes["ativo"] and not recurso.ativo:
        tipo = "recurso.desativado"
    elif not antes["ativo"] and recurso.ativo:
        tipo = "recurso.reativado"
    else:
        tipo = "recurso.editado"
    with traduzindo_erros_do_banco(db, mensagem_duplicado=MSG_NOME_DUPLICADO):
        db.flush()
        auditoria.registrar(
            db,
            tipo=tipo,
            ator_id=ator.id,
            entidade="recurso",
            entidade_id=recurso.id,
            antes=antes,
            depois=auditoria.instantaneo_recurso(recurso),
        )
        db.commit()
    db.refresh(recurso)
    log.info(tipo, recurso_id=recurso.id, usuario_id=ator.id)
    return recurso


def desativar(db: Session, ator: User, recurso_id: int) -> None:
    """DELETE /recursos/{id}: soft delete (o banco nem deixaria apagar um
    recurso em uso: FK RESTRICT). Idempotente, como em salas.desativar."""
    recurso = obter(db, recurso_id)
    if recurso.ativo:
        atualizar(db, ator, recurso_id, {"ativo": False})
