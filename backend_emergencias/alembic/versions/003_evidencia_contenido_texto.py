"""Evidencia: columna contenido_texto (CU-09 texto sin archivo).

Revision ID: 003_evidencia_texto
Revises: 002_mec_especialidad
Create Date: 2026-04-17

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_evidencia_texto"
down_revision: Union[str, None] = "002_mec_especialidad"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if not insp.has_table("evidencia"):
        return
    cols = {c["name"] for c in insp.get_columns("evidencia")}
    if "contenido_texto" not in cols:
        op.add_column("evidencia", sa.Column("contenido_texto", sa.Text(), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if not insp.has_table("evidencia"):
        return
    cols = {c["name"] for c in insp.get_columns("evidencia")}
    if "contenido_texto" in cols:
        op.drop_column("evidencia", "contenido_texto")
