import 'package:flutter/material.dart';

import '../../../core/authorized_client.dart' show ApiClientException, SessionExpiredException;
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../../core/widgets/primary_button.dart';
import '../data/profile_api.dart';

/// Client home: summary and shortcuts (not the vehicle list).
class ClientHomeTab extends StatefulWidget {
  const ClientHomeTab({
    super.key,
    required this.profileApi,
    required this.onSessionExpired,
    required this.onOpenVehicles,
    required this.onAddVehicle,
    this.onOpenIncidents,
    this.onReportEmergency,
    this.isTechnician = false,
  });

  final ProfileApi profileApi;
  final VoidCallback onSessionExpired;
  final VoidCallback onOpenVehicles;
  final VoidCallback onAddVehicle;

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
