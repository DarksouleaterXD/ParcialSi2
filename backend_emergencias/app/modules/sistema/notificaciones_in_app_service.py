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


def insertar_notificacion_por_incidente(
    db: Session,
    incidente_id: int,
    *,
    titulo: str,
    mensaje: str,
    tipo: str = "incidente",
) -> None:
    row = db.execute(
        select(Vehiculo.id_usuario)
        .join(Incidente, Incidente.id_vehiculo == Vehiculo.id)
        .where(Incidente.id == incidente_id)
    ).scalar_one_or_none()
    if row is None:
        return
    t = (titulo or "Aviso")[:150]
    m = (mensaje or "")[:20000]
    k = (tipo or "sistema")[:50]
    db.add(Notificacion(id_usuario=int(row), titulo=t, mensaje=m, tipo=k, leida=False))
