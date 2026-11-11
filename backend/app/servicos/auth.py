import structlog
from sqlalchemy.orm import Session

from app.core.security import DUMMY_HASH, verify_password
from app.models.user import User
from app.repositorios import usuarios as repo_usuarios

log = structlog.get_logger()


def autenticar(db: Session, email: str, senha: str) -> User | None:
    """Devolve o usuário se e-mail e senha conferem e a conta está ativa."""
    email = email.strip().lower()
    usuario = repo_usuarios.buscar_por_email(db, email)
    # Verifica a senha MESMO se o usuário não existir (tempo de resposta
    # parecido): não revela quais e-mails estão cadastrados.
    hashed = usuario.hashed_password if usuario else DUMMY_HASH
    senha_ok = verify_password(senha, hashed)
    if usuario is None or not senha_ok or not usuario.is_active:
        # Muitas linhas deste evento seguidas = tentativa de adivinhar senha.
        # (Nunca logar a senha digitada.)
        log.warning("auth.login_falhou", email=email)
        return None
    log.info("auth.login", usuario_id=usuario.id)
    return usuario
