"""Tabla notificacion_push_token (FCM / registro de dispositivos)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "009_notificacion_push_token"
down_revision: Union[str, None] = "008_incidente_ia_asignacion"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if insp.has_table("notificacion_push_token"):
        return
    op.create_table(
        "notificacion_push_token",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("id_usuario", sa.Integer(), sa.ForeignKey("usuario.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token", sa.String(length=512), nullable=False),
        sa.Column("plataforma", sa.String(length=32), nullable=False),
        sa.Column("fechacreacion", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index(
        "ix_notificacion_push_token_id_usuario",
        "notificacion_push_token",
        ["id_usuario"],
    )
    op.create_index(
        "uq_push_token_user_token",
        "notificacion_push_token",
        ["id_usuario", "token"],
        unique=True,
    )


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if not insp.has_table("notificacion_push_token"):
        return
    op.drop_index("uq_push_token_user_token", table_name="notificacion_push_token")
    op.drop_index("ix_notificacion_push_token_id_usuario", table_name="notificacion_push_token")
    op.drop_table("notificacion_push_token")
