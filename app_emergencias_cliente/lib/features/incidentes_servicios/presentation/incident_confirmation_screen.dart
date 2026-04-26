import 'package:flutter/material.dart';

import '../../../core/auth_api.dart';
import '../../../core/auth_storage.dart';
import '../../../core/authorized_client.dart' show ApiClientException, AuthorizedClient, SessionExpiredException;
import '../../../core/theme/app_spacing.dart';
import '../../../core/widgets/primary_button.dart';
import '../../usuario_autenticacion/presentation/session_navigation.dart';
import '../data/incidents_api.dart';
import '../domain/incident.dart';

/// Confirmación con `GET /incidentes-servicios/incidentes/{id}`.
class IncidentConfirmationScreen extends StatefulWidget {
  const IncidentConfirmationScreen({
    super.key,
    required this.storage,
    required this.authApi,
    required this.incidenteId,
    this.initialWarnings = const [],
  });

  final AuthStorage storage;
  final AuthApi authApi;
  final int incidenteId;
  final List<String> initialWarnings;

  @override
  State<IncidentConfirmationScreen> createState() => _IncidentConfirmationScreenState();
}

class _IncidentConfirmationScreenState extends State<IncidentConfirmationScreen> {
  late final IncidentsApi _api = IncidentsApi(AuthorizedClient(storage: widget.storage));

  var _loading = true;
  String? _error;
  IncidentDetail? _detail;

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
      final d = await _api.getIncidentById(widget.incidenteId);
      if (!mounted) {
        return;
      }
      setState(() {
        _detail = d;
        _loading = false;
      });
    } on SessionExpiredException {
      if (mounted) {
        navigateToLoginReplacingStack(context: context, storage: widget.storage, authApi: widget.authApi);
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
    return Scaffold(
      appBar: AppBar(
        title: const Text('Emergencia registrada'),
        leading: IconButton(
          icon: const Icon(Icons.close_rounded),
          onPressed: () => Navigator.of(context).popUntil((r) => r.isFirst),
        ),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(AppSpacing.lg),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.cloud_off_outlined, size: 48, color: scheme.onSurfaceVariant),
                        const SizedBox(height: AppSpacing.md),
                        Text(_error!, textAlign: TextAlign.center),
                        const SizedBox(height: AppSpacing.lg),
                        SecondaryButton(
                          label: 'Reintentar',
                          icon: Icons.refresh_rounded,
                          onPressed: _load,
                        ),
                      ],
                    ),
                  ),
                )
              : ListView(
                  padding: const EdgeInsets.all(AppSpacing.lg),
                  children: [
                    if (widget.initialWarnings.isNotEmpty) ...[
                      Card(
                        color: scheme.errorContainer.withValues(alpha: 0.35),
                        child: Padding(
                          padding: const EdgeInsets.all(AppSpacing.md),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                children: [
                                  Icon(Icons.warning_amber_rounded, color: scheme.error),
                                  const SizedBox(width: AppSpacing.sm),
                                  Expanded(
                                    child: Text(
                                      'Parte de las evidencias no se subieron',
                                      style: Theme.of(context).textTheme.titleSmall?.copyWith(
                                            fontWeight: FontWeight.w700,
                                            color: scheme.onErrorContainer,
                                          ),
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: AppSpacing.sm),
                              for (final w in widget.initialWarnings)
                                Padding(
                                  padding: const EdgeInsets.only(bottom: AppSpacing.xxs),
                                  child: Text(w, style: Theme.of(context).textTheme.bodySmall),
                                ),
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(height: AppSpacing.md),
                    ],
                    Icon(Icons.check_circle_rounded, size: 56, color: scheme.primary),
                    const SizedBox(height: AppSpacing.md),
                    Text(
                      'Tu reporte quedó registrado.',
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800),
                    ),
                    const SizedBox(height: AppSpacing.sm),
                    if (_detail != null) ...[
                      Text(
                        'Incidente #${_detail!.id} · estado ${_detail!.estado}',
                        style: Theme.of(context).textTheme.bodyLarge,
                      ),
                      const SizedBox(height: AppSpacing.lg),
                      _kv(context, 'Vehículo', '#${_detail!.vehiculoId}'),
                      _kv(context, 'Ubicación', '${_detail!.latitud.toStringAsFixed(5)}, ${_detail!.longitud.toStringAsFixed(5)}'),
                      if (_detail!.descripcionTexto != null && _detail!.descripcionTexto!.isNotEmpty)
                        _kv(context, 'Descripción', _detail!.descripcionTexto!),
                      _kv(context, 'Evidencias', '${_detail!.evidencias.length} adjunto(s)'),
                    ],
                    const SizedBox(height: AppSpacing.xl),
                    PrimaryButton(
                      label: 'Ver estado de la solicitud',
                      icon: Icons.track_changes_outlined,
                      onPressed: () {
                        showDialog<void>(
                          context: context,
                          builder: (ctx) => AlertDialog(
                            title: const Text('Seguimiento'),
                            content: const Text(
                              'El seguimiento detallado desde esta pantalla estará disponible en una próxima versión. '
                              'Podés ver el estado en la pestaña Actividad.',
                            ),
                            actions: [
                              TextButton(
                                onPressed: () => Navigator.of(ctx).pop(),
                                child: const Text('Entendido'),
                              ),
                            ],
                          ),
                        );
                      },
                    ),
                    const SizedBox(height: AppSpacing.sm),
                    SecondaryButton(
                      label: 'Volver al inicio',
                      icon: Icons.home_outlined,
                      onPressed: () => Navigator.of(context).popUntil((r) => r.isFirst),
                    ),
                  ],
                ),
    );
  }

  Widget _kv(BuildContext context, String k, String v) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 110,
            child: Text(
              k,
              style: Theme.of(context).textTheme.labelLarge?.copyWith(color: Theme.of(context).colorScheme.onSurfaceVariant),
            ),
          ),
          Expanded(child: Text(v, style: Theme.of(context).textTheme.bodyMedium)),
        ],
      ),
    );
  }
}
