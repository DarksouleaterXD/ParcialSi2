"""Estados de incidente compartidos con otros módulos (p. ej. vehículos)."""

TERMINAL_ESTADOS_INCIDENTE = frozenset(
    {"cerrado", "finalizado", "cancelado", "resuelto", "completado", "pagado"},
)

EVIDENCE_TYPES = frozenset({"foto", "audio", "texto"})

ESTADO_INICIAL_INCIDENTE = "Pendiente"
ESTADO_PENDIENTE_IA = "Pendiente IA"
ESTADO_REVISION_MANUAL = "Revision manual"
ESTADO_SUGERIDO = "Sugerido"
