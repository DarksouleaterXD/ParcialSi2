"""Cliente Gemini para análisis estructurado de incidentes (sin fallback heurístico)."""

from __future__ import annotations

import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.modules.incidentes_servicios.ai_analysis_schemas import IncidentStructuredAnalysis
from app.modules.incidentes_servicios.gemini_incident_ai import _gemini_model_chain, _is_quota_or_resource_error

logger = logging.getLogger(__name__)

STRUCTURED_JSON_INSTRUCTION = """
Sos un asistente técnico para emergencias vehiculares. Analizá la información provista (texto del cliente, datos del vehículo, ubicación, transcripción de audio si existe, imágenes si existen).

Reglas:
- Respondé SOLO un JSON válido (sin markdown, sin bloques ```, sin texto fuera del JSON).
- No inventes datos no presentes en la entrada.
- Si la evidencia es insuficiente, usá tipo_incidente "otro" y confianza baja (p. ej. <= 0.35).
- La prioridad debe considerar: choque, riesgo en ubicación, imposibilidad de mover el vehículo, menciones de humo/fuego, daños visibles en fotos.
- No des instrucciones peligrosas (no manipular batería expuesta con llamas, no abrir capot con humo intenso, etc.).
- recomendaciones_inmediatas: solo seguridad básica (estacionar seguro, balizas, alejarse si hay riesgo de incendio, llamar emergencias si hay heridos).

Claves y valores permitidos:
- tipo_incidente: "bateria_descargada" | "pinchazo" | "choque" | "sobrecalentamiento" | "falla_motor" | "otro"
- prioridad: "baja" | "media" | "alta" | "critica"
- especialidad_requerida: "electricidad" | "llantas" | "mecanica_general" | "grua" | "carroceria" | "diagnostico"
- resumen_cliente: string breve y claro
- resumen_taller: string técnico breve
- recomendaciones_inmediatas: array de strings
- riesgos_detectados: array de strings
- confianza: número entre 0 y 1
- requiere_grua: boolean
- requiere_atencion_inmediata: boolean
"""


def _parse_json_only(text: str) -> dict[str, Any]:
    s = (text or "").strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z]*\n?", "", s)
        s = re.sub(r"\n?```$", "", s).strip()
    data = json.loads(s)
    if not isinstance(data, dict):
        raise ValueError("La respuesta del modelo no es un objeto JSON")
    return data


def call_gemini_structured_incident_analysis(
    *,
    context_text: str,
    image_parts: list[tuple[bytes, str]],
) -> tuple[IncidentStructuredAnalysis, str]:
    """
    Llama a Gemini con timeout. Requiere API key configurada (validar antes en la capa HTTP).

    Returns:
        (análisis estructurado, nombre del modelo usado)

    Raises:
        TimeoutError, ValueError, RuntimeError según fallos del proveedor o JSON inválido.
    """
    if not (settings.google_ai_api_key or "").strip():
        raise RuntimeError("missing_api_key")

    try:
        import google.generativeai as genai
    except ImportError as exc:
        raise RuntimeError("google-generativeai no instalado") from exc

    genai.configure(api_key=settings.google_ai_api_key)
    model_chain = _gemini_model_chain()
    parts: list[Any] = [STRUCTURED_JSON_INSTRUCTION, "\n=== DATOS DEL INCIDENTE ===\n", context_text or "(sin texto)"]
    for i, (blob, mime) in enumerate(image_parts[:6], start=1):
        parts.append(f"\nImagen evidencia {i}:")
        parts.append({"mime_type": mime, "data": blob})

    timeout_s = float(settings.ai_request_timeout_seconds or 60.0)
    executor = ThreadPoolExecutor(max_workers=1)
    last_err: BaseException | None = None
    try:
        for model_name in model_chain:
            model = genai.GenerativeModel(
                model_name,
                generation_config={
                    "response_mime_type": "application/json",
                    "temperature": 0.15,
                },
            )
            for attempt in range(3):
                try:
                    fut = executor.submit(model.generate_content, parts)
                    try:
                        resp = fut.result(timeout=timeout_s)
                    except FutureTimeout as exc:
                        fut.cancel()
                        raise TimeoutError(f"Gemini timeout ({timeout_s:.0f}s)") from exc
                    raw_text = (resp.text or "").strip()
                    data = _parse_json_only(raw_text)
                    parsed = IncidentStructuredAnalysis.model_validate_relaxed(data)
                    return parsed, model_name
                except BaseException as exc:
                    last_err = exc
                    if _is_quota_or_resource_error(exc):
                        logger.warning("Gemini cuota/límite modelo=%s: %s", model_name, exc)
                        break
                    logger.warning("Gemini modelo=%s intento=%s: %s", model_name, attempt + 1, exc)
                    time.sleep(min(6.0, 0.45 * (2**attempt)))
    finally:
        executor.shutdown(wait=False, cancel_futures=True)

    msg = str(last_err) if last_err else "error desconocido"
    raise RuntimeError(f"Gemini no disponible tras reintentos: {msg[:400]}")


def try_load_local_image(path: Path) -> tuple[bytes, str] | None:
    if not path.is_file():
        return None
    data = path.read_bytes()
    rel = path.name.lower()
    mime = "image/jpeg"
    if rel.endswith(".png"):
        mime = "image/png"
    elif rel.endswith(".webp"):
        mime = "image/webp"
    return data, mime


def try_fetch_remote_image(url: str, *, max_bytes: int = 6_000_000) -> tuple[bytes, str] | None:
    u = (url or "").strip()
    if not u.startswith(("http://", "https://")):
        return None
    try:
        import httpx

        with httpx.Client(timeout=20.0, follow_redirects=True) as client:
            r = client.get(u)
            if r.status_code != 200:
                logger.info("No se pudo descargar imagen evidencia HTTP %s status=%s", u[:120], r.status_code)
                return None
            ct = (r.headers.get("content-type") or "").split(";")[0].strip().lower()
            data = r.content
            if len(data) > max_bytes:
                logger.info("Imagen evidencia demasiado grande url=%s", u[:120])
                return None
            mime = "image/jpeg"
            if "png" in ct:
                mime = "image/png"
            elif "webp" in ct:
                mime = "image/webp"
            return data, mime
    except Exception:
        logger.exception("Fallo al obtener imagen remota (primeros 120 chars): %s", u[:120])
        return None
