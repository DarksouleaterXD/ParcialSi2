from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Siempre cargar .env desde la raíz de backend_emergencias (no depende del cwd de uvicorn).
_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_ENV_FILE = _BACKEND_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE if _ENV_FILE.is_file() else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    uploads_dir: str = str(_BACKEND_ROOT / "uploads")

    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/emergencias_db"
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@emergencias.local"
    smtp_use_tls: bool = True


settings = Settings()
