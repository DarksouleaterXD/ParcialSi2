import 'package:flutter/material.dart';

import '../../../core/authorized_client.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../../core/widgets/app_empty_state.dart';
import '../../../core/widgets/app_snackbar.dart';
import '../../../core/widgets/destructive_button.dart';
import '../../../core/widgets/primary_button.dart';
import '../data/vehicles_api.dart';
import '../domain/vehicle.dart';
import 'vehicle_form_screen.dart';
import 'widgets/vehicle_list_card.dart';

class VehiclesListTab extends StatefulWidget {
  const VehiclesListTab({
    super.key,
    required this.api,
    required this.onSessionExpired,
    required this.onAddVehicle,
  });

  final VehiclesApi api;
  final VoidCallback onSessionExpired;
  final VoidCallback onAddVehicle;

  @override
  State<VehiclesListTab> createState() => VehiclesListTabState();
}

class VehiclesListTabState extends State<VehiclesListTab> {
  final _pageSize = 20;
  var _page = 1;
  var _loading = true;
  var _loadingMore = false;
  String? _error;
  final _items = <Vehicle>[];
  var _total = 0;

  @override
  void initState() {
    super.initState();
    reload();
  }

  void reload() {
    setState(() {
      _page = 1;
      _items.clear();
    });
    _load(reset: true);
  }

  Future<void> _load({required bool reset}) async {
    if (reset) {
      setState(() {
        _loading = true;
        _error = null;
      });
    } else {
      setState(() => _loadingMore = true);
    }
    try {
      final res = await widget.api.list(page: _page, pageSize: _pageSize);
      if (!mounted) {
        return;
      }
      setState(() {
        if (reset) {
          _items
            ..clear()
            ..addAll(res.items);
        } else {
          _items.addAll(res.items);
        }
        _total = res.total;
        _loading = false;
        _loadingMore = false;
        _error = null;
      });
    } on SessionExpiredException {
      if (mounted) {
        widget.onSessionExpired();
      }
    } on ApiClientException catch (e) {
      if (mounted) {
        setState(() {
          _loading = false;
          _loadingMore = false;
          _error = e.message;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          _loading = false;
          _loadingMore = false;
          _error = 'No se pudo conectar con el servidor';
        });
      }
    }
  }

  Future<void> _loadMore() async {
    if (_loadingMore || _items.length >= _total) {
      return;
    }
    setState(() => _page++);
    await _load(reset: false);
  }

  Future<void> _openEdit(Vehicle v) async {
    final ok = await Navigator.of(context).push<bool>(
      MaterialPageRoute<bool>(
        builder: (_) => VehicleFormScreen(
          api: widget.api,
          vehicle: v,
          onSessionExpired: widget.onSessionExpired,
        ),
      ),
    );
    if (ok == true && mounted) {
      reload();
    }
  }

  Future<void> _confirmDelete(Vehicle v) async {
    final go = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Eliminar vehículo'),
        content: Text(
          '¿Eliminar el vehículo ${v.placa}? Esta acción no se puede deshacer.',
        ),
        actionsPadding: const EdgeInsets.fromLTRB(AppSpacing.md, 0, AppSpacing.md, AppSpacing.md),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancelar'),
          ),
          DestructiveFilledButton(
            label: 'Eliminar',
            onPressed: () => Navigator.pop(ctx, true),
          ),
        ],
      ),
    );
    if (go != true || !mounted) {
      return;
    }
    try {
      await widget.api.delete(v.id);
      if (mounted) {
        AppSnackBar.success(context, 'Vehículo eliminado.');
        reload();
      }
    } on SessionExpiredException {
      widget.onSessionExpired();
    } on ApiClientException catch (e) {
      if (mounted) {
        AppSnackBar.error(context, e.message);
      }
    } catch (_) {
      if (mounted) {
        AppSnackBar.error(context, 'No se pudo conectar con el servidor');
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;

    if (_loading) {
      return const Center(child: AppLoadingState(message: 'Cargando vehículos…'));
    }
    if (_error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
          child: AppEmptyState(
            icon: Icons.cloud_off_outlined,
            iconColor: scheme.onSurfaceVariant,
            title: 'No pudimos cargar tus vehículos',
            subtitle: _error!,
            action: SecondaryButton(
              label: 'Reintentar',
              icon: Icons.refresh_rounded,
              onPressed: reload,
            ),
          ),
        ),
      );
    }
    if (_items.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
          child: TweenAnimationBuilder<double>(
            tween: Tween(begin: 0, end: 1),
            duration: const Duration(milliseconds: 400),
            curve: Curves.easeOutCubic,
            builder: (context, t, child) {
              return Opacity(
                opacity: t,
                child: Transform.translate(
                  offset: Offset(0, (1 - t) * 14),
                  child: child,
                ),
              );
            },
            child: AppEmptyState(
              icon: Icons.directions_car_outlined,
              title: 'No tenés vehículos registrados',
              subtitle: 'Agregá tu primer vehículo para reportar emergencias más rápido.',
              action: PrimaryButton(
                label: 'Agregar vehículo',
                icon: Icons.add_rounded,
                onPressed: widget.onAddVehicle,
              ),
            ),
          ),
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: () async => reload(),
      color: scheme.primary,
      child: ListView.builder(
        padding: const EdgeInsets.fromLTRB(AppSpacing.md, AppSpacing.xs, AppSpacing.md, 100),
        itemCount: _items.length + (_items.length < _total ? 1 : 0),
        itemBuilder: (context, i) {
          if (i >= _items.length) {
            return Padding(
              padding: const EdgeInsets.symmetric(vertical: AppSpacing.md),
              child: Center(
                child: _loadingMore
                    ? Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          SizedBox(
                            width: 22,
                            height: 22,
                            child: CircularProgressIndicator(
                              strokeWidth: 2.5,
                              color: scheme.primary,
                            ),
                          ),
                          const SizedBox(width: AppSpacing.sm),
                          Text(
                            'Cargando más…',
                            style: AppTextStyles.caption(context).copyWith(
                              color: scheme.onSurfaceVariant,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ],
                      )
                    : SecondaryButton(
                        label: 'Cargar más',
                        icon: Icons.expand_more_rounded,
                        onPressed: _loadMore,
                      ),
              ),
            );
          }
          final v = _items[i];
          return Padding(
            padding: const EdgeInsets.only(bottom: AppSpacing.sm),
            child: AnimatedVehicleListCard(
              index: i,
              vehicleId: v.id,
              child: VehicleListCard(
                vehicle: v,
                onOpenDetail: () => _openEdit(v),
                onEdit: () => _openEdit(v),
                onDelete: () => _confirmDelete(v),
              ),
            ),
          );
        },
      ),
    );
  }
}
