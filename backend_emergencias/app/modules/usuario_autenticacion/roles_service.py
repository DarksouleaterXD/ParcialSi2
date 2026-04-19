"""Domain helpers for role rules (no FastAPI dependency)."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.modules.usuario_autenticacion.models import Rol, Usuario, usuario_rol


def count_users_with_role(db: Session, rol_id: int) -> int:
    return int(
        db.execute(
            select(func.count()).select_from(usuario_rol).where(usuario_rol.c.id_rol == rol_id),
        ).scalar_one(),
    )


def load_usuario_with_roles(db: Session, user_id: int) -> Usuario | None:
    return db.execute(
        select(Usuario).options(selectinload(Usuario.roles)).where(Usuario.id == user_id),
    ).scalar_one_or_none()
