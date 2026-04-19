import 'package:flutter/material.dart';

import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../domain/vehicle.dart';

String vehicleCardTitle(Vehicle v) {
  final mm = '${v.marca} ${v.modelo}'.trim();
  if (mm.isEmpty) {
    return v.placa;
  }
  return mm;
}

String vehicleCardSubtitle(Vehicle v) {
  final parts = <String>[];
  if (v.color != null && v.color!.trim().isNotEmpty) {
    parts.add(v.color!.trim());
  }
  return parts.join(' · ');
}

/// Entry animation for list items (fade + slide).
class AnimatedVehicleListCard extends StatelessWidget {
  const AnimatedVehicleListCard({
    super.key,
    required this.index,
    required this.vehicleId,
    required this.child,
  });

  final int index;
  final int vehicleId;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    final capped = index.clamp(0, 10);
    return TweenAnimationBuilder<double>(
      key: ValueKey<int>(vehicleId),
      tween: Tween(begin: 0, end: 1),
      duration: Duration(milliseconds: 220 + capped * 26),
      curve: Curves.easeOutCubic,
      child: child,
      builder: (context, t, c) {
        return Opacity(
          opacity: t,
          child: Transform.translate(
            offset: Offset(0, (1 - t) * 10),
            child: c,
          ),
        );
      },
    );
  }
}

/// Vehicle row card (CU-05 list) — reusable list tile with actions.
class VehicleListCard extends StatelessWidget {
  const VehicleListCard({
    super.key,
    required this.vehicle,
    required this.onOpenDetail,
    required this.onEdit,
    required this.onDelete,
  });

  final Vehicle vehicle;
  final VoidCallback onOpenDetail;
  final VoidCallback onEdit;
  final VoidCallback onDelete;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final v = vehicle;

    return Card(
      child: InkWell(
        onTap: onOpenDetail,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(AppSpacing.sm, AppSpacing.md, AppSpacing.xs, AppSpacing.md),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              DecoratedBox(
                decoration: BoxDecoration(
                  color: scheme.primaryContainer.withValues(alpha: 0.55),
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: scheme.outlineVariant.withValues(alpha: 0.55)),
                ),
                child: Padding(
                  padding: const EdgeInsets.all(AppSpacing.sm),
                  child: Icon(Icons.directions_car_rounded, color: scheme.primary, size: 26),
                ),
              ),
              const SizedBox(width: AppSpacing.sm),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      vehicleCardTitle(v),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: AppTextStyles.subtitle(context).copyWith(
                        fontWeight: FontWeight.w800,
                        letterSpacing: -0.2,
                        height: 1.2,
                      ),
                    ),
                    const SizedBox(height: AppSpacing.xs),
                    Wrap(
                      spacing: AppSpacing.xs,
                      runSpacing: AppSpacing.xs,
                      crossAxisAlignment: WrapCrossAlignment.center,
                      children: [
                        PlacaBadge(placa: v.placa),
                        VehicleMetaChip(
                          icon: Icons.calendar_month_outlined,
                          label: '${v.anio}',
                        ),
                        if (v.tipoSeguro != null && v.tipoSeguro!.trim().isNotEmpty)
                          VehicleMetaChip(
                            icon: Icons.shield_outlined,
                            label: v.tipoSeguro!.trim(),
                          ),
                      ],
                    ),
                    if (vehicleCardSubtitle(v).trim().isNotEmpty) ...[
                      const SizedBox(height: AppSpacing.xs),
                      Text(
                        vehicleCardSubtitle(v),
                        maxLines: 3,
                        overflow: TextOverflow.ellipsis,
                        style: AppTextStyles.bodyMedium(context),
                      ),
                    ],
                  ],
                ),
              ),
              Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  IconButton(
                    tooltip: 'Editar',
                    style: IconButton.styleFrom(minimumSize: const Size(48, 48)),
                    onPressed: onEdit,
                    icon: const Icon(Icons.edit_outlined),
                  ),
                  IconButton(
                    tooltip: 'Eliminar',
                    style: IconButton.styleFrom(minimumSize: const Size(48, 48)),
                    onPressed: onDelete,
                    icon: Icon(Icons.delete_outline_rounded, color: scheme.error),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class PlacaBadge extends StatelessWidget {
  const PlacaBadge({super.key, required this.placa});

  final String placa;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.sm, vertical: AppSpacing.xxs),
      decoration: BoxDecoration(
        color: scheme.surfaceContainerHighest.withValues(alpha: 0.55),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: scheme.outlineVariant.withValues(alpha: 0.75)),
      ),
      child: Text(
        placa,
        style: AppTextStyles.caption(context).copyWith(
          fontWeight: FontWeight.w800,
          letterSpacing: 0.6,
        ),
      ),
    );
  }
}

class VehicleMetaChip extends StatelessWidget {
  const VehicleMetaChip({super.key, required this.icon, required this.label});

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.sm, vertical: AppSpacing.xxs),
      decoration: BoxDecoration(
        color: scheme.primary.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: scheme.outlineVariant.withValues(alpha: 0.55)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 16, color: scheme.primary),
          const SizedBox(width: 6),
          ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 160),
            child: Text(
              label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: AppTextStyles.caption(context).copyWith(
                color: scheme.onSurfaceVariant,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
