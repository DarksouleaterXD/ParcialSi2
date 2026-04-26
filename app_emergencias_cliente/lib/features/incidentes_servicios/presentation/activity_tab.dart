import 'dart:async';

import 'package:flutter/material.dart';

import '../../../core/auth_api.dart';
import '../../../core/auth_storage.dart';
import '../../../core/authorized_client.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/widgets/app_empty_state.dart';
import '../../../core/widgets/primary_button.dart';
import '../../usuario_autenticacion/data/profile_api.dart';
import '../data/incidents_api.dart';
import '../domain/incident.dart';
import 'incident_detail_screen.dart';
import 'widgets/incident_status_style.dart';

/// Listado paginado del cliente o, para técnico, fusión de páginas filtradas por asignación propia.
class ActivityListController extends ChangeNotifier {
  ActivityListController({
    required IncidentsApi api,
    required this.onSessionExpired,
    this.assignedTechnicianUserId,
    this.listOnlyAssignedToTechnician = false,
  }) : _api = api;

  final IncidentsApi _api;
  final VoidCallback onSessionExpired;
  final int? assignedTechnicianUserId;
  final bool listOnlyAssignedToTechnician;

  static const int _pageSize = 50;

  var _loading = true;
  var _loadingMore = false;
  String? _error;
  final List<IncidentListItem> _items = <IncidentListItem>[];
  var _page = 1;
  var _total = 0;

  bool get loading => _loading;
  bool get loadingMore => _loadingMore;
  String? get error => _error;
  List<IncidentListItem> get items => List.unmodifiable(_items);
  int get total => _total;
  bool get hasMore => !listOnlyAssignedToTechnician && _items.length < _total;

  Future<void> refresh() async {
    _page = 1;
    _error = null;
    _loading = true;
    notifyListeners();
    if (listOnlyAssignedToTechnician) {
      await _fetchAssignedToTechnicianMerged();
    } else {
      await _fetch(reset: true);
    }
  }

  Future<void> loadMore() async {
    if (listOnlyAssignedToTechnician || _loadingMore || !hasMore || _loading) {
      return;
    }
    _page += 1;
    _loadingMore = true;
    notifyListeners();
    await _fetch(reset: false);
  }

  Future<void> _fetchAssignedToTechnicianMerged() async {
    final tid = assignedTechnicianUserId;
    if (tid == null) {
      _error = 'No se pudo determinar el usuario técnico.';
      _loading = false;
      notifyListeners();
      return;
    }
    try {
      const ps = _pageSize;
      var page = 1;
      final acc = <IncidentListItem>[];
      while (true) {
        final res = await _api.getIncidents(page: page, pageSize: ps);
        acc.addAll(res.items.where((e) => e.tecnicoId == tid));
        if (res.items.isEmpty || res.items.length < ps) {
          break;
        }
        if (page * ps >= res.total) {
          break;
        }
        page++;
      }
      _items
        ..clear()
        ..addAll(acc);
      _total = acc.length;
      _error = null;
      _loading = false;
      _loadingMore = false;
      notifyListeners();
    } on SessionExpiredException {
      _loading = false;
      _loadingMore = false;
      onSessionExpired();
    } on ApiClientException catch (e) {
      _error = e.message;
      _loading = false;
      _loadingMore = false;
      notifyListeners();
    } catch (_) {
      _error = 'No se pudo conectar con el servidor';
      _loading = false;
      _loadingMore = false;
      notifyListeners();
    }
  }

  Future<void> _fetch({required bool reset}) async {
    try {
      final res = await _api.getIncidents(page: _page, pageSize: _pageSize);
      if (reset) {
        _items
          ..clear()
          ..addAll(res.items);
      } else {
        _items.addAll(res.items);
      }
      _total = res.total;
      _error = null;
      _loading = false;
      _loadingMore = false;
      notifyListeners();
    } on SessionExpiredException {
      _loading = false;
      _loadingMore = false;
      onSessionExpired();
    } on ApiClientException catch (e) {
      _error = e.message;
      _loading = false;
      _loadingMore = false;
      notifyListeners();
    } catch (_) {
      _error = 'No se pudo conectar con el servidor';
      _loading = false;
      _loadingMore = false;
      notifyListeners();
    }
  }
}

/// Pestaña de actividad: cliente (sus reportes) o técnico (viajes asignados a su usuario).
class ActivityTab extends StatefulWidget {
  const ActivityTab({
    super.key,
    required this.storage,
    required this.authApi,
    required this.onSessionExpired,
    required this.onGoToInicioTab,
    this.isTechnician = false,
  });

  final AuthStorage storage;
  final AuthApi authApi;
  final VoidCallback onSessionExpired;
  final VoidCallback onGoToInicioTab;
  final bool isTechnician;

  @override
  State<ActivityTab> createState() => _ActivityTabState();
}

class _ActivityTabState extends State<ActivityTab> {
  ActivityListController? _controller;
  var _bootstrapping = true;
  String? _bootstrapError;

  @override
  void initState() {
    super.initState();
    unawaited(_bootstrap());
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  Future<void> _bootstrap() async {
    final client = AuthorizedClient(storage: widget.storage);
    final api = IncidentsApi(client);
    int? technicianId;
    if (widget.isTechnician) {
      try {
        final me = await ProfileApi(client).fetchProfile();
        technicianId = me.id;
      } on SessionExpiredException {
        if (mounted) {
          widget.onSessionExpired();
        }
        return;
      } catch (_) {
        if (mounted) {
          setState(() {
            _bootstrapping = false;
            _bootstrapError = 'No se pudo cargar tu perfil para filtrar los viajes asignados.';
          });
        }
        return;
      }
    }
    if (!mounted) {
      return;
    }
    _controller = ActivityListController(
      api: api,
      onSessionExpired: widget.onSessionExpired,
      assignedTechnicianUserId: technicianId,
      listOnlyAssignedToTechnician: widget.isTechnician,
    );
    await _controller!.refresh();
    if (mounted) {
      setState(() => _bootstrapping = false);
    }
  }

  void _openDetail(IncidentListItem row) {
    Navigator.of(context)
        .push<void>(
      MaterialPageRoute<void>(
        builder: (_) => IncidentDetailScreen(
          storage: widget.storage,
          authApi: widget.authApi,
          incidenteId: row.id,
          vehiculoLabel: _vehiculoLine(row),
          onSessionExpired: widget.onSessionExpired,
          isTechnician: widget.isTechnician,
          clienteNombre: widget.isTechnician
              ? (row.clienteNombre.isNotEmpty ? row.clienteNombre : null)
              : null,
        ),
      ),
    )
        .then((_) {
      if (mounted && _controller != null) {
        unawaited(_controller!.refresh());
      }
    });
  }

  String _vehiculoLine(IncidentListItem row) {
    final parts = <String>[row.vehiculoPlaca, row.vehiculoMarcaModelo].where((s) => s.isNotEmpty).join(' · ');
    if (parts.isEmpty) {
      return 'Vehículo #${row.id}';
    }
    return parts;
  }

  String _cardTitle(IncidentListItem row) {
    final d = row.createdAt?.toLocal();
    if (d == null) {
      return widget.isTechnician ? 'Viaje #${row.id}' : 'Emergencia #${row.id}';
    }
    final fecha =
        '${d.day.toString().padLeft(2, '0')}/${d.month.toString().padLeft(2, '0')}/${d.year} '
        '${d.hour.toString().padLeft(2, '0')}:${d.minute.toString().padLeft(2, '0')}';
    return widget.isTechnician ? 'Viaje - $fecha' : 'Emergencia - $fecha';
  }

  Widget _estadoBadge(BuildContext context, String estado) {
    final theme = Theme.of(context);
    final label = estado.isEmpty ? 'Sin estado' : estado;
    final c = incidentEstadoBadgeColors(theme, estado);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: c.background,
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: c.border, width: 1),
      ),
      child: Text(
        label,
        style: theme.textTheme.labelMedium?.copyWith(
          color: c.foreground,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;

    if (_bootstrapping || _controller == null) {
      return Center(child: CircularProgressIndicator(color: scheme.primary));
    }
    if (_bootstrapError != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
          child: AppEmptyState(
            icon: Icons.error_outline_rounded,
            iconColor: scheme.onSurfaceVariant,
            title: 'No pudimos preparar el listado',
            subtitle: _bootstrapError!,
            action: SecondaryButton(
              label: 'Reintentar',
              icon: Icons.refresh_rounded,
              onPressed: () {
                _controller?.dispose();
                _controller = null;
                setState(() {
                  _bootstrapping = true;
                  _bootstrapError = null;
                });
                unawaited(_bootstrap());
              },
            ),
          ),
        ),
      );
    }

    final c = _controller!;

    return ListenableBuilder(
      listenable: c,
      builder: (context, _) {
        if (c.loading) {
          return Center(child: CircularProgressIndicator(color: scheme.primary));
        }
        if (c.error != null) {
          return Center(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
              child: AppEmptyState(
                icon: Icons.cloud_off_outlined,
                iconColor: scheme.onSurfaceVariant,
                title: widget.isTechnician ? 'No pudimos cargar los trabajos' : 'No pudimos cargar tu actividad',
                subtitle: c.error!,
                action: SecondaryButton(
                  label: 'Reintentar',
                  icon: Icons.refresh_rounded,
                  onPressed: () => unawaited(c.refresh()),
                ),
              ),
            ),
          );
        }
        if (c.items.isEmpty) {
          return Center(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
              child: AppEmptyState(
                icon: widget.isTechnician ? Icons.assignment_outlined : Icons.inbox_outlined,
                title: widget.isTechnician ? 'No tenés viajes asignados' : 'No tenés solicitudes registradas',
                subtitle: widget.isTechnician
                    ? 'Cuando aceptes un auxilio desde la bolsa de solicitudes, vas a verlo acá con su estado.'
                    : 'Cuando reportes una emergencia desde Inicio, vas a ver el seguimiento acá.',
                action: PrimaryButton(
                  label: 'Ir a Inicio',
                  icon: Icons.home_outlined,
                  onPressed: widget.onGoToInicioTab,
                ),
              ),
            ),
          );
        }

        return RefreshIndicator(
          color: scheme.primary,
          onRefresh: () => c.refresh(),
          child: ListView.builder(
            padding: const EdgeInsets.fromLTRB(AppSpacing.md, AppSpacing.sm, AppSpacing.md, 100),
            itemCount: c.items.length + (c.hasMore ? 1 : 0),
            itemBuilder: (context, i) {
              if (i >= c.items.length) {
                return Padding(
                  padding: const EdgeInsets.symmetric(vertical: AppSpacing.md),
                  child: Center(
                    child: c.loadingMore
                        ? SizedBox(
                            width: 24,
                            height: 24,
                            child: CircularProgressIndicator(strokeWidth: 2.5, color: scheme.primary),
                          )
                        : SecondaryButton(
                            label: 'Cargar más',
                            icon: Icons.expand_more_rounded,
                            onPressed: () => unawaited(c.loadMore()),
                          ),
                  ),
                );
              }
              final row = c.items[i];
              return Padding(
                padding: const EdgeInsets.only(bottom: AppSpacing.sm),
                child: Card(
                  clipBehavior: Clip.antiAlias,
                  child: InkWell(
                    onTap: () => _openDetail(row),
                    child: Padding(
                      padding: const EdgeInsets.all(AppSpacing.md),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Icon(
                            widget.isTechnician ? Icons.handyman_outlined : Icons.local_shipping_outlined,
                            color: scheme.primary,
                            size: 28,
                          ),
                          const SizedBox(width: AppSpacing.md),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  _cardTitle(row),
                                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                                        fontWeight: FontWeight.w800,
                                      ),
                                ),
                                if (widget.isTechnician && row.clienteNombre.isNotEmpty) ...[
                                  const SizedBox(height: 4),
                                  Text(
                                    'Cliente: ${row.clienteNombre}',
                                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                          color: scheme.onSurfaceVariant,
                                          fontWeight: FontWeight.w600,
                                        ),
                                  ),
                                ],
                                const SizedBox(height: AppSpacing.xs),
                                Text(
                                  _vehiculoLine(row),
                                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                        color: scheme.onSurfaceVariant,
                                        fontWeight: FontWeight.w600,
                                      ),
                                ),
                                const SizedBox(height: AppSpacing.sm),
                                Wrap(
                                  spacing: 8,
                                  runSpacing: 8,
                                  crossAxisAlignment: WrapCrossAlignment.center,
                                  children: [
                                    _estadoBadge(context, row.estado),
                                    if (row.evidenciasCount > 0)
                                      Text(
                                        '${row.evidenciasCount} evidencia(s)',
                                        style: Theme.of(context).textTheme.labelSmall?.copyWith(
                                              color: scheme.onSurfaceVariant,
                                            ),
                                      ),
                                  ],
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
              );
            },
          ),
        );
      },
    );
  }
}
