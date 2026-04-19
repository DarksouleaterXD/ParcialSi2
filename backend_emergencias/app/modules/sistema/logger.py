"""Revocación de JWT en logout (TokenRevocado). La bitácora queda en `bitacora_service`."""
from datetime import datetime

from sqlalchemy.orm import Session

from app.modules.sistema.models import TokenRevocado


def revocar_token(db: Session, *, jti: str, expiracion: datetime) -> None:
    db.merge(TokenRevocado(jti=jti, expiracion=expiracion))


def token_esta_revocado(db: Session, jti: str) -> bool:
    return db.get(TokenRevocado, jti) is not None
