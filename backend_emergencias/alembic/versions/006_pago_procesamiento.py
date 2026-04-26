"""Crear tabla pago para procesamiento financiero.

Revision ID: 006_pago_procesamiento
Revises: 005_incidente_tecnico
Create Date: 2026-04-25
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006_pago_procesamiento"
down_revision: Union[str, None] = "005_incidente_tecnico"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if insp.has_table("pago"):
        col_names = {c["name"].lower() for c in insp.get_columns("pago")}
        if "id_incidente" in col_names:
            return
        # Esquema legado (p. ej. script SQL con id_asignacion) incompatible con el modelo ORM.
        op.drop_table("pago")
    op.create_table(
        "pago",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("id_incidente", sa.Integer(), nullable=False),
        sa.Column("id_cliente", sa.Integer(), nullable=False),
        sa.Column("id_tecnico", sa.Integer(), nullable=False),
        sa.Column("monto_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("monto_taller", sa.Numeric(12, 2), nullable=False),
        sa.Column("comision_plataforma", sa.Numeric(12, 2), nullable=False),
        sa.Column("metodo_pago", sa.String(length=50), nullable=False, server_default="TARJETA_SIMULADA"),
        sa.Column("estado", sa.String(length=50), nullable=False, server_default="COMPLETADO"),
        sa.Column("fechapago", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["id_incidente"], ["incidente.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["id_cliente"], ["usuario.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["id_tecnico"], ["usuario.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("id_incidente", name="uq_pago_id_incidente"),
    )


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if insp.has_table("pago"):
        op.drop_table("pago")
