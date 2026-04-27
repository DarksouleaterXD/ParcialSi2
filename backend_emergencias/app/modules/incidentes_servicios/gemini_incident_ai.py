"""Cliente Google Gemini multimodal (audio/imagen/texto) con salida JSON estructurada."""

from __future__ import annotations

import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.modules.incidentes_servicios.ai_assignment_schemas import (
    AiIncidentResult,
    CategoriaIncidenteIA,
)
from app.modules.incidentes_servicios.ai_dataset_few_shot import build_few_shot_blocks

logger = logging.getLogger(__name__)

_JSON_INSTRUCTION = """
Analizá un incidente vehicular de emergencia. Respondé SOLO un JSON válido (sin markdown) con exactamente estas claves:
{
  "transcripcion": string (si hay audio transcribí el habla; si no hay audio dejá ""),
  "danos_identificados": string[] (descripciones cortas de daños visibles en imágenes; si no hay imágenes []),
  "categoria_incidente": one of "bateria"|"llanta"|"choque"|"motor"|"otro",
  "resumen_automatico": string (2-4 frases, tono operativo),
  "confidence": number entre 0 y 1 (confianza global de tu análisis)
}
"""


def sanitize_text_for_provider(text: str, *, max_len: int = 8000) -> str:
    t = (text or "").strip()
    t = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "[email]", t)
    t = re.sub(r"\+?\d[\d\s\-]{8,}\d", "[telefono]", t)
    return t[:max_len]


def _normalize_categoria(raw: str) -> CategoriaIncidenteIA:
    k = (raw or "").strip().lower()
    if k in ("bateria", "battery", "batería"):
        return "bateria"
    if k in ("llanta", "neumatico", "neumático", "neumaticos", "neumáticos", "tire", "tires"):
        return "llanta"
    if k in ("choque", "accidente", "collision"):
        return "choque"
    if k in ("motor", "engine"):
        return "motor"
    return "otro"


def _parse_model_json(text: str) -> dict[str, Any]:
    s = (text or "").strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z]*\n?", "", s)
        s = re.sub(r"\n?```$", "", s).strip()
    return json.loads(s)


def _to_ai_result(data: dict[str, Any]) -> AiIncidentResult:
    """Acepta JSON estricto o con claves extra; tolera modelos que devuelven variantes mínimas."""
    raw = data
    if not isinstance(raw, dict):
        raise ValueError("IA: respuesta no es un objeto JSON")
    conf_raw = raw.get("confidence", 0.6)
    try:
        c = float(conf_raw)
    except (TypeError, ValueError):
        c = 0.6
    c = min(1.0, max(0.0, c))
    danos = raw.get("danos_identificados")
    if not isinstance(danos, list):
        danos = []
    danos = [str(x).strip() for x in danos if str(x).strip()][:30]
    return AiIncidentResult(
        transcripcion=str(raw.get("transcripcion") or "")[:50000],
        danos_identificados=danos,
        categoria_incidente=_normalize_categoria(str(raw.get("categoria_incidente") or "otro")),
        resumen_automatico=(str(raw.get("resumen_automatico") or "Sin resumen estructurado."))[:20000],
        confidence=c,
    )


def _fallback_local_result(descripcion: str, *, has_audio: bool, has_photo: bool) -> AiIncidentResult:
    from app.modules.sistema.ai_engine import simulate_incident_analysis

    bundle = simulate_incident_analysis(descripcion, has_audio=has_audio, has_photo=has_photo)
    cat = _normalize_categoria(str(bundle.get("categoria_ia") or "otro"))
    prio = (bundle.get("prioridad_ia") or "").lower()
    conf = float(bundle.get("confianza_ia") or 0.75)
    resumen = str(bundle.get("resumen_ia") or "")
    trans = ""
    if has_audio and "Audio transcrito" in resumen:
        trans = resumen
    danos: list[str] = []
    if has_photo and cat != "otro":
        danos.append("Daños visibles sugeridos por heurística local (sin modelo de visión).")
    return AiIncidentResult(
        transcripcion=trans,
        danos_identificados=danos,
        categoria_incidente=cat,
        resumen_automatico=resumen or "Análisis local sin proveedor externo.",
        confidence=min(0.95, max(0.35, conf)),
    )


def analyze_with_google(
    descripcion_sanitizada: str,
    *,
    rutas_audio_relativas: list[str],
    rutas_imagen_relativas: list[str],
    uploads_root: Path,
) -> tuple[AiIncidentResult, str, str]:
    """Devuelve (resultado, provider, model). Lanza excepción si Gemini falla tras reintentos."""
    has_audio = bool(rutas_audio_relativas)
    has_photo = bool(rutas_imagen_relativas)
    if not (settings.google_ai_api_key or "").strip():
        r = _fallback_local_result(descripcion_sanitizada, has_audio=has_audio, has_photo=has_photo)
        return r, "local_fallback", "heuristic-v1"

    try:
        import google.generativeai as genai
    except ImportError as exc:
        logger.warning("google-generativeai no instalado: %s", exc)
        r = _fallback_local_result(descripcion_sanitizada, has_audio=has_audio, has_photo=has_photo)
        return r, "local_fallback", "heuristic-v1"

    genai.configure(api_key=settings.google_ai_api_key)
    model_name = (settings.google_ai_model or "gemini-2.0-flash").strip()
    model = genai.GenerativeModel(
        model_name,
        generation_config={
            "response_mime_type": "application/json",
            "temperature": 0.2,
        },
    )

    few_text, ref_images = build_few_shot_blocks()
    parts: list[Any] = []
    parts.append(_JSON_INSTRUCTION)
    parts.append(few_text)
    for i, (img_bytes, mime) in enumerate(ref_images, start=1):
        parts.append(f"Imagen de referencia {i} (dataset interno, solo guía):")
        parts.append({"mime_type": mime, "data": img_bytes})
    parts.append("=== ANÁLISIS DEL PEDIDO ACTUAL (cliente) ===\n")
    parts.append(f"Descripción del cliente (sanitizada):\n{descripcion_sanitizada or '(vacía)'}\n")
    for rel in rutas_imagen_relativas[:4]:
        p = uploads_root / rel
        if not p.is_file():
            continue
        data = p.read_bytes()
        mime = "image/jpeg"
        if rel.lower().endswith(".png"):
            mime = "image/png"
        elif rel.lower().endswith(".webp"):
            mime = "image/webp"
        parts.append({"mime_type": mime, "data": data})
    for rel in rutas_audio_relativas[:2]:
        p = uploads_root / rel
        if not p.is_file():
            continue
        data = p.read_bytes()
        mime = "audio/mpeg"
        if rel.lower().endswith(".wav"):
            mime = "audio/wav"
        elif rel.lower().endswith(".webm"):
            mime = "audio/webm"
        parts.append({"mime_type": mime, "data": data})

    last_err: BaseException | None = None
    timeout_s = float(settings.ai_request_timeout_seconds or 60.0)
    executor = ThreadPoolExecutor(max_workers=1)
    try:
        for attempt in range(3):
            try:
                fut = executor.submit(model.generate_content, parts)
                try:
                    resp = fut.result(timeout=timeout_s)
                except FutureTimeout as exc:
                    fut.cancel()
                    raise TimeoutError(f"Gemini timeout ({timeout_s:.0f}s)") from exc
                raw_text = (resp.text or "").strip()
                data = _parse_model_json(raw_text)
                if not isinstance(data, dict):
                    raise ValueError("IA: JSON no es un objeto")
                r = _to_ai_result(data)
                return (r, "google_gemini", model_name)
            except BaseException as exc:
                last_err = exc
                logger.warning("Gemini intento %s falló: %s", attempt + 1, exc)
                time.sleep(0.4 * (2**attempt))
    finally:
        executor.shutdown(wait=False, cancel_futures=True)
    assert last_err is not None
    logger.error("Gemini: agotados reintentos, usando heurística local. Último error: %s", last_err)
    r = _fallback_local_result(descripcion_sanitizada, has_audio=has_audio, has_photo=has_photo)
    return (r, "local_fallback", f"gemini-failed:{type(last_err).__name__}")
