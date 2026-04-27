"""IA multimodal (Gemini) y trazas de asignación en incidente + candidatos.

Revision ID: 008_incidente_ia_asignacion
Revises: 007_calificacion_incidente
Create Date: 2026-04-25
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008_incidente_ia_asignacion"
down_revision: Union[str, None] = "007_calificacion_incidente"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if not insp.has_table("incidente"):
        return
    inc_cols = {c["name"] for c in insp.get_columns("incidente")}
    add = [
        ("ai_result_json", sa.Column("ai_result_json", sa.Text(), nullable=True)),
        ("ai_confidence", sa.Column("ai_confidence", sa.Numeric(5, 2), nullable=True)),
        ("ai_status", sa.Column("ai_status", sa.String(length=32), nullable=True)),
        ("ai_provider", sa.Column("ai_provider", sa.String(length=64), nullable=True)),
        ("ai_model", sa.Column("ai_model", sa.String(length=128), nullable=True)),
        ("prompt_version", sa.Column("prompt_version", sa.String(length=32), nullable=True)),
        ("assignment_trace_json", sa.Column("assignment_trace_json", sa.Text(), nullable=True)),
    ]
    for name, col in add:
        if name not in inc_cols:
            op.add_column("incidente", col)

    if not insp.has_table("incidente_taller_candidato"):
        op.create_table(
            "incidente_taller_candidato",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("id_incidente", sa.Integer(), sa.ForeignKey("incidente.id", ondelete="CASCADE"), nullable=False),
            sa.Column("id_taller", sa.Integer(), sa.ForeignKey("taller.id", ondelete="CASCADE"), nullable=False),
            sa.Column("id_tecnico_sugerido", sa.Integer(), sa.ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True),
            sa.Column("rank_order", sa.Integer(), nullable=False),
            sa.Column("score_total", sa.Numeric(10, 4), nullable=False),
            sa.Column("score_breakdown_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("eta_minutos_estimada", sa.Numeric(10, 2), nullable=True),
            sa.UniqueConstraint("id_incidente", "id_taller", name="uq_incidente_taller_candidato_inc_taller"),
        )
        op.create_index(
            "ix_incidente_taller_candidato_incidente",
            "incidente_taller_candidato",
            ["id_incidente"],
        )


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if insp.has_table("incidente_taller_candidato"):
        op.drop_index("ix_incidente_taller_candidato_incidente", table_name="incidente_taller_candidato")
        op.drop_table("incidente_taller_candidato")
    if not insp.has_table("incidente"):
        return
    inc_cols = {c["name"] for c in insp.get_columns("incidente")}
    for col in (
        "assignment_trace_json",
        "prompt_version",
        "ai_model",
        "ai_provider",
        "ai_status",
        "ai_confidence",
        "ai_result_json",
    ):
        if col in inc_cols:
            op.drop_column("incidente", col)
