"""Deterministic local stub for CU-09 Step 5 (IA sin proveedores externos)."""


def simulate_incident_analysis(descripcion_texto: str, has_audio: bool, has_photo: bool) -> dict:
    """
    Classify and prioritize from plain text and evidence flags (no file I/O).

    Returns keys: categoria_ia, prioridad_ia, resumen_ia, confianza_ia (float).
    """
    t = (descripcion_texto or "").strip().lower()
    conf = 0.85
    if has_photo:
        conf = min(0.95, conf + 0.02)
    if has_audio and t:
        conf = min(0.95, conf + 0.03)

    if "bateria" in t or "arranca" in t:
        return {
            "categoria_ia": "Batería",
            "prioridad_ia": "ALTA",
            "resumen_ia": "Problema de encendido/batería.",
            "confianza_ia": conf,
        }
    if "llanta" in t or "pinchazo" in t or "goma" in t:
        return {
            "categoria_ia": "Neumáticos",
            "prioridad_ia": "MEDIA",
            "resumen_ia": "Pinchazo reportado.",
            "confianza_ia": conf,
        }
    if "choque" in t or "accidente" in t:
        return {
            "categoria_ia": "Accidente",
            "prioridad_ia": "CRÍTICA",
            "resumen_ia": "Colisión. Requiere asistencia inmediata.",
            "confianza_ia": conf,
        }
    if not t and has_audio:
        return {
            "categoria_ia": "Motor",
            "prioridad_ia": "MEDIA",
            "resumen_ia": "Audio transcrito: el motor hace un ruido extraño.",
            "confianza_ia": conf,
        }
    return {
        "categoria_ia": "Otro",
        "prioridad_ia": "BAJA",
        "resumen_ia": "Revisión general requerida.",
        "confianza_ia": conf,
    }
