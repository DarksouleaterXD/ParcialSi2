"""Incidente: técnico asignado (CU10).

Revision ID: 005_incidente_tecnico
Revises: 004_idempotencia
Create Date: 2026-04-20

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_incidente_tecnico"
down_revision: Union[str, None] = "004_idempotencia"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if not insp.has_table("incidente"):
        return
    cols = {c["name"] for c in insp.get_columns("incidente")}
    if "tecnico_id" not in cols:
        op.add_column("incidente", sa.Column("tecnico_id", sa.Integer(), nullable=True))
        op.create_foreign_key(
            "incidente_tecnico_id_fkey",
            "incidente",
            "usuario",
            ["tecnico_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if not insp.has_table("incidente"):
        return
    cols = {c["name"] for c in insp.get_columns("incidente")}
    if "tecnico_id" in cols:
        op.drop_constraint("incidente_tecnico_id_fkey", "incidente", type_="foreignkey")
        op.drop_column("incidente", "tecnico_id")
