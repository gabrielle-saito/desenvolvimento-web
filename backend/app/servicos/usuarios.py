from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.dominio.enums import Papel
from app.dominio.excecoes import NaoEncontrado
from app.dominio.permissoes import validar_alteracao_do_proprio_admin
from app.models.user import User
from app.repositorios import usuarios as repo_usuarios
from app.servicos._transacao import traduzindo_erros_do_banco

CAMPOS_EDITAVEIS = {"nome", "papel", "is_active"}


def obter(db: Session, usuario_id: int) -> User:
    usuario = repo_usuarios.buscar(db, usuario_id)
    if usuario is None:
        raise NaoEncontrado("Usuário não encontrado.")
    return usuario


def listar(db: Session, *, limit: int, offset: int) -> list[User]:
    return repo_usuarios.listar(db, limit=limit, offset=offset)


def criar(db: Session, ator: User, *, email: str, nome: str, senha: str, papel: Papel) -> User:
    usuario = User(
        email=email, nome=nome, hashed_password=hash_password(senha), papel=papel
    )
    repo_usuarios.adicionar(db, usuario)
    # Quem garante e-mail único é a constraint do banco. Checar antes com um
    # SELECT não basta: duas requisições simultâneas passariam juntas.
    with traduzindo_erros_do_banco(db, mensagem_duplicado="E-mail já cadastrado."):
        db.flush()
        db.commit()
    db.refresh(usuario)
    return usuario


def atualizar(db: Session, ator: User, usuario_id: int, alteracoes: dict) -> User:
    usuario = obter(db, usuario_id)
    alteracoes = {k: v for k, v in alteracoes.items() if k in CAMPOS_EDITAVEIS}
    validar_alteracao_do_proprio_admin(
        ator_id=ator.id,
        alvo_id=usuario.id,
        novo_papel=alteracoes.get("papel"),
        novo_ativo=alteracoes.get("is_active"),
    )
    for campo, valor in alteracoes.items():
        setattr(usuario, campo, valor)
    with traduzindo_erros_do_banco(db):
        db.flush()
        db.commit()
    db.refresh(usuario)
    return usuario
