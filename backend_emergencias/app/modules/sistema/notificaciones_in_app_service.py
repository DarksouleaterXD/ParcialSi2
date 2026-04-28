"""Persistencia de notificaciones in-app (tabla `notificacion`).

Los mensajes se asocian al dueño del vehículo vía `id_usuario` del [Vehiculo].
No hace `commit` ni `flush`: el llamador transacciona con el resto del flujo.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.incidentes_servicios.models import Incidente
from app.modules.sistema.models import Notificacion
from app.modules.usuario_autenticacion.models import Vehiculo


def resolve_client_user_id_for_incident(db: Session, incidente_id: int) -> int | None:
    """Usuario dueño del vehículo del incidente (destinatario de avisos)."""
    row = db.execute(
        select(Vehiculo.id_usuario)
        .join(Incidente, Incidente.id_vehiculo == Vehiculo.id)
        .where(Incidente.id == incidente_id),
    ).scalar_one_or_none()
    return int(row) if row is not None else None


def insertar_notificacion_por_incidente(
    db: Session,
    incidente_id: int,
    *,
    titulo: str,
    mensaje: str,
    tipo: str = "incidente",
) -> None:
    row = resolve_client_user_id_for_incident(db, incidente_id)
    if row is None:
        return
    t = (titulo or "Aviso")[:150]
    m = (mensaje or "")[:20000]
    k = (tipo or "sistema")[:50]
    db.add(Notificacion(id_usuario=row, titulo=t, mensaje=m, tipo=k, leida=False))
