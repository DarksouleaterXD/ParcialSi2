"""Few-shot y referencias en `ai_dataset/` para reforzar prompts Gemini (1.5.4) sin entrenar modelo local."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DATASET_DIR = Path(__file__).resolve().parent / "ai_dataset"
_JSON_PATH = _DATASET_DIR / "few_shot_examples.json"
_IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp")


def _first_image_in_category(categoria: str) -> Path | None:
    sub = (categoria or "otro").strip().lower()
    d = _DATASET_DIR / "images" / sub
    if not d.is_dir():
        return None
    for p in sorted(d.iterdir()):
        if p.is_file() and p.suffix.lower() in _IMAGE_EXTS:
            return p
    return None


def _read_image_part(path: Path) -> tuple[bytes, str] | None:
    if not path.is_file():
        return None
    data = path.read_bytes()
    mime = "image/jpeg"
    s = path.suffix.lower()
    if s == ".png":
        mime = "image/png"
    elif s == ".webp":
        mime = "image/webp"
    return (data, mime)


def _resolve_example_image(ex: dict[str, Any]) -> Path | None:
    out = ex.get("output_esperado") or {}
    cat = str(out.get("categoria_incidente") or "otro").strip().lower()
    rel = (ex.get("image") or "").strip()
    if rel:
        p = (_DATASET_DIR / rel).resolve()
        try:
            p.relative_to(_DATASET_DIR)
        except ValueError:
            return _first_image_in_category(cat)
        if p.is_file():
            return p
        logger.info("Imagen few-shot no hallada, fallback categoría: %s -> %s", p, cat)
    return _first_image_in_category(cat)


def build_few_shot_blocks() -> tuple[str, list[tuple[bytes, str]]]:
    """
    Texto de referencia + imágenes de apoyo (máx. 4) bajo el directorio ai_dataset.
    Si no hay JSON o imágenes, devuelve texto mínimo y lista vacía.
    """
    lines: list[str] = [
        "Referencia de categorías del sistema: bateria, llanta, choque, motor, otro.",
        "Usá imágenes de EJEMPLO (si se adjuntan) solo como guía de estilo, no asumas que el cliente envió la misma foto.",
    ]
    ref_images: list[tuple[bytes, str]] = []
    if not _JSON_PATH.is_file():
        logger.info("ai_dataset: sin %s; few-shot solo por instrucción base.", _JSON_PATH.name)
        return "\n".join(lines), []

    try:
        doc = json.loads(_JSON_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("ai_dataset: JSON inválido: %s", exc)
        return "\n".join(lines), []

    for ex in (doc.get("examples") or [])[:6]:
        ex_id = ex.get("id", "")
        des = (ex.get("descripcion_cliente") or "").strip()
        o = ex.get("output_esperado") or {}
        cat = o.get("categoria_incidente", "")
        res_breve = (o.get("resumen_automatico") or "")[:300]
        lines.append(
            f"---\nEJEMPLO {ex_id} | categoría_tipo: {cat}\n"
            f"Texto cliente: {des}\n"
            f"Salida razonable: resumen ~ {res_breve!s}\n"
        )
        if len(ref_images) >= 4:
            continue
        rpath = _resolve_example_image(ex)
        if rpath is None:
            continue
        part = _read_image_part(rpath)
        if part is not None:
            ref_images.append(part)
            lines.append(f"(Foto de referencia adjunta: categoría aprox. {cat}, archivo {rpath.name})")

    return "\n".join(lines), ref_images
