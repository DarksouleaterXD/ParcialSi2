"""Mecanico_Taller: columna especialidad (técnico / especialidad declarada).

Revision ID: 002_mec_especialidad
Revises: 001_taller_cu06
Create Date: 2026-04-18

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_mec_especialidad"
down_revision: Union[str, None] = "001_taller_cu06"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if not insp.has_table("mecanico_taller"):
        return
    cols = {c["name"] for c in insp.get_columns("mecanico_taller")}
    if "especialidad" not in cols:
        op.add_column("mecanico_taller", sa.Column("especialidad", sa.String(length=30), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if not insp.has_table("mecanico_taller"):
        return
    cols = {c["name"] for c in insp.get_columns("mecanico_taller")}
    if "especialidad" in cols:
        op.drop_column("mecanico_taller", "especialidad")
