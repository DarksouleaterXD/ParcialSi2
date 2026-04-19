"""Taller: columnas email y horario_atencion.

Idempotente: solo añade columnas si no existen (bases creadas antes del parche SQL).

Revision ID: 001_taller_cu06
Revises:
Create Date: 2026-04-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001_taller_cu06"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if not insp.has_table("taller"):
        return
    cols = {c["name"] for c in insp.get_columns("taller")}
    if "email" not in cols:
        op.add_column("taller", sa.Column("email", sa.String(length=150), nullable=True))
    if "horario_atencion" not in cols:
        op.add_column("taller", sa.Column("horario_atencion", sa.String(length=120), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if not insp.has_table("taller"):
        return
    cols = {c["name"] for c in insp.get_columns("taller")}
    if "horario_atencion" in cols:
        op.drop_column("taller", "horario_atencion")
    if "email" in cols:
        op.drop_column("taller", "email")
