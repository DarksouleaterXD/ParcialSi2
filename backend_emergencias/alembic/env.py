"""Alembic: usa la misma `DATABASE_URL` que `app.core.config` (.env)."""

from __future__ import annotations

import logging
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from app.core.config import settings
from app.core.database import Base

# Registrar todos los modelos en Base.metadata (autogenerate y consistencia)
from app.modules.incidentes_servicios import models as _incidentes_models  # noqa: F401
from app.modules.pagos import models as _pagos_models  # noqa: F401
from app.modules.sistema import models as _sistema_models  # noqa: F401
from app.modules.taller_tecnico import models as _taller_models  # noqa: F401
from app.modules.usuario_autenticacion import models as _usuario_models  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
logger = logging.getLogger("alembic.env")

# ConfigParser trata % como interpolación; escapar en URLs con contraseña
config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = settings.database_url
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(settings.database_url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
