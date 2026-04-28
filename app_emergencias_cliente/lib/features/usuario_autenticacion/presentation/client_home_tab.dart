import 'dart:async' show unawaited;

import 'package:flutter/material.dart';

import '../../../core/authorized_client.dart' show ApiClientException, SessionExpiredException;
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../../core/widgets/primary_button.dart';
import '../../incidentes_servicios/data/incidents_api.dart';
import '../data/profile_api.dart';

/// Client home: summary and shortcuts (not the vehicle list).
class ClientHomeTab extends StatefulWidget {
  const ClientHomeTab({
    super.key,
    required this.profileApi,
    required this.onSessionExpired,
    required this.onOpenVehicles,
    required this.onAddVehicle,
    this.incidentsApi,
    this.onOpenIncidents,
    this.onReportEmergency,
    this.isTechnician = false,
  });

  final ProfileApi profileApi;
  final VoidCallback onSessionExpired;
  final VoidCallback onOpenVehicles;
  final VoidCallback onAddVehicle;

  /// Si está definido, el resumen muestra último resultado de IA del historial del cliente.
  final IncidentsApi? incidentsApi;

  /// Abre la pestaña de actividad o de viajes asignados (técnico).
  final VoidCallback? onOpenIncidents;

  /// Abre el asistente de reporte (solo cliente).
  final VoidCallback? onReportEmergency;

  final bool isTechnician;

  @override
  State<ClientHomeTab> createState() => _ClientHomeTabState();
}

class _ClientHomeTabState extends State<ClientHomeTab> {
  var _loading = true;
  String? _nombre;
  String? _email;
  String? _error;
  /// Resumen IA bajo «Resumen» (cliente): categoría corta / título auxiliar.
  String? _iaHeadline;
  /// Texto principal (resumen para el usuario).
  String? _iaBody;
  /// Hasta tres sugerencias inmediatas prioritarias (si las devuelve el backend).
  final List<String> _iaTips = <String>[];
  var _iaLoading = false;
  var _iaChecked = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final me = await widget.profileApi.fetchProfile();
      if (!mounted) {
        return;
      }
      setState(() {
        _nombre = me.nombre.trim().isNotEmpty ? me.nombre : null;
        _email = me.email;
        _loading = false;
      });
      if (!widget.isTechnician && widget.incidentsApi != null) {
        unawaited(_loadIaSnippet());
      }
    } on SessionExpiredException {
      if (mounted) {
        widget.onSessionExpired();
      }
    } on ApiClientException catch (e) {
      if (mounted) {
        setState(() {
          _loading = false;
          _error = e.message;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          _loading = false;
          _error = 'No se pudo conectar con el servidor';
        });
      }
    }
  }

  Future<void> _loadIaSnippet() async {
    final api = widget.incidentsApi;
    if (api == null || !mounted || widget.isTechnician) {
      return;
    }
    setState(() {
      _iaLoading = true;
      _iaChecked = false;
      _iaHeadline = null;
      _iaBody = null;
      _iaTips.clear();
    });
    try {
      final page = await api.listIncidents(page: 1, pageSize: 12);
      for (final row in page.items) {
        if (!mounted) {
          return;
        }
        final structured = await api.getLastAnalisisIa(row.id);
        if (structured != null && structured.isNotEmpty) {
          final tipo = '${structured['tipo_incidente'] ?? ''}'.trim();
          final esp = '${structured['especialidad_requerida'] ?? ''}'.trim();
          final rc = '${structured['resumen_cliente'] ?? ''}'.trim();
          final tips = structured['recomendaciones_inmediatas'];
          _iaHeadline = [
            if (tipo.isNotEmpty) _labelTipoIncidente(tipo),
            if (esp.isNotEmpty) esp,
          ].join(' · ');
          if (_iaHeadline!.isEmpty) {
            _iaHeadline = 'Asistencia sugerida';
          }
          if (rc.isNotEmpty) {
            _iaBody = _ellipsis(rc, 360);
          }
          _iaTips.clear();
          if (tips is List) {
            for (final t in tips) {
              final s = '$t'.trim();
              if (s.isEmpty) continue;
              _iaTips.add(s);
              if (_iaTips.length >= 4) break;
            }
          }
          if (mounted) {
            setState(() {
              _iaLoading = false;
              _iaChecked = true;
            });
          }
          return;
        }
        try {
          final detail = await api.getIncident(row.id);
          if (!mounted) {
            return;
          }
          final cat = (detail.categoriaIa ?? '').trim();
          final res = (detail.resumenIa ?? '').trim();
          if (cat.isEmpty && res.isEmpty) {
            continue;
          }
          _iaHeadline = cat.isNotEmpty ? cat : 'Resumen IA';
          if (res.isNotEmpty) {
            _iaBody = _ellipsis(res, 360);
          }
          final ar = detail.aiResult;
          final ra = ar == null ? null : '${ar['resumen_automatico'] ?? ''}'.trim();
          if ((_iaBody == null || _iaBody!.isEmpty) && ra != null && ra.isNotEmpty) {
            _iaBody = _ellipsis(ra, 360);
          }
          _iaTips.clear();
          if (!mounted) {
            return;
          }
          setState(() {
            _iaLoading = false;
            _iaChecked = true;
          });
          return;
        } on ApiClientException {
          continue;
        }
      }
    } on SessionExpiredException {
      widget.onSessionExpired();
    } catch (_) {
      /* sin bloquear inicio si falla el extra */
    }
    if (mounted) {
      setState(() {
        _iaLoading = false;
        _iaChecked = true;
      });
    }
  }

  static String _labelTipoIncidente(String raw) {
    const m = <String, String>{
      'bateria_descargada': 'Batería descargada',
      'pinchazo': 'Pinchazo',
      'choque': 'Choque / accidente',
      'sobrecalentamiento': 'Sobrecalentamiento',
      'falla_motor': 'Falla de motor',
      'otro': 'Incidente general',
    };
    return m[raw.trim().toLowerCase()] ?? raw;
  }

  static String _ellipsis(String s, int max) {
    final t = s.trim();
    if (t.length <= max) return t;
    return '${t.substring(0, max).trim()}…';
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;

    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.cloud_off_outlined, size: 48, color: scheme.onSurfaceVariant),
              const SizedBox(height: AppSpacing.md),
              Text(_error!, textAlign: TextAlign.center),
              const SizedBox(height: AppSpacing.lg),
              FilledButton.tonalIcon(
                onPressed: _load,
                icon: const Icon(Icons.refresh_rounded),
                label: const Text('Reintentar'),
              ),
            ],
          ),
        ),
      );
    }

    final greeting = _nombre != null ? 'Hola, $_nombre' : 'Hola';
    return RefreshIndicator(
      onRefresh: _load,
      color: scheme.primary,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(AppSpacing.lg, AppSpacing.md, AppSpacing.lg, 100),
        children: [
          Text(
            greeting,
            style: AppTextStyles.title(context).copyWith(letterSpacing: -0.4),
          ),
          if (_email != null) ...[
            const SizedBox(height: AppSpacing.xxs),
            Text(
              _email!,
              style: AppTextStyles.bodyMedium(context),
            ),
          ],
          const SizedBox(height: AppSpacing.xl),
          Text(
            'Resumen',
            style: AppTextStyles.sectionTitle(context),
          ),
          const SizedBox(height: AppSpacing.sm),
          Text(
            widget.isTechnician
                ? 'Desde Mis asignados ves los viajes que te asignaron o aceptaste y podés avanzar el estado del servicio.'
                : 'Desde acá podés gestionar tus vehículos y revisar tus emergencias en Actividad.',
            style: AppTextStyles.bodyMedium(context),
          ),
          if (!widget.isTechnician && widget.incidentsApi != null) ...[
            const SizedBox(height: AppSpacing.md),
            if (_iaLoading)
              const Padding(
                padding: EdgeInsets.only(bottom: AppSpacing.sm),
                child: LinearProgressIndicator(minHeight: 3),
              ),
            if (!_iaLoading &&
                ((_iaHeadline != null && _iaHeadline!.trim().isNotEmpty) ||
                    (_iaBody != null && _iaBody!.trim().isNotEmpty) ||
                    _iaTips.isNotEmpty))
              Card(
                elevation: 0,
                color: scheme.primaryContainer.withValues(alpha: 0.42),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                child: Padding(
                  padding: const EdgeInsets.all(AppSpacing.lg),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Icon(Icons.auto_awesome_outlined, color: scheme.primary, size: 22),
                          const SizedBox(width: AppSpacing.sm),
                          Expanded(
                            child: Text(
                              'Sugerencias de IA',
                              style: AppTextStyles.subtitle(context).copyWith(fontWeight: FontWeight.w700),
                            ),
                          ),
                        ],
                      ),
                      if (_iaHeadline != null && _iaHeadline!.trim().isNotEmpty) ...[
                        const SizedBox(height: AppSpacing.sm),
                        Text(
                          _iaHeadline!,
                          style: AppTextStyles.bodyMedium(context).copyWith(fontWeight: FontWeight.w600),
                        ),
                      ],
                      if (_iaBody != null && _iaBody!.trim().isNotEmpty) ...[
                        const SizedBox(height: AppSpacing.xs),
                        Text(_iaBody!, style: AppTextStyles.bodyMedium(context)),
                      ],
                      for (final t in _iaTips) ...[
                        const SizedBox(height: AppSpacing.sm),
                        Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Padding(
                              padding: const EdgeInsets.only(top: 2),
                              child: Icon(Icons.arrow_right_rounded, size: 18, color: scheme.primary),
                            ),
                            Expanded(child: Text(t, style: AppTextStyles.bodyMedium(context))),
                          ],
                        ),
                      ],
                      if (widget.onOpenIncidents != null) ...[
                        const SizedBox(height: AppSpacing.sm),
                        Align(
                          alignment: Alignment.centerRight,
                          child: TextButton(
                            onPressed: widget.onOpenIncidents,
                            child: const Text('Ver mis emergencias'),
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              )
            else if (_iaChecked && !_iaLoading && _iaHeadline == null && (_iaBody == null || _iaBody!.isEmpty) && _iaTips.isEmpty)
              Padding(
                padding: const EdgeInsets.only(bottom: AppSpacing.xs),
                child: Text(
                  'Cuando tengas emergencias procesadas por la IA, acá aparecerá un resumen breve y consejos sobre la más reciente.',
                  style: AppTextStyles.bodyMedium(context).copyWith(color: scheme.onSurfaceVariant),
                ),
              ),
          ],
          const SizedBox(height: AppSpacing.lg),
          if (widget.onReportEmergency != null) ...[
            PrimaryButton(
              label: 'Reportar emergencia',
              icon: Icons.emergency_outlined,
              onPressed: widget.onReportEmergency,
            ),
            const SizedBox(height: AppSpacing.md),
          ],
          if (widget.onOpenIncidents != null) ...[
            Card(
              child: InkWell(
                borderRadius: BorderRadius.circular(12),
                onTap: widget.onOpenIncidents,
                child: Padding(
                  padding: const EdgeInsets.all(AppSpacing.lg),
                  child: Row(
                    children: [
                      Icon(
                        widget.isTechnician ? Icons.assignment_turned_in_outlined : Icons.history_outlined,
                        size: 32,
                        color: scheme.primary,
                      ),
                      const SizedBox(width: AppSpacing.md),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              widget.isTechnician ? 'Mis asignados' : 'Mis emergencias',
                              style: AppTextStyles.subtitle(context).copyWith(fontWeight: FontWeight.w700),
                            ),
                            const SizedBox(height: AppSpacing.xxs),
                            Text(
                              widget.isTechnician
                                  ? 'Viajes asignados a vos y estado de cada uno.'
                                  : 'Ver incidencias reportadas y su estado.',
                              style: AppTextStyles.bodyMedium(context),
                            ),
                          ],
                        ),
                      ),
                      Icon(Icons.chevron_right_rounded, color: scheme.onSurfaceVariant),
                    ],
                  ),
                ),
              ),
            ),
            const SizedBox(height: AppSpacing.md),
          ],
          if (!widget.isTechnician) ...[
            Card(
              child: InkWell(
                borderRadius: BorderRadius.circular(12),
                onTap: widget.onOpenVehicles,
                child: Padding(
                  padding: const EdgeInsets.all(AppSpacing.lg),
                  child: Row(
                    children: [
                      Icon(Icons.directions_car_outlined, size: 32, color: scheme.primary),
                      const SizedBox(width: AppSpacing.md),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Mis vehículos',
                              style: AppTextStyles.subtitle(context).copyWith(fontWeight: FontWeight.w700),
                            ),
                            const SizedBox(height: AppSpacing.xxs),
                            Text(
                              'Listado, alta, edición y baja de vehículos.',
                              style: AppTextStyles.bodyMedium(context),
                            ),
                          ],
                        ),
                      ),
                      Icon(Icons.chevron_right_rounded, color: scheme.onSurfaceVariant),
                    ],
                  ),
                ),
              ),
            ),
            const SizedBox(height: AppSpacing.md),
            PrimaryButton(
              label: 'Agregar vehículo',
              icon: Icons.add_rounded,
              onPressed: widget.onAddVehicle,
            ),
          ],
        ],
      ),
    );
  }
}
