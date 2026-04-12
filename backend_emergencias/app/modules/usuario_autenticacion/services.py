import logging
import smtplib
from email.message import EmailMessage

import aiosmtplib
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_token_safe
from app.modules.sistema.logger import token_esta_revocado
from app.modules.usuario_autenticacion.models import Usuario

logger = logging.getLogger(__name__)

security_bearer = HTTPBearer(auto_error=False)
ADMIN_ROL = "Administrador"


def get_current_user(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(security_bearer),
) -> Usuario:
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token_safe(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
    jti = payload.get("jti")
    if jti and token_esta_revocado(db, jti):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesión cerrada")
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
    stmt = select(Usuario).options(selectinload(Usuario.roles)).where(Usuario.id == int(sub))
    user = db.execute(stmt).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado")
    if (user.estado or "").strip().lower() != "activo":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cuenta deshabilitada")
    return user


def require_admin(user: Usuario = Depends(get_current_user)) -> Usuario:
    nombres = {r.nombre for r in user.roles}
    if ADMIN_ROL not in nombres:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Requiere rol Administrador")
    return user


async def enviar_credenciales_nuevo_usuario(*, destino: str, password_plano: str, nombre: str) -> bool:
    if not settings.smtp_host:
        logger.warning(
            "SMTP no configurado: credenciales para %s no enviadas por email. Password: %s",
            destino,
            password_plano,
        )
        return False
    body = (
        f"Hola {nombre},\n\n"
        f"Tu cuenta fue creada en la plataforma de emergencias.\n"
        f"Email: {destino}\n"
        f"Contraseña temporal: {password_plano}\n\n"
        f"Cambiá la contraseña en el primer acceso si la aplicación lo permite.\n"
    )
    msg = EmailMessage()
    msg["From"] = settings.smtp_from
    msg["To"] = destino
    msg["Subject"] = "Credenciales de acceso - Plataforma Emergencias"
    msg.set_content(body)
    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user or None,
            password=settings.smtp_password or None,
            start_tls=settings.smtp_use_tls,
        )
        return True
    except Exception:
        logger.exception("Fallo envío SMTP a %s", destino)
        return False


def enviar_credenciales_nuevo_usuario_sync(*, destino: str, password_plano: str, nombre: str) -> None:
    if not settings.smtp_host:
        logger.warning(
            "SMTP no configurado: credenciales para %s no enviadas. Password temporal: %s",
            destino,
            password_plano,
        )
        return
    body = (
        f"Hola {nombre},\n\n"
        f"Tu cuenta fue creada en la plataforma de emergencias.\n"
        f"Email: {destino}\n"
        f"Contraseña temporal: {password_plano}\n\n"
    )
    msg = EmailMessage()
    msg["From"] = settings.smtp_from
    msg["To"] = destino
    msg["Subject"] = "Credenciales de acceso - Plataforma Emergencias"
    msg.set_content(body)
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
            if settings.smtp_use_tls:
                server.starttls()
            if settings.smtp_user:
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
    except Exception:
        logger.exception("Fallo envío SMTP (sync) a %s", destino)
