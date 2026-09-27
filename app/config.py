from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações da aplicação, lidas de variáveis de ambiente ou do arquivo .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./data/estante.db"

    jwt_secret: str = "troque-esta-chave-secreta-jwt-em-producao-2026"
    jwt_algoritmo: str = "HS256"
    jwt_expiracao_minutos: int = 480

    open_library_url: str = "https://openlibrary.org"
    metas_api_url: str = "http://localhost:8001"
    metas_api_key: str = "chave-interna-dev"
    http_timeout_segundos: float = 10.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
