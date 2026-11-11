"""Hash de senha e JWT. Toda a criptografia da aplicação mora neste arquivo."""

from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

# Argon2: lento de propósito e com uso de memória configurável. Isso encarece
# tentativas em massa de adivinhar senhas, ao contrário de MD5/SHA-256,
# que foram feitos para ser rápidos. O "salt" aleatório já vem embutido no hash.
password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)


# Hash de uma senha qualquer, usado quando o e-mail NÃO existe no login.
# Assim o tempo de resposta é parecido nos dois casos e não revela
# quais e-mails estão cadastrados.
DUMMY_HASH = hash_password("senha-ficticia-para-equalizar-tempo")


def create_access_token(subject: str) -> str:
    """Gera um JWT assinado. ATENÇÃO: o conteúdo é só codificado em Base64,
    não cifrado — qualquer um lê o payload. Nunca coloque dados sensíveis nele."""
    now = datetime.now(UTC)
    payload = {
        "sub": subject,  # quem é o dono do token (o id do usuário, como string)
        "iat": now,  # emitido em
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> str:
    """Valida assinatura e expiração; devolve o "sub".
    Levanta jwt.InvalidTokenError se algo estiver errado."""
    payload = jwt.decode(
        token,
        settings.secret_key,
        # Lista explícita: o servidor decide o algoritmo, não o token.
        algorithms=[settings.jwt_algorithm],
        options={"require": ["exp", "sub"]},
    )
    return payload["sub"]
