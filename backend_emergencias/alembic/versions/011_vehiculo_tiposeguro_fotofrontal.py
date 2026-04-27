"""Asegura columnas opcionales de vehículo (evita ProgrammingError en INSERT si la BD quedó atrás).

Revision ID: 011_vehiculo_tiposeguro_fotofrontal
Revises: 010_calificacion_id_incidente
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "011_vehiculo_tiposeguro_fotofrontal"
down_revision: Union[str, None] = "010_calificacion_id_incidente"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(text("ALTER TABLE vehiculo ADD COLUMN IF NOT EXISTS tiposeguro VARCHAR(50)"))
    op.execute(text("ALTER TABLE vehiculo ADD COLUMN IF NOT EXISTS fotofrontal VARCHAR(255)"))


def downgrade() -> None:
    op.execute(text("ALTER TABLE vehiculo DROP COLUMN IF EXISTS tiposeguro"))
    op.execute(text("ALTER TABLE vehiculo DROP COLUMN IF EXISTS fotofrontal"))
