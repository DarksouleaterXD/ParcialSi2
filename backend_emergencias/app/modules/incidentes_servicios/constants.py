"""Estados de incidente compartidos con otros módulos (p. ej. vehículos)."""

TERMINAL_ESTADOS_INCIDENTE = frozenset(
    {"cerrado", "finalizado", "cancelado", "resuelto", "completado"},
)

EVIDENCE_TYPES = frozenset({"foto", "audio", "texto"})

ESTADO_INICIAL_INCIDENTE = "Pendiente"
