"""Bitácora de auditoría y revocación de JWT (logout)."""
from datetime import datetime

from sqlalchemy.orm import Session

from app.modules.sistema.models import Bitacora, TokenRevocado


def registrar_bitacora(
    db: Session,
    *,
    id_usuario: int,
    modulo: str,
    accion: str,
    ip: str | None,
    resultado: str | None,
) -> None:
    row = Bitacora(
        id_usuario=id_usuario,
        modulo=modulo,
        accion=accion,
        iporigen=ip,
        resultado=resultado,
    )
    db.add(row)


def revocar_token(db: Session, *, jti: str, expiracion: datetime) -> None:
    db.merge(TokenRevocado(jti=jti, expiracion=expiracion))


def token_esta_revocado(db: Session, jti: str) -> bool:
    return db.get(TokenRevocado, jti) is not None
