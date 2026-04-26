import 'package:flutter/material.dart';

/// Normaliza `estado` del backend para comparaciones (sin acentos en valores actuales del API).
String normalizeIncidentEstado(String raw) {
  return raw.trim().toLowerCase().replaceAll(' ', '_');
}

bool incidentEstadoIsPendiente(String estado) {
  return normalizeIncidentEstado(estado) == 'pendiente';
}

bool incidentEstadoIsCancelado(String estado) {
  return normalizeIncidentEstado(estado) == 'cancelado';
}

/// El cliente puede cancelar solo en pendiente o asignado (reglas del servidor).
bool incidentEstadoCanClientCancel(String estado) {
  final e = normalizeIncidentEstado(estado);
  return e == 'pendiente' || e == 'asignado';
}

bool incidentEstadoCanClientDelete(String estado) {
  const deletable = {'cancelado', 'finalizado', 'pagado', 'cerrado', 'resuelto', 'completado'};
  return deletable.contains(normalizeIncidentEstado(estado));
}

bool incidentTechnicianShowsEnCaminoAction(String estado) {
  return normalizeIncidentEstado(estado) == 'asignado';
}

bool incidentTechnicianShowsIniciarTrabajoAction(String estado) {
  return normalizeIncidentEstado(estado) == 'en_camino';
}

bool incidentTechnicianShowsFinalizarTrabajoAction(String estado) {
  return normalizeIncidentEstado(estado) == 'en_proceso';
}

bool incidentEstadoIsTerminalSuccess(String estado) {
  const done = {'cerrado', 'finalizado', 'resuelto', 'completado', 'atendido'};
  return done.contains(normalizeIncidentEstado(estado));
}

/// Paso activo del stepper (0–3). `-1` = cancelado (UI especial).
int incidentTimelineStepIndex(String estado) {
  final e = normalizeIncidentEstado(estado);
  if (e == 'cancelado') {
    return -1;
  }
  if (e == 'pendiente') {
    return 0;
  }
  if (e == 'asignado') {
    return 1;
  }
  if (e == 'en_camino' || e == 'en_curso' || e == 'en_proceso') {
    return 2;
  }
  if (incidentEstadoIsTerminalSuccess(estado)) {
    return 3;
  }
  return 1;
}

({Color background, Color foreground, Color border}) incidentEstadoBadgeColors(
  ThemeData theme,
  String estado,
) {
  final e = normalizeIncidentEstado(estado);
  final scheme = theme.colorScheme;
  if (e == 'cancelado') {
    return (
      background: scheme.errorContainer,
      foreground: scheme.onErrorContainer,
      border: scheme.error,
    );
  }
  if (incidentEstadoIsTerminalSuccess(estado)) {
    const fg = Color(0xFF166534);
    const bg = Color(0xFFDCFCE7);
    return (background: bg, foreground: fg, border: const Color(0xFF22C55E));
  }
  if (e == 'pendiente') {
    const fg = Color(0xFF57534E);
    const bg = Color(0xFFF5F5F4);
    return (background: bg, foreground: fg, border: const Color(0xFFFDBA74));
  }
  if (e == 'asignado' || e == 'en_camino' || e == 'en_curso' || e == 'en_proceso') {
    const fg = Color(0xFF1E3A8A);
    const bg = Color(0xFFEFF6FF);
    return (background: bg, foreground: fg, border: scheme.primary);
  }
  return (
    background: scheme.surfaceContainerHighest,
    foreground: scheme.onSurfaceVariant,
    border: scheme.outlineVariant,
  );
}
