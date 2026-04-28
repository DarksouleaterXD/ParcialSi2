"""Tabla historial analisis_incidente_ia (Gemini estructurado).

Revision ID: 012_ai_analysis
Revises: 011_vehiculo_cols
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "012_ai_analysis"
down_revision: Union[str, None] = "011_vehiculo_cols"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if not insp.has_table("incidente"):
        return
    if insp.has_table("analisis_incidente_ia"):
        return

    is_pg = conn.dialect.name == "postgresql"
    json_t = postgresql.JSONB(astext_type=sa.Text()) if is_pg else sa.JSON()
    json_empty = sa.text("'[]'::jsonb") if is_pg else sa.text("'[]'")

    op.create_table(
        "analisis_incidente_ia",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("id_incidente", sa.Integer(), sa.ForeignKey("incidente.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tipo_incidente", sa.String(length=64), nullable=False),
        sa.Column("prioridad", sa.String(length=32), nullable=False),
        sa.Column("especialidad_requerida", sa.String(length=64), nullable=False),
        sa.Column("resumen_cliente", sa.Text(), nullable=True),
        sa.Column("resumen_taller", sa.Text(), nullable=True),
        sa.Column("recomendaciones_inmediatas", json_t, nullable=False, server_default=json_empty),
        sa.Column("riesgos_detectados", json_t, nullable=False, server_default=json_empty),
        sa.Column("confianza", sa.Numeric(6, 4), nullable=False),
        sa.Column("requiere_grua", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("requiere_atencion_inmediata", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("modelo_usado", sa.String(length=128), nullable=True),
        sa.Column("raw_response", json_t, nullable=True),
        sa.Column("fecha", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("estado", sa.String(length=32), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
    )
    op.create_index("ix_analisis_incidente_ia_incidente", "analisis_incidente_ia", ["id_incidente"])


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if not insp.has_table("analisis_incidente_ia"):
        return
    op.drop_index("ix_analisis_incidente_ia_incidente", table_name="analisis_incidente_ia")
    op.drop_table("analisis_incidente_ia")
