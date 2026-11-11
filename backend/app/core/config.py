"""Configuração lida de variáveis de ambiente (Twelve-Factor, fator III).

Nenhum segredo fica no código: se uma variável obrigatória faltar,
a aplicação NÃO sobe — e isso é proposital (falhar cedo e alto).
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "AGROEMERGIA API"
    database_url: str  # obrigatória: sem valor padrão

    # --- JWT ---
    # min_length: uma chave curta pode ser descoberta por força bruta,
    # e aí qualquer um forja tokens. A API se recusa a subir com chave fraca.
    secret_key: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=30, ge=1, le=1440)

    # --- CORS ---
    # Origens (front-ends) que o NAVEGADOR deixa chamar esta API.
    # No .env, em formato JSON: CORS_ORIGINS=["http://localhost:5173"]
    cors_origins: list[str] = ["http://localhost:5173"]


settings = Settings()
