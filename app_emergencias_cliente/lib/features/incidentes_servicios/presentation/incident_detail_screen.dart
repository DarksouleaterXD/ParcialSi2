import 'dart:async' show unawaited;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_stripe/flutter_stripe.dart' hide Card;

import '../../../core/auth_api.dart';
import '../../../core/auth_storage.dart';
import '../../../core/authorized_client.dart' show ApiClientException, AuthorizedClient, SessionExpiredException;
import '../../../core/theme/app_spacing.dart';
import '../data/incidents_api.dart';
import '../data/incidents_repository.dart';
import '../domain/incident.dart';
import '../../pagos/data/pagos_api.dart';
import '../../pagos/data/pagos_repository.dart';
import 'calificacion_screen.dart';
import 'widgets/incident_status_style.dart';

/// Detalle de incidente y acciones según rol (cliente vs técnico asignado).
class IncidentDetailScreen extends StatefulWidget {
  const IncidentDetailScreen({
    super.key,
    required this.storage,
    required this.authApi,
    required this.incidenteId,
    required this.onSessionExpired,
    this.vehiculoLabel,
    this.isTechnician = false,
    this.clienteNombre,
  });

  final AuthStorage storage;
  final AuthApi authApi;
  final int incidenteId;
  final VoidCallback onSessionExpired;
  final String? vehiculoLabel;
  final bool isTechnician;
  final String? clienteNombre;

  @override
  State<IncidentDetailScreen> createState() => _IncidentDetailScreenState();
}

class _IncidentDetailScreenState extends State<IncidentDetailScreen> {
  late final AuthorizedClient _authorizedClient = AuthorizedClient(storage: widget.storage);
  late final IncidentsApi _api = IncidentsApi(_authorizedClient);
  late final IncidentsRepository _repo = IncidentsRepository(_api);
  late final PagosRepository _pagosRepo = PagosRepository(PagosApi(_authorizedClient));

  var _loading = true;
  var _servicioProgresoBusy = false;
  var _pagoBusy = false;
  String? _error;
  IncidentDetail? _detail;
  /// Talleres candidatos (1.5.5) luego de IA `completed` en servidor.
  List<Map<String, dynamic>>? _candidatosAsignacion;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
      _candidatosAsignacion = null;
    });
    try {
      final d = await _api.getIncidentById(widget.incidenteId);
      List<Map<String, dynamic>>? cands;
      if (!widget.isTechnician && (d.aiStatus ?? '').toLowerCase() == 'completed') {
        try {
          final m = await _api.getAssignmentCandidates(widget.incidenteId);
          final list = m['candidates'];
          if (list is List) {
            final out = <Map<String, dynamic>>[];
            for (final e in list) {
              if (e is Map) {
                out.add(Map<String, dynamic>.from(e));
              }
            }
            cands = out.isEmpty ? null : out;
          }
        } on ApiClientException {
          cands = null;
        } catch (_) {
          cands = null;
        }
      }
      if (!mounted) {
        return;
      }
      setState(() {
        _detail = d;
        _candidatosAsignacion = cands;
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

  Future<void> _showCancelConfirmationDialog() async {
    if (!mounted) {
      return;
    }
    var submitting = false;
    final messenger = ScaffoldMessenger.of(context);
    await showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (dialogContext) {
        return StatefulBuilder(
          builder: (context, setDialogState) {
            final scheme = Theme.of(context).colorScheme;
            return PopScope(
              canPop: !submitting,
              child: AlertDialog(
                title: const Text('¿Cancelar solicitud?'),
                content: const Text(
                  'Si cancelás ahora, el taller asignado será notificado y deberás crear un nuevo reporte si necesitás asistencia.',
                ),
                actions: [
                  TextButton(
                    onPressed: submitting ? null : () => Navigator.of(dialogContext).pop(),
                    child: const Text('No, mantener'),
                  ),
                  FilledButton(
                    style: FilledButton.styleFrom(
                      backgroundColor: scheme.error,
                      foregroundColor: scheme.onError,
                    ),
                    onPressed: submitting
                        ? null
                        : () async {
                            setDialogState(() {
                              submitting = true;
                            });
                            try {
                              final updated = await _repo.cancelIncident(widget.incidenteId);
                              if (!dialogContext.mounted) {
                                return;
                              }
                              Navigator.of(dialogContext).pop();
                              if (!mounted) {
                                return;
                              }
                              setState(() {
                                _detail = updated;
                                _error = null;
                                _loading = false;
                              });
                              messenger.showSnackBar(
                                const SnackBar(content: Text('Solicitud cancelada')),
                              );
                            } on SessionExpiredException {
                              if (dialogContext.mounted) {
                                Navigator.of(dialogContext).pop();
                              }
                              if (mounted) {
                                widget.onSessionExpired();
                              }
                            } on ApiClientException catch (e) {
                              if (dialogContext.mounted) {
                                setDialogState(() {
                                  submitting = false;
                                });
                              }
                              if (!mounted) {
                                return;
                              }
                              String msg;
                              if (e.statusCode == 409) {
                                final m = e.message.toLowerCase();
                                if (m.contains('ya fue cancelada') ||
                                    m.contains('ya estaba') ||
                                    m.contains('cancelada.')) {
                                  msg = e.message;
                                } else {
                                  msg = 'El técnico ya está en camino, no podés cancelar ahora';
                                }
                              } else {
                                msg = 'Error al cancelar';
                              }
                              messenger.showSnackBar(
                                SnackBar(content: Text(msg)),
                              );
                            } catch (_) {
                              if (dialogContext.mounted) {
                                setDialogState(() {
                                  submitting = false;
                                });
                              }
                              if (mounted) {
                                messenger.showSnackBar(
                                  const SnackBar(content: Text('Error al cancelar')),
                                );
                              }
                            }
                          },
                    child: submitting
                        ? SizedBox(
                            width: 24,
                            height: 24,
                            child: CircularProgressIndicator(
                              strokeWidth: 2.5,
                              color: scheme.onError,
                            ),
                          )
                        : const Text('Sí, cancelar'),
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }

  Future<void> _showDeleteConfirmationDialog() async {
    if (!mounted) {
      return;
    }
    var submitting = false;
    final messenger = ScaffoldMessenger.of(context);
    await showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (dialogContext) {
        return StatefulBuilder(
          builder: (context, setDialogState) {
            final scheme = Theme.of(context).colorScheme;
            return PopScope(
              canPop: !submitting,
              child: AlertDialog(
                title: const Text('¿Eliminar solicitud?'),
                content: const Text(
                  'Esta acción es permanente y eliminará evidencias y datos asociados de esta solicitud.',
                ),
                actions: [
                  TextButton(
                    onPressed: submitting ? null : () => Navigator.of(dialogContext).pop(),
                    child: const Text('Cancelar'),
                  ),
                  FilledButton(
                    style: FilledButton.styleFrom(
                      backgroundColor: scheme.error,
                      foregroundColor: scheme.onError,
                    ),
                    onPressed: submitting
                        ? null
                        : () async {
                            setDialogState(() {
                              submitting = true;
                            });
                            try {
                              await _repo.deleteIncident(widget.incidenteId);
                              if (!dialogContext.mounted) {
                                return;
                              }
                              Navigator.of(dialogContext).pop();
                              if (!mounted) {
                                return;
                              }
                              messenger.showSnackBar(
                                const SnackBar(content: Text('Solicitud eliminada')),
                              );
                              Navigator.of(context).pop();
                            } on SessionExpiredException {
                              if (dialogContext.mounted) {
                                Navigator.of(dialogContext).pop();
                              }
                              if (mounted) {
                                widget.onSessionExpired();
                              }
                            } on ApiClientException catch (e) {
                              if (dialogContext.mounted) {
                                setDialogState(() {
                                  submitting = false;
                                });
                              }
                              if (mounted) {
                                messenger.showSnackBar(
                                  SnackBar(content: Text(e.message.isEmpty ? 'No se pudo eliminar' : e.message)),
                                );
                              }
                            } catch (_) {
                              if (dialogContext.mounted) {
                                setDialogState(() {
                                  submitting = false;
                                });
                              }
                              if (mounted) {
                                messenger.showSnackBar(
                                  const SnackBar(content: Text('Error al eliminar la solicitud')),
                                );
                              }
                            }
                          },
                    child: submitting
                        ? SizedBox(
                            width: 24,
                            height: 24,
                            child: CircularProgressIndicator(
                              strokeWidth: 2.5,
                              color: scheme.onError,
                            ),
                          )
                        : const Text('Eliminar'),
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }

  static const Color _successGreen = Color(0xFF16A34A);
  static const Color _accentOrange = Color(0xFFF97316);
  static const double _montoPagoMvp = 15000.0;

  String _estadoNormalizado(String estado) => estado.trim().toLowerCase().replaceAll(' ', '_');

  bool _isEstadoFinalizado(String estado) => _estadoNormalizado(estado) == 'finalizado';

  bool _isEstadoPagado(String estado) => _estadoNormalizado(estado) == 'pagado';

  Future<void> _ejecutarAccionProgresoYRecargar(Future<void> Function() op, String successMessage) async {
    if (_servicioProgresoBusy) {
      return;
    }
    setState(() {
      _servicioProgresoBusy = true;
    });
    final messenger = ScaffoldMessenger.of(context);
    try {
      await op();
      if (!mounted) {
        return;
      }
      await _load();
      if (mounted) {
        messenger.showSnackBar(SnackBar(content: Text(successMessage)));
      }
    } on SessionExpiredException {
      if (mounted) {
        widget.onSessionExpired();
      }
    } on ApiClientException catch (e) {
      if (mounted) {
        messenger.showSnackBar(SnackBar(content: Text(e.message)));
      }
    } catch (_) {
      if (mounted) {
        messenger.showSnackBar(const SnackBar(content: Text('Error al actualizar el estado')));
      }
    } finally {
      if (mounted) {
        setState(() {
          _servicioProgresoBusy = false;
        });
      }
    }
  }

  Future<void> _showFinalizarConfirmationDialog() async {
    if (!mounted || _servicioProgresoBusy) {
      return;
    }
    var submitting = false;
    final messenger = ScaffoldMessenger.of(context);
    await showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (dialogContext) {
        return StatefulBuilder(
          builder: (context, setDialogState) {
            return PopScope(
              canPop: !submitting,
              child: AlertDialog(
                title: const Text('¿Finalizar el trabajo?'),
                content: const Text(
                  'Se marcará el servicio como finalizado. Asegurate de que el asistente vehicular quedó resuelto.',
                ),
                actions: [
                  TextButton(
                    onPressed: submitting ? null : () => Navigator.of(dialogContext).pop(),
                    child: const Text('Cancelar'),
                  ),
                  FilledButton(
                    style: FilledButton.styleFrom(
                      backgroundColor: _successGreen,
                      foregroundColor: Colors.white,
                    ),
                    onPressed: submitting
                        ? null
                        : () async {
                            setDialogState(() {
                              submitting = true;
                            });
                            try {
                              await _repo.markAsFinalizado(widget.incidenteId);
                              if (!dialogContext.mounted) {
                                return;
                              }
                              Navigator.of(dialogContext).pop();
                              if (!mounted) {
                                return;
                              }
                              setState(() {
                                _servicioProgresoBusy = true;
                              });
                              try {
                                await _load();
                                if (mounted) {
                                  messenger.showSnackBar(
                                    const SnackBar(content: Text('Trabajo finalizado')),
                                  );
                                }
                              } finally {
                                if (mounted) {
                                  setState(() {
                                    _servicioProgresoBusy = false;
                                  });
                                }
                              }
                            } on SessionExpiredException {
                              if (dialogContext.mounted) {
                                Navigator.of(dialogContext).pop();
                              }
                              if (mounted) {
                                widget.onSessionExpired();
                              }
                            } on ApiClientException catch (e) {
                              if (dialogContext.mounted) {
                                setDialogState(() {
                                  submitting = false;
                                });
                              }
                              if (mounted) {
                                messenger.showSnackBar(SnackBar(content: Text(e.message)));
                              }
                            } catch (_) {
                              if (dialogContext.mounted) {
                                setDialogState(() {
                                  submitting = false;
                                });
                              }
                              if (mounted) {
                                messenger.showSnackBar(
                                  const SnackBar(content: Text('Error al finalizar')),
                                );
                              }
                            }
                          },
                    child: submitting
                        ? const SizedBox(
                            width: 24,
                            height: 24,
                            child: CircularProgressIndicator(
                              strokeWidth: 2.5,
                              color: Colors.white,
                            ),
                          )
                        : const Text('Sí, finalizar'),
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }

  Future<void> _showPagoBottomSheet() async {
    if (!mounted || _pagoBusy) {
      return;
    }
    setState(() {
      _pagoBusy = true;
    });

    final messenger = ScaffoldMessenger.of(context);
    try {
      final clientSecret = await _pagosRepo.createPaymentIntent(widget.incidenteId);

      await Stripe.instance.initPaymentSheet(
        paymentSheetParameters: SetupPaymentSheetParameters(
          paymentIntentClientSecret: clientSecret,
          merchantDisplayName: 'Taller Inteligente',
        ),
      );

      await Stripe.instance.presentPaymentSheet();

      // If it reaches here, payment was successful. Notify backend.
      await _pagosRepo.procesarPago(widget.incidenteId, _montoPagoMvp, metodoPago: 'TARJETA');
      await _load();

      if (mounted) {
        await Navigator.of(context).push(
          MaterialPageRoute<void>(
            builder: (_) => CalificacionScreen(
              storage: widget.storage,
              incidenteId: widget.incidenteId,
              onSessionExpired: widget.onSessionExpired,
            ),
          ),
        );
      }
    } on StripeException catch (e) {
      if (mounted) {
        messenger.showSnackBar(
          SnackBar(content: Text('Pago cancelado o fallido: ${e.error.localizedMessage}')),
        );
      }
    } on SessionExpiredException {
      if (mounted) {
        widget.onSessionExpired();
      }
    } on ApiClientException catch (e) {
      if (mounted) {
        messenger.showSnackBar(
          SnackBar(content: Text(e.message.isEmpty ? 'Error al preparar el pago' : e.message)),
        );
      }
    } catch (_) {
      if (mounted) {
        messenger.showSnackBar(const SnackBar(content: Text('Error al preparar el pago')));
      }
    } finally {
      if (mounted) {
        setState(() {
          _pagoBusy = false;
        });
      }
    }
  }

  String _vehiculoDisplay(IncidentDetail d) {
    if (widget.vehiculoLabel != null && widget.vehiculoLabel!.isNotEmpty) {
      return widget.vehiculoLabel!;
    }
    return 'Vehículo #${d.vehiculoId}';
  }

  String _fechaDisplay(IncidentDetail d) {
    final t = d.createdAt?.toLocal();
    if (t == null) {
      return '—';
    }
    return '${t.day.toString().padLeft(2, '0')}/${t.month.toString().padLeft(2, '0')}/${t.year} '
        '${t.hour.toString().padLeft(2, '0')}:${t.minute.toString().padLeft(2, '0')}';
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;

    return Scaffold(
      appBar: AppBar(
        title: Text('Solicitud #${widget.incidenteId}'),
        actions: [
          IconButton(
            tooltip: 'Actualizar',
            onPressed: _loading ? null : () => _load(),
            icon: const Icon(Icons.refresh_rounded),
          ),
        ],
      ),
      body: _loading && _detail == null
          ? Center(child: CircularProgressIndicator(color: scheme.primary))
          : _error != null && _detail == null
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(AppSpacing.lg),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.error_outline_rounded, size: 48, color: scheme.onSurfaceVariant),
                        const SizedBox(height: AppSpacing.md),
                        Text(_error!, textAlign: TextAlign.center),
                        const SizedBox(height: AppSpacing.md),
                        FilledButton.tonal(
                          onPressed: _load,
                          child: const Text('Reintentar'),
                        ),
                      ],
                    ),
                  ),
                )
              : _detail == null
                  ? const SizedBox.shrink()
                  : RefreshIndicator(
                      color: scheme.primary,
                      onRefresh: _load,
                      child: ListView(
                        padding: const EdgeInsets.fromLTRB(
                          AppSpacing.md,
                          AppSpacing.md,
                          AppSpacing.md,
                          120,
                        ),
                        children: [
                          _buildSummary(context, _detail!),
                          const SizedBox(height: AppSpacing.md),
                          if (widget.isTechnician) ...[
                            _buildTechnicianContextPanel(context, _detail!),
                            const SizedBox(height: AppSpacing.sm),
                            Card(
                              child: Theme(
                                data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
                                child: ExpansionTile(
                                  tilePadding: const EdgeInsets.symmetric(
                                    horizontal: AppSpacing.md,
                                    vertical: AppSpacing.xs,
                                  ),
                                  title: Text(
                                    'Seguimiento del cliente (solo lectura)',
                                    style: Theme.of(context).textTheme.titleSmall?.copyWith(
                                          fontWeight: FontWeight.w800,
                                        ),
                                  ),
                                  childrenPadding: const EdgeInsets.fromLTRB(
                                    AppSpacing.md,
                                    0,
                                    AppSpacing.md,
                                    AppSpacing.md,
                                  ),
                                  children: [
                                    IgnorePointer(
                                      child: Opacity(
                                        opacity: 0.92,
                                        child: _buildTimeline(context, _detail!),
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ),
                          ] else if (!_isEstadoFinalizado(_detail!.estado) && !_isEstadoPagado(_detail!.estado))
                            _buildTimeline(context, _detail!),
                          if (!widget.isTechnician && _isEstadoFinalizado(_detail!.estado)) ...[
                            _buildPagoPendienteCard(context, _detail!),
                          ],
                          if (!widget.isTechnician && _isEstadoPagado(_detail!.estado)) ...[
                            _buildPagoCompletadoCard(context),
                          ],
                          if (!widget.isTechnician &&
                              _detail!.tecnicoId != null &&
                              !incidentEstadoIsPendiente(_detail!.estado) &&
                              !incidentEstadoIsCancelado(_detail!.estado)) ...[
                            const SizedBox(height: AppSpacing.md),
                            _buildTechnicianCard(context, _detail!),
                          ],
                          if (_showClienteIaCard(_detail!)) ...[
                            const SizedBox(height: AppSpacing.md),
                            _buildIaCard(context, _detail!),
                          ],
                          if (!widget.isTechnician &&
                              _candidatosAsignacion != null &&
                              _candidatosAsignacion!.isNotEmpty) ...[
                            const SizedBox(height: AppSpacing.md),
                            _buildCandidatosAsignacionCard(context, _candidatosAsignacion!),
                          ],
                          if (widget.isTechnician) ...[
                            const SizedBox(height: AppSpacing.lg),
                            if (incidentTechnicianShowsEnCaminoAction(_detail!.estado))
                              _botonProgresoOutlineGrande(
                                context: context,
                                label: 'Avisar que estoy en camino',
                                onPressed: _servicioProgresoBusy
                                    ? null
                                    : () => _ejecutarAccionProgresoYRecargar(
                                          () async {
                                            await _repo.markAsEnCamino(widget.incidenteId);
                                          },
                                          'Listo, estás en camino',
                                        ),
                                busy: _servicioProgresoBusy,
                              ),
                            if (incidentTechnicianShowsIniciarTrabajoAction(_detail!.estado))
                              _botonProgresoOutlineGrande(
                                context: context,
                                label: 'Llegué, iniciar trabajo',
                                onPressed: _servicioProgresoBusy
                                    ? null
                                    : () => _ejecutarAccionProgresoYRecargar(
                                          () async {
                                            await _repo.markAsEnProceso(widget.incidenteId);
                                          },
                                          'Trabajo en curso',
                                        ),
                                busy: _servicioProgresoBusy,
                              ),
                            if (incidentTechnicianShowsFinalizarTrabajoAction(_detail!.estado))
                              _botonProgresoVerdeGrande(
                                context: context,
                                label: 'Finalizar trabajo',
                                onPressed: _servicioProgresoBusy
                                    ? null
                                    : () => unawaited(_showFinalizarConfirmationDialog()),
                                busy: _servicioProgresoBusy,
                              ),
                          ],
                          if (!widget.isTechnician && incidentEstadoCanClientCancel(_detail!.estado)) ...[
                            const SizedBox(height: AppSpacing.lg),
                            SizedBox(
                              width: double.infinity,
                              child: OutlinedButton.icon(
                                style: OutlinedButton.styleFrom(
                                  foregroundColor: scheme.error,
                                  side: BorderSide(color: scheme.error.withValues(alpha: 0.65)),
                                ),
                                onPressed: _showCancelConfirmationDialog,
                                icon: const Icon(Icons.cancel_outlined),
                                label: const Text('Cancelar Solicitud'),
                              ),
                            ),
                          ],
                          if (!widget.isTechnician && incidentEstadoCanClientDelete(_detail!.estado)) ...[
                            const SizedBox(height: AppSpacing.sm),
                            SizedBox(
                              width: double.infinity,
                              child: OutlinedButton.icon(
                                style: OutlinedButton.styleFrom(
                                  foregroundColor: scheme.error,
                                  side: BorderSide(color: scheme.error.withValues(alpha: 0.45)),
                                ),
                                onPressed: _showDeleteConfirmationDialog,
                                icon: const Icon(Icons.delete_outline_rounded),
                                label: const Text('Eliminar Solicitud'),
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),
    );
  }

  Widget _botonProgresoOutlineGrande({
    required BuildContext context,
    required String label,
    required VoidCallback? onPressed,
    required bool busy,
  }) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.md),
      child: OutlinedButton(
        style: OutlinedButton.styleFrom(
          foregroundColor: _accentOrange,
          side: const BorderSide(color: _accentOrange, width: 2),
          padding: const EdgeInsets.symmetric(vertical: 18, horizontal: AppSpacing.lg),
          textStyle: Theme.of(context).textTheme.titleSmall?.copyWith(
                fontWeight: FontWeight.w800,
                letterSpacing: 0.2,
              ),
        ),
        onPressed: onPressed,
        child: busy
            ? const SizedBox(
                width: 24,
                height: 24,
                child: CircularProgressIndicator(
                  strokeWidth: 2.5,
                  color: _accentOrange,
                ),
              )
            : Text(label, textAlign: TextAlign.center),
      ),
    );
  }

  Widget _botonProgresoVerdeGrande({
    required BuildContext context,
    required String label,
    required VoidCallback? onPressed,
    required bool busy,
  }) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.md),
      child: FilledButton(
        style: FilledButton.styleFrom(
          backgroundColor: _successGreen,
          foregroundColor: Colors.white,
          padding: const EdgeInsets.symmetric(vertical: 18, horizontal: AppSpacing.lg),
          textStyle: Theme.of(context).textTheme.titleSmall?.copyWith(
                fontWeight: FontWeight.w800,
                letterSpacing: 0.2,
              ),
        ),
        onPressed: onPressed,
        child: busy
            ? const SizedBox(
                width: 24,
                height: 24,
                child: CircularProgressIndicator(
                  strokeWidth: 2.5,
                  color: Colors.white,
                ),
              )
            : Text(label, textAlign: TextAlign.center),
      ),
    );
  }

  Widget _buildTechnicianContextPanel(BuildContext context, IncidentDetail d) {
    final scheme = Theme.of(context).colorScheme;
    if (incidentEstadoIsCancelado(d.estado)) {
      return Card(
        color: scheme.errorContainer.withValues(alpha: 0.35),
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.md),
          child: Row(
            children: [
              Icon(Icons.cancel_rounded, color: scheme.error),
              const SizedBox(width: AppSpacing.md),
              Expanded(
                child: Text(
                  'Esta solicitud fue cancelada por el cliente.',
                  style: Theme.of(context).textTheme.bodyLarge?.copyWith(fontWeight: FontWeight.w600),
                ),
              ),
            ],
          ),
        ),
      );
    }
    if (incidentEstadoIsTerminalSuccess(d.estado) || normalizeIncidentEstado(d.estado) == 'finalizado') {
      return Card(
        color: const Color(0xFFECFDF5),
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.md),
          child: Row(
            children: [
              const Icon(Icons.verified_outlined, color: _successGreen, size: 32),
              const SizedBox(width: AppSpacing.md),
              Expanded(
                child: Text(
                  'Servicio finalizado. Buen trabajo.',
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.w800,
                        color: const Color(0xFF166534),
                      ),
                ),
              ),
            ],
          ),
        ),
      );
    }
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(Icons.info_outline_rounded, color: scheme.primary, size: 28),
            const SizedBox(width: AppSpacing.md),
            Expanded(
              child: Text(
                'Gestioná el avance con los botones de abajo. En la app del cliente se muestra otra vista de seguimiento.',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: scheme.onSurfaceVariant,
                      height: 1.35,
                    ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPagoPendienteCard(BuildContext context, IncidentDetail d) {
    final scheme = Theme.of(context).colorScheme;
    return Card(
      color: const Color(0xFFFFF7ED),
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.task_alt_rounded, color: Color(0xFF9A3412), size: 30),
                const SizedBox(width: AppSpacing.sm),
                Expanded(
                  child: Text(
                    'Servicio Terminado',
                    style: Theme.of(context).textTheme.titleLarge?.copyWith(
                          fontWeight: FontWeight.w900,
                          color: const Color(0xFF9A3412),
                        ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.md),
            Text(
              'El mecánico ha finalizado el trabajo. Por favor, procede al pago para cerrar la solicitud.',
              style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                    color: scheme.onSurface,
                    height: 1.35,
                  ),
            ),
            const SizedBox(height: AppSpacing.md),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(AppSpacing.md),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: const Color(0xFFF97316).withValues(alpha: 0.35)),
              ),
              child: Text(
                'Monto a pagar: \$${_montoPagoMvp.toStringAsFixed(2)}',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w900,
                      color: const Color(0xFF9A3412),
                    ),
              ),
            ),
            const SizedBox(height: AppSpacing.lg),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                style: FilledButton.styleFrom(
                  backgroundColor: _accentOrange,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 18),
                  textStyle: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w800),
                ),
                onPressed: _pagoBusy ? null : () => unawaited(_showPagoBottomSheet()),
                icon: _pagoBusy
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(strokeWidth: 2.2, color: Colors.white),
                      )
                    : const Icon(Icons.credit_card_rounded),
                label: Text(_pagoBusy ? 'Procesando...' : 'Pagar Servicio'),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPagoCompletadoCard(BuildContext context) {
    return Card(
      color: const Color(0xFFECFDF5),
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.receipt_long_rounded, color: _successGreen, size: 30),
                const SizedBox(width: AppSpacing.sm),
                Expanded(
                  child: Text(
                    'Servicio Pagado Exitosamente',
                    style: Theme.of(context).textTheme.titleLarge?.copyWith(
                          fontWeight: FontWeight.w900,
                          color: const Color(0xFF166534),
                        ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.md),
            Text(
              'Tu solicitud quedó cerrada correctamente. Gracias por confiar en nosotros.',
              style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                    color: const Color(0xFF166534),
                    height: 1.35,
                  ),
            ),
            const SizedBox(height: AppSpacing.md),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(AppSpacing.md),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: const Color(0xFF22C55E).withValues(alpha: 0.35)),
              ),
              child: Text(
                'Recibo emitido por el sistema',
                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w800,
                      color: const Color(0xFF166534),
                    ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSummary(BuildContext context, IncidentDetail d) {
    final scheme = Theme.of(context).colorScheme;
    final badge = incidentEstadoBadgeColors(Theme.of(context), d.estado);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    'Estado',
                    style: Theme.of(context).textTheme.labelLarge?.copyWith(color: scheme.onSurfaceVariant),
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: badge.background,
                    borderRadius: BorderRadius.circular(999),
                    border: Border.all(color: badge.border),
                  ),
                  child: Text(
                    d.estado.isEmpty ? '—' : d.estado,
                    style: Theme.of(context).textTheme.labelMedium?.copyWith(
                          color: badge.foreground,
                          fontWeight: FontWeight.w800,
                        ),
                  ),
                ),
              ],
            ),
            const Divider(height: AppSpacing.lg),
            if (widget.isTechnician && widget.clienteNombre != null && widget.clienteNombre!.isNotEmpty) ...[
              _kv(context, Icons.person_outline, 'Cliente', widget.clienteNombre!),
              const SizedBox(height: AppSpacing.sm),
            ],
            _kv(context, Icons.calendar_today_outlined, 'Fecha', _fechaDisplay(d)),
            const SizedBox(height: AppSpacing.sm),
            _kv(context, Icons.directions_car_outlined, 'Vehículo', _vehiculoDisplay(d)),
            const SizedBox(height: AppSpacing.sm),
            _kv(
              context,
              Icons.place_outlined,
              'Ubicación',
              '${d.latitud.toStringAsFixed(5)}, ${d.longitud.toStringAsFixed(5)}',
              trailing: IconButton(
                tooltip: 'Copiar coordenadas',
                onPressed: () async {
                  await Clipboard.setData(ClipboardData(text: '${d.latitud},${d.longitud}'));
                  if (context.mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('Coordenadas copiadas')),
                    );
                  }
                },
                icon: const Icon(Icons.copy_rounded, size: 20),
              ),
            ),
            if (d.descripcionTexto != null && d.descripcionTexto!.trim().isNotEmpty) ...[
              const SizedBox(height: AppSpacing.sm),
              Text('Descripción', style: Theme.of(context).textTheme.labelLarge),
              const SizedBox(height: AppSpacing.xxs),
              Text(d.descripcionTexto!, style: Theme.of(context).textTheme.bodyMedium),
            ],
          ],
        ),
      ),
    );
  }

  Widget _kv(BuildContext context, IconData icon, String k, String v, {Widget? trailing}) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, size: 22, color: Theme.of(context).colorScheme.primary),
        const SizedBox(width: AppSpacing.sm),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(k, style: Theme.of(context).textTheme.labelMedium?.copyWith(fontWeight: FontWeight.w700)),
              const SizedBox(height: 2),
              Text(v, style: Theme.of(context).textTheme.bodyMedium),
            ],
          ),
        ),
        if (trailing != null) trailing,
      ],
    );
  }

  Widget _buildTimeline(BuildContext context, IncidentDetail d) {
    final scheme = Theme.of(context).colorScheme;
    final stepIdx = incidentTimelineStepIndex(d.estado);
    const labels = <String>[
      'Reportado',
      'Taller asignado',
      'En proceso',
      'Finalizado',
    ];

    if (incidentEstadoIsCancelado(d.estado)) {
      return Card(
        color: scheme.errorContainer.withValues(alpha: 0.35),
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.md),
          child: Row(
            children: [
              Icon(Icons.cancel_rounded, color: scheme.error),
              const SizedBox(width: AppSpacing.md),
              Expanded(
                child: Text(
                  'Esta solicitud fue cancelada.',
                  style: Theme.of(context).textTheme.bodyLarge?.copyWith(fontWeight: FontWeight.w600),
                ),
              ),
            ],
          ),
        ),
      );
    }

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Seguimiento',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: AppSpacing.md),
            for (var i = 0; i < labels.length; i++)
              _TimelineRow(
                title: labels[i],
                subtitle: i == 0
                    ? 'Pendiente de asignación'
                    : i == 1
                        ? 'Asignado a taller / técnico'
                        : i == 2
                            ? 'Auxilio en curso'
                            : 'Servicio concluido',
                isDone: stepIdx > i,
                isCurrent: stepIdx == i,
                showLineBelow: i < labels.length - 1,
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildTechnicianCard(BuildContext context, IncidentDetail d) {
    final scheme = Theme.of(context).colorScheme;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Row(
          children: [
            CircleAvatar(
              backgroundColor: scheme.primaryContainer,
              child: Icon(Icons.build_circle_outlined, color: scheme.onPrimaryContainer),
            ),
            const SizedBox(width: AppSpacing.md),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Mecánico asignado',
                    style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w800),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Usuario técnico ID: ${d.tecnicoId}',
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: scheme.onSurfaceVariant),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  bool _showClienteIaCard(IncidentDetail d) {
    if ((d.resumenIa ?? '').trim().isNotEmpty) {
      return true;
    }
    if ((d.aiStatus ?? '').trim().isNotEmpty) {
      return true;
    }
    final ar = d.aiResult;
    return ar != null && ar.isNotEmpty;
  }

  Widget _buildIaCard(BuildContext context, IncidentDetail d) {
    final scheme = Theme.of(context).colorScheme;
    final st = (d.aiStatus ?? '').toLowerCase();
    final manual = st == 'manual_review';
    final ar = d.aiResult;
    final transcripcion = (ar?['transcripcion'] as String?)?.trim();
    final danos = ar?['danos_identificados'];
    final resumenJson = (ar?['resumen_automatico'] as String?)?.trim();
    final confJson = ar?['confidence'];

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Análisis asistido',
              style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w800),
            ),
            if (manual) ...[
              const SizedBox(height: AppSpacing.sm),
              Text(
                'En revisión manual: el sistema marcó baja confianza. Un operador validará el caso.',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: const Color(0xFFC2410C),
                      fontWeight: FontWeight.w600,
                    ),
              ),
            ],
            if ((d.aiStatus ?? '').isNotEmpty) ...[
              const SizedBox(height: AppSpacing.xs),
              Text(
                'Estado IA: ${d.aiStatus}'
                '${d.aiProvider != null ? ' · ${d.aiProvider}' : ''}'
                '${d.aiModel != null ? ' / ${d.aiModel}' : ''}',
                style: Theme.of(context).textTheme.labelSmall?.copyWith(color: scheme.onSurfaceVariant),
              ),
            ],
            if (d.categoriaIa != null) ...[
              const SizedBox(height: AppSpacing.xs),
              Text('Categoría: ${d.categoriaIa}', style: Theme.of(context).textTheme.bodyMedium),
            ],
            if (d.prioridadIa != null) ...[
              const SizedBox(height: 4),
              Text('Prioridad: ${d.prioridadIa}', style: Theme.of(context).textTheme.bodySmall),
            ],
            if (transcripcion != null && transcripcion.isNotEmpty) ...[
              const SizedBox(height: AppSpacing.sm),
              Text('Transcripción', style: Theme.of(context).textTheme.labelLarge),
              Text(transcripcion, style: Theme.of(context).textTheme.bodyMedium),
            ],
            if (danos is List && danos.isNotEmpty) ...[
              const SizedBox(height: AppSpacing.sm),
              Text('Daños detectados', style: Theme.of(context).textTheme.labelLarge),
              ...danos.whereType<String>().map(
                    (x) => Padding(
                      padding: const EdgeInsets.only(left: 8, top: 2),
                      child: Text('· $x', style: Theme.of(context).textTheme.bodySmall),
                    ),
                  ),
            ],
            if ((d.resumenIa ?? '').trim().isNotEmpty) ...[
              const SizedBox(height: AppSpacing.xs),
              Text(d.resumenIa!, style: Theme.of(context).textTheme.bodyMedium),
            ] else if (resumenJson != null && resumenJson.isNotEmpty) ...[
              const SizedBox(height: AppSpacing.xs),
              Text(resumenJson, style: Theme.of(context).textTheme.bodyMedium),
            ],
            if (d.confianzaIa != null) ...[
              const SizedBox(height: AppSpacing.xs),
              Text(
                'Confianza: ${d.confianzaIa!.toStringAsFixed(2)}',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(color: scheme.onSurfaceVariant),
              ),
            ] else if (confJson is num) ...[
              const SizedBox(height: AppSpacing.xs),
              Text(
                'Confianza: ${confJson.toStringAsFixed(2)}',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(color: scheme.onSurfaceVariant),
              ),
            ],
          ],
        ),
      ),
    );
  }

  /// Listado básico 1.5.5: prioridad/distancia/ETA aprox. (servidor).
  Widget _buildCandidatosAsignacionCard(BuildContext context, List<Map<String, dynamic>> items) {
    final scheme = Theme.of(context).colorScheme;
    final take = items.length > 5 ? items.sublist(0, 5) : items;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Talleres sugeridos',
              style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 4),
            Text(
              'Orden por puntuación del motor (distancia, especialidad, prioridad, ETA aprox.). La asignación final la confirma el operador.',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(color: scheme.onSurfaceVariant),
            ),
            const SizedBox(height: AppSpacing.sm),
            for (final c in take) ...[
              const Divider(height: 1),
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 8),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    CircleAvatar(
                      backgroundColor: scheme.primaryContainer,
                      child: Text(
                        '${(c['rank'] as num?)?.toInt() ?? '—'}',
                        style: TextStyle(
                          color: scheme.onPrimaryContainer,
                          fontWeight: FontWeight.w800,
                          fontSize: 12,
                        ),
                      ),
                    ),
                    const SizedBox(width: AppSpacing.sm),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            (c['taller_nombre'] as String?)?.trim().isNotEmpty == true
                                ? c['taller_nombre'] as String
                                : 'Taller #${c['taller_id']}',
                            style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700),
                          ),
                          if (c['distancia_km'] != null)
                            Text(
                              'Distancia ≈ ${(c['distancia_km'] as num).toStringAsFixed(1)} km',
                              style: Theme.of(context).textTheme.bodySmall,
                            )
                          else
                            Text(
                              'Score: ${(c['score_total'] as num?)?.toStringAsFixed(3) ?? '—'}',
                              style: Theme.of(context).textTheme.bodySmall,
                            ),
                          if (c['eta_minutos_estimada'] != null)
                            Text(
                              'ETA aprox. ~ ${(c['eta_minutos_estimada'] as num).round()} min',
                              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                    color: scheme.onSurfaceVariant,
                                  ),
                            ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _TimelineRow extends StatelessWidget {
  const _TimelineRow({
    required this.title,
    required this.subtitle,
    required this.isDone,
    required this.isCurrent,
    required this.showLineBelow,
  });

  final String title;
  final String subtitle;
  final bool isDone;
  final bool isCurrent;
  final bool showLineBelow;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final dotColor = isDone
        ? const Color(0xFF22C55E)
        : isCurrent
            ? scheme.primary
            : scheme.outlineVariant;
    final titleStyle = Theme.of(context).textTheme.titleSmall?.copyWith(
          fontWeight: isCurrent ? FontWeight.w900 : FontWeight.w600,
          color: isDone || isCurrent ? scheme.onSurface : scheme.onSurfaceVariant,
        );

    return IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 28,
            child: Column(
              children: [
                Container(
                  width: 14,
                  height: 14,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: dotColor,
                    border: Border.all(
                      color: isCurrent ? scheme.primary.withValues(alpha: 0.4) : Colors.transparent,
                      width: 3,
                    ),
                  ),
                ),
                if (showLineBelow)
                  Expanded(
                    child: Container(
                      width: 2,
                      margin: const EdgeInsets.symmetric(vertical: 2),
                      color: isDone ? const Color(0xFF86EFAC) : scheme.outlineVariant,
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(width: AppSpacing.sm),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.only(bottom: AppSpacing.md),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: titleStyle),
                  const SizedBox(height: 2),
                  Text(
                    subtitle,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: scheme.onSurfaceVariant,
                          fontWeight: isCurrent ? FontWeight.w600 : FontWeight.w400,
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
