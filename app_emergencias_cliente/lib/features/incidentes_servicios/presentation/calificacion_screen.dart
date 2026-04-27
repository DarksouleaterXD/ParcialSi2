import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';

import '../../../core/auth_storage.dart';
import '../../../core/authorized_client.dart';
import '../../../core/theme/app_spacing.dart';
import '../data/incidents_api.dart';
import '../data/incidents_repository.dart';
import '../../pagos/data/pagos_api.dart';
import '../domain/incident.dart';

class CalificacionScreen extends StatefulWidget {
  const CalificacionScreen({
    super.key,
    required this.storage,
    required this.incidenteId,
    required this.onSessionExpired,
  });

  final AuthStorage storage;
  final int incidenteId;
  final VoidCallback onSessionExpired;

  @override
  State<CalificacionScreen> createState() => _CalificacionScreenState();
}

class _CalificacionScreenState extends State<CalificacionScreen> {
  late final AuthorizedClient _authorizedClient = AuthorizedClient(storage: widget.storage);
  late final IncidentsRepository _repo = IncidentsRepository(IncidentsApi(_authorizedClient));
  late final IncidentsApi _incidentsApi = IncidentsApi(_authorizedClient);
  late final PagosApi _pagosApi = PagosApi(_authorizedClient);
  final TextEditingController _commentController = TextEditingController();

  int _rating = 5;
  bool _submitting = false;
  bool _loadingGate = true;
  String? _inlineError;
  IncidentDetail? _incident;
  PagoListItem? _incidentPago;

  @override
  void dispose() {
    _commentController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_submitting) {
      return;
    }
    final messenger = ScaffoldMessenger.of(context);
    setState(() {
      _submitting = true;
      _inlineError = null;
    });
    try {
      await _repo.calificarIncidente(widget.incidenteId, _rating, _commentController.text);
      if (!mounted) {
        return;
      }
      messenger.showSnackBar(
        const SnackBar(content: Text('Gracias por tu calificación. Seguimos mejorando para vos.')),
      );
      await _loadGateData();
      if (mounted) {
        Navigator.of(context).pop(true);
      }
    } on SessionExpiredException {
      if (mounted) {
        widget.onSessionExpired();
      }
    } on ApiClientException catch (e) {
      if (mounted) {
        setState(() {
          if (e.statusCode == 409) {
            _inlineError = 'Este servicio ya fue calificado.';
          } else if (e.statusCode == 403) {
            _inlineError = 'No tienes permiso para calificar este servicio.';
          } else if (e.statusCode == 400) {
            _inlineError = e.message;
          } else {
            _inlineError = e.message;
          }
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          _inlineError = 'No se pudo enviar la calificación.';
        });
      }
    } finally {
      if (mounted) {
        setState(() {
          _submitting = false;
        });
      }
    }
  }

  bool get _isServiceFinalizado {
    final status = (_incident?.estado ?? '').trim().toLowerCase().replaceAll(' ', '_');
    return status == 'finalizado' || status == 'pagado';
  }

  bool get _canShowForm {
    if (!_isServiceFinalizado) {
      return false;
    }
    final pago = _incidentPago;
    if (pago == null) {
      return true;
    }
    final pagoEstado = pago.estado.trim().toLowerCase();
    return pagoEstado == 'pagado' || pagoEstado == 'confirmado' || pagoEstado == 'completado' || pagoEstado == 'paid';
  }

  Future<void> _loadGateData() async {
    setState(() {
      _loadingGate = true;
      _inlineError = null;
    });
    try {
      final detail = await _incidentsApi.getIncidentById(widget.incidenteId);
      PagoListItem? pago;
      try {
        final pagos = await _pagosApi.listPagos(page: 1, pageSize: 100);
        for (final item in pagos.items) {
          if (item.incidenteId == widget.incidenteId) {
            pago = item;
            break;
          }
        }
      } catch (_) {
        // Si la consulta de pagos falla, dejamos solo la validación por estado de servicio.
      }
      if (!mounted) {
        return;
      }
      setState(() {
        _incident = detail;
        _incidentPago = pago;
        _loadingGate = false;
      });
    } on SessionExpiredException {
      if (mounted) {
        widget.onSessionExpired();
      }
    } on ApiClientException catch (e) {
      if (!mounted) {
        return;
      }
      setState(() {
        _loadingGate = false;
        _inlineError = e.message;
      });
    } catch (e) {
      if (kDebugMode) {
        debugPrint('CalificacionScreen gate load failed: $e');
      }
      if (!mounted) {
        return;
      }
      setState(() {
        _loadingGate = false;
        _inlineError = 'No se pudo cargar el estado del servicio.';
      });
    }
  }

  @override
  void initState() {
    super.initState();
    _loadGateData();
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final incidentEstado = _incident?.estado ?? '—';
    final pagoEstado = _incidentPago?.estado;
    return Scaffold(
      appBar: AppBar(title: Text('Calificar servicio #${widget.incidenteId}')),
      body: _loadingGate
          ? const Center(child: CircularProgressIndicator())
          : ListView(
        padding: const EdgeInsets.all(AppSpacing.lg),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(AppSpacing.lg),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Estado del servicio: $incidentEstado',
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: scheme.onSurfaceVariant),
                  ),
                  if (pagoEstado != null) ...[
                    const SizedBox(height: AppSpacing.xs),
                    Text(
                      'Estado del pago: $pagoEstado',
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: scheme.onSurfaceVariant),
                    ),
                  ],
                  const SizedBox(height: AppSpacing.md),
                  Text(
                    '¿Cómo fue tu experiencia?',
                    style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800),
                  ),
                  const SizedBox(height: AppSpacing.md),
                  if (!_canShowForm) ...[
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(AppSpacing.md),
                      decoration: BoxDecoration(
                        color: const Color(0xFFFFF7ED),
                        border: Border.all(color: const Color(0xFFF97316).withValues(alpha: 0.35)),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Text(
                        !_isServiceFinalizado
                            ? 'La calificación se habilita cuando el servicio está finalizado.'
                            : 'La calificación se habilita cuando el pago asociado está pagado.',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                    ),
                    const SizedBox(height: AppSpacing.md),
                  ],
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: List<Widget>.generate(5, (index) {
                      final value = index + 1;
                      return IconButton(
                        onPressed: _submitting || !_canShowForm
                            ? null
                            : () {
                                setState(() {
                                  _rating = value;
                                });
                              },
                        iconSize: 34,
                        color: value <= _rating ? const Color(0xFFF59E0B) : scheme.outlineVariant,
                        icon: Icon(value <= _rating ? Icons.star_rounded : Icons.star_border_rounded),
                      );
                    }),
                  ),
                  const SizedBox(height: AppSpacing.sm),
                  Text(
                    'Puntuación: $_rating / 5',
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: scheme.onSurfaceVariant),
                  ),
                  const SizedBox(height: AppSpacing.lg),
                  TextField(
                    controller: _commentController,
                    enabled: !_submitting,
                    maxLength: 500,
                    minLines: 3,
                    maxLines: 5,
                    decoration: const InputDecoration(
                      labelText: 'Comentario (opcional)',
                      hintText: 'Contanos cómo fue la atención del técnico.',
                      border: OutlineInputBorder(),
                    ),
                  ),
                  if (_inlineError != null) ...[
                    const SizedBox(height: AppSpacing.sm),
                    Text(
                      _inlineError!,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: scheme.error),
                    ),
                  ],
                  const SizedBox(height: AppSpacing.md),
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton(
                      style: FilledButton.styleFrom(
                        backgroundColor: const Color(0xFFF97316),
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(vertical: 16),
                      ),
                      onPressed: _submitting || !_canShowForm ? null : _submit,
                      child: _submitting
                          ? const SizedBox(
                              width: 20,
                              height: 20,
                              child: CircularProgressIndicator(strokeWidth: 2.2, color: Colors.white),
                            )
                          : const Text('Enviar Calificación'),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
