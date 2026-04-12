"""Catálogo estático de permisos. Los códigos nuevos se agregan editando este módulo o el despliegue."""

from __future__ import annotations

import json
from typing import Final

# (codigo, descripcion legible para UI)
PERMISOS_CATALOGO: Final[list[tuple[str, str]]] = [
    ("usuarios.ver", "Ver listado de usuarios"),
    ("usuarios.editar", "Crear y editar usuarios"),
    ("roles.gestionar", "Administrar roles y permisos"),
    ("taller.acceder", "Acceder al módulo taller (futuro)"),
    ("incidentes.acceder", "Acceder a incidentes (futuro)"),
    ("pagos.acceder", "Acceder a pagos (futuro)"),
    ("sistema.acceder", "Acceder a sistema / bitácora (futuro)"),
]

PERMISOS_VALIDOS: Final[frozenset[str]] = frozenset(c for c, _ in PERMISOS_CATALOGO)


def parse_permisos(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        if not isinstance(data, list):
            return []
        return [str(x) for x in data if str(x) in PERMISOS_VALIDOS]
    except json.JSONDecodeError:
        return []


def dump_permisos(codes: list[str]) -> str | None:
    clean = sorted({c for c in codes if c in PERMISOS_VALIDOS})
    if not clean:
        return None
    return json.dumps(clean, ensure_ascii=False)
