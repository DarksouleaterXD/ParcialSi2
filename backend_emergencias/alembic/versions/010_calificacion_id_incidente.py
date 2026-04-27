"""Alineación: revisión 010 faltante en el repo; esquema ya coherente en BD (stamp previo).

Si tu base fue estampada con 010 y este archivo no existía, `alembic` fallaba al cargar el grafo.
`upgrade` es no-op: la tabla `calificacion` y su vínculo a `incidente` vienen de 007.

Revision ID: 010_calificacion_id_incidente
Revises: 009_notificacion_push_token
"""

from typing import Sequence, Union

from alembic import op

revision: str = "010_calificacion_id_incidente"
down_revision: Union[str, None] = "009_notificacion_push_token"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Sin cambios de esquema: 007 crea `calificacion` con `id_incidente` y UQ adecuada.
    pass


def downgrade() -> None:
    # No revierte; evita borrar datos si 010 se usa solo para desbloquear Alembic.
    pass
