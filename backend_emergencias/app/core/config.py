from pathlib import Path

from pydantic import field_validator
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

    # IA mínima (transcripción Whisper u otro proveedor). Vacío => solo fallback determinístico.
    openai_api_key: str = ""

    # Google Gemini (multimodal). Sin GOOGLE_AI_API_KEY => fallback local determinístico.
    google_ai_api_key: str = ""
    google_ai_model: str = "gemini-2.0-flash"
    ai_confidence_threshold: float = 0.55
    ai_request_timeout_seconds: float = 60.0
    ai_prompt_version: str = "v1"
    assignment_weight_priority: float = 0.25
    assignment_weight_distance: float = 0.25
    assignment_weight_specialty: float = 0.25
    assignment_weight_availability: float = 0.15
    assignment_weight_eta: float = 0.10
    assignment_avg_speed_kmh: float = 35.0

    # CORS: en producción definir CORS_ORIGINS (coma, sin espacios dudosos). Lista cerrada; nunca "*"
    # con allow_credentials. Si CORS_ORIGINS está vacío, se usan orígenes de desarrollo locales
    # (ver main.py) y, si cors_allow_localhost_regex es True, un regex para cualquier puerto en
    # localhost / 127.0.0.1 (útil para Flutter web, que elige un puerto aleatorio).
    cors_origins: str = ""
    cors_allow_localhost_regex: bool = True

    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    @field_validator("database_url", mode="before")
    @classmethod
    def _normalize_postgres_url(cls, v: object) -> object:
        """Render/Neon suelen entregar `postgres://` o `postgresql://` sin driver; SQLAlchemy+psycopg2 requiere el prefijo explícito."""
        if not isinstance(v, str):
            return v
        u = v.strip()
        if u.startswith("postgres://"):
            return "postgresql+psycopg2://" + u[len("postgres://") :]
        if u.startswith("postgresql://") and "+psycopg" not in u[:30]:
            return "postgresql+psycopg2://" + u[len("postgresql://") :]
        return u


settings = Settings()
