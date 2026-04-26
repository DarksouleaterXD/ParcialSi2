"""Tabla idempotencia_registro (POST incidentes/evidencias).

Revision ID: 004_idempotencia
Revises: 003_evidencia_texto
Create Date: 2026-04-17

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_idempotencia"
down_revision: Union[str, None] = "003_evidencia_texto"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if insp.has_table("idempotencia_registro"):
        return
    op.create_table(
        "idempotencia_registro",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("alcance", sa.String(length=50), nullable=False),
        sa.Column("clave", sa.String(length=128), nullable=False),
        sa.Column("id_usuario", sa.Integer(), sa.ForeignKey("usuario.id", ondelete="CASCADE"), nullable=False),
        sa.Column("huella_carga", sa.String(length=64), nullable=False),
        sa.Column("id_incidente_ref", sa.Integer(), sa.ForeignKey("incidente.id", ondelete="CASCADE"), nullable=True),
        sa.Column("id_evidencia_ref", sa.Integer(), sa.ForeignKey("evidencia.id", ondelete="CASCADE"), nullable=True),
        sa.Column("fechacreacion", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("expira_en", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "uq_idempotencia_usuario_alcance_clave",
        "idempotencia_registro",
        ["id_usuario", "alcance", "clave"],
        unique=True,
    )


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if not insp.has_table("idempotencia_registro"):
        return
    op.drop_index("uq_idempotencia_usuario_alcance_clave", table_name="idempotencia_registro")
    op.drop_table("idempotencia_registro")
