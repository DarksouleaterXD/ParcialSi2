"""Tabla calificacion ligada a incidente (cliente 1–5 estrellas).

Revision ID: 007_calificacion_incidente
Revises: 006_pago_procesamiento
Create Date: 2026-04-25
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007_calificacion_incidente"
down_revision: Union[str, None] = "006_pago_procesamiento"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if insp.has_table("calificacion"):
        return
    op.create_table(
        "calificacion",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("id_incidente", sa.Integer(), nullable=False),
        sa.Column("puntuacion", sa.Integer(), nullable=False),
        sa.Column("comentario", sa.Text(), nullable=True),
        sa.Column("fecha", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("puntuacion >= 1 AND puntuacion <= 5", name="ck_calificacion_puntuacion"),
        sa.ForeignKeyConstraint(["id_incidente"], ["incidente.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("id_incidente", name="uq_calificacion_id_incidente"),
    )


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if insp.has_table("calificacion"):
        op.drop_table("calificacion")
