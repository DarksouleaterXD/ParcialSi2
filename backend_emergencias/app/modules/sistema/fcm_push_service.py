"""Envío de notificaciones push FCM al cliente (Firebase Admin SDK).

Requiere credenciales de cuenta de servicio (`firebase_credentials_json` o `firebase_credentials_path`).
Sin credenciales, las llamadas no fallan: solo se omiten los envíos (logs en debug).
"""

from __future__ import annotations

import json
import logging
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.sistema.models import NotificacionPushToken
from app.modules.sistema.notificaciones_in_app_service import resolve_client_user_id_for_incident

logger = logging.getLogger(__name__)

_firebase_ready: bool | None = None


def _ensure_firebase_app() -> bool:
    """Inicializa Firebase Admin una vez; devuelve False si no hay credenciales o falla."""
    global _firebase_ready
    if _firebase_ready is True:
        return True
    if _firebase_ready is False:
        return False

    try:
        import firebase_admin
        from firebase_admin import credentials

        if firebase_admin._apps:
            _firebase_ready = True
            return True

        raw_json = (settings.firebase_credentials_json or "").strip()
        path = (settings.firebase_credentials_path or "").strip()
        if raw_json:
            cred = credentials.Certificate(json.loads(raw_json))
            firebase_admin.initialize_app(cred)
        elif path:
            cred = credentials.Certificate(path)
            firebase_admin.initialize_app(cred)
        else:
            _firebase_ready = False
            logger.warning(
                "FCM deshabilitado: definí FIREBASE_CREDENTIALS_JSON o FIREBASE_CREDENTIALS_PATH en el servidor.",
            )
            return False

        _firebase_ready = True
        logger.info("Firebase Admin inicializado para FCM.")
        return True
    except Exception:
        _firebase_ready = False
        logger.exception("No se pudo inicializar Firebase Admin para FCM.")
        return False


def try_send_push_for_incident(db: Session, incidente_id: int, titulo: str, mensaje: str) -> None:
    """Tras persistir la notificación in-app y hacer commit, envía la misma alerta por FCM al cliente."""
    if not _ensure_firebase_app():
        return

    uid = resolve_client_user_id_for_incident(db, incidente_id)
    if uid is None:
        return

    tokens = (
        db.execute(select(NotificacionPushToken.token).where(NotificacionPushToken.id_usuario == uid)).scalars().all()
    )
    if not tokens:
        logger.debug("FCM: usuario %s sin tokens registrados", uid)
        return

    from firebase_admin import messaging

    tit = (titulo or "Aviso")[:150]
    body = (mensaje or "")[:4000]

    for raw in tokens:
        tok = (raw or "").strip()
        if not tok:
            continue
        msg = messaging.Message(
            notification=messaging.Notification(title=tit, body=body),
            token=tok,
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    channel_id="high_importance_channel",
                    default_sound=True,
                ),
            ),
        )
        try:
            messaging.send(msg)
        except messaging.UnregisteredError:
            logger.info("FCM token inválido o dado de baja (usuario %s)", uid)
        except Exception:
            logger.exception("FCM send falló (usuario %s)", uid)
