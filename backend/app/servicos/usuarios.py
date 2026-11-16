import structlog
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.dominio.enums import Papel
from app.dominio.excecoes import NaoEncontrado
from app.dominio.permissoes import validar_alteracao_do_proprio_admin
from app.models.user import User
from app.repositorios import usuarios as repo_usuarios
from app.servicos import auditoria
from app.servicos._transacao import traduzindo_erros_do_banco

CAMPOS_EDITAVEIS = {"nome", "papel", "is_active"}

log = structlog.get_logger()


def obter(db: Session, usuario_id: int) -> User:
    usuario = repo_usuarios.buscar(db, usuario_id)
    if usuario is None:
        raise NaoEncontrado("Usuário não encontrado.")
    return usuario


def listar(
    db: Session,
    *,
    busca: str | None = None,
    papel: Papel | None = None,
    ativos: bool | None = None,
    limit: int,
    offset: int,
) -> tuple[list[User], int]:
    """Uma página da listagem e o total de itens (para a paginação)."""
    filtros = {"busca": busca, "papel": papel, "ativos": ativos}
    itens = repo_usuarios.listar(db, **filtros, limit=limit, offset=offset)
    return itens, repo_usuarios.contar(db, **filtros)


def criar(
    db: Session, ator: User | None, *, email: str, nome: str, senha: str, papel: Papel
) -> User:
    """Cadastro feito pelo admin (qualquer papel).
    ator=None só no seed (não há ninguém logado criando o primeiro admin)."""
    return _gravar_novo(
        db, ator.id if ator else None, email=email, nome=nome, senha=senha, papel=papel
    )


def registrar(db: Session, *, email: str, nome: str, senha: str) -> User:
    """Cadastro PÚBLICO (a própria pessoa se cadastra). O papel é sempre
    colaborador, o de menor poder: ninguém se cadastra como admin. Promover
    alguém continua sendo tarefa do admin (PATCH /v1/usuarios/{id})."""
    return _gravar_novo(
        db, None, email=email, nome=nome, senha=senha, papel=Papel.COLABORADOR, autocadastro=True
    )


def _gravar_novo(
    db: Session,
    ator_id: int | None,
    *,
    email: str,
    nome: str,
    senha: str,
    papel: Papel,
    autocadastro: bool = False,
) -> User:
    usuario = User(
        email=email, nome=nome, hashed_password=hash_password(senha), papel=papel
    )
    repo_usuarios.adicionar(db, usuario)
    tipo = "usuario.registrado" if autocadastro else "usuario.criado"
    # Quem garante e-mail único é a constraint do banco. Checar antes com um
    # SELECT não basta: duas requisições simultâneas passariam juntas.
    with traduzindo_erros_do_banco(db, mensagem_duplicado="E-mail já cadastrado."):
        db.flush()
        if autocadastro:
            ator_id = usuario.id  # quem fez o cadastro foi a própria pessoa
        auditoria.registrar(
            db,
            tipo=tipo,
            ator_id=ator_id,
            entidade="usuario",
            entidade_id=usuario.id,
            depois=auditoria.instantaneo_usuario(usuario),
        )
        db.commit()
    db.refresh(usuario)
    log.info(tipo, novo_usuario_id=usuario.id, papel=usuario.papel, usuario_id=ator_id)
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
    antes = auditoria.instantaneo_usuario(usuario)
    for campo, valor in alteracoes.items():
        setattr(usuario, campo, valor)
    desativou = antes["is_active"] and not usuario.is_active
    tipo = "usuario.desativado" if desativou else "usuario.editado"
    with traduzindo_erros_do_banco(db):
        db.flush()
        auditoria.registrar(
            db,
            tipo=tipo,
            ator_id=ator.id,
            entidade="usuario",
            entidade_id=usuario.id,
            antes=antes,
            depois=auditoria.instantaneo_usuario(usuario),
        )
        db.commit()
    db.refresh(usuario)
    log.info(tipo, alvo_usuario_id=usuario.id, usuario_id=ator.id)
    return usuario
