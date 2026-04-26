import 'package:flutter/material.dart';

import '../theme/app_radius.dart';
import '../theme/app_spacing.dart';

/// Action sheet del FAB: reporte (CU-09) y vehículo (CU-05).
abstract final class QuickActionsSheet {
  static const double _minTileHeight = 52;

  static Future<void> show({
    required BuildContext context,
    required VoidCallback onAddVehicle,
    required VoidCallback onReportEmergency,
  }) {
    return showModalBottomSheet<void>(
      context: context,
      useSafeArea: true,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) {
        final scheme = Theme.of(ctx).colorScheme;
        return Padding(
          padding: EdgeInsets.only(bottom: MediaQuery.paddingOf(ctx).bottom),
          child: DecoratedBox(
            decoration: BoxDecoration(
              color: scheme.surfaceContainerHigh,
              borderRadius: const BorderRadius.vertical(
                top: Radius.circular(AppRadius.lg + 12),
              ),
              boxShadow: [
                BoxShadow(
                  color: scheme.shadow.withValues(alpha: 0.12),
                  blurRadius: 16,
                  offset: const Offset(0, -4),
                ),
              ],
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Center(
                  child: Container(
                    width: 40,
                    height: 4,
                    margin: const EdgeInsets.only(top: AppSpacing.sm, bottom: AppSpacing.md),
                    decoration: BoxDecoration(
                      color: scheme.onSurfaceVariant.withValues(alpha: 0.25),
                      borderRadius: BorderRadius.circular(AppRadius.pill),
                    ),
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.fromLTRB(AppSpacing.lg, 0, AppSpacing.lg, AppSpacing.sm),
                  child: Text(
                    '¿Qué querés hacer?',
                    style: Theme.of(ctx).textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.w800,
                          letterSpacing: -0.2,
                        ),
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
                  child: _QuickActionTile(
                    minHeight: _minTileHeight,
                    icon: Icons.warning_amber_rounded,
                    title: 'Reportar emergencia',
                    subtitle: 'Enviá ubicación y evidencias del incidente',
                    emphasize: true,
                    onTap: () => _closeAndRun(ctx, onReportEmergency),
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.fromLTRB(AppSpacing.md, AppSpacing.xs, AppSpacing.md, AppSpacing.sm),
                  child: _QuickActionTile(
                    minHeight: _minTileHeight,
                    icon: Icons.directions_car_outlined,
                    title: 'Agregar vehículo',
                    subtitle: 'Registrá un nuevo vehículo para tus solicitudes',
                    emphasize: false,
                    onTap: () => _closeAndRun(ctx, onAddVehicle),
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.fromLTRB(AppSpacing.lg, AppSpacing.sm, AppSpacing.lg, AppSpacing.lg),
                  child: SizedBox(
                    width: double.infinity,
                    height: _minTileHeight,
                    child: OutlinedButton(
                      onPressed: () => Navigator.of(ctx).pop(),
                      child: const Text('Cancelar'),
                    ),
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  static void _closeAndRun(BuildContext sheetContext, VoidCallback action) {
    Navigator.of(sheetContext).pop();
    Future<void>.microtask(action);
  }
}

class _QuickActionTile extends StatelessWidget {
  const _QuickActionTile({
    required this.minHeight,
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.emphasize,
    required this.onTap,
  });

  final double minHeight;
  final IconData icon;
  final String title;
  final String subtitle;
  final bool emphasize;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final border = emphasize
        ? Border.all(color: scheme.primary.withValues(alpha: 0.45), width: 1.5)
        : Border.all(color: scheme.outlineVariant.withValues(alpha: 0.5));
    final bg = emphasize ? scheme.primaryContainer.withValues(alpha: 0.35) : scheme.surface;

    return Material(
      color: bg,
      borderRadius: BorderRadius.circular(AppRadius.md),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(AppRadius.md),
        child: Container(
          constraints: BoxConstraints(minHeight: minHeight),
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md, vertical: AppSpacing.sm),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(AppRadius.md),
            border: border,
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Icon(icon, size: 28, color: emphasize ? scheme.primary : scheme.onSurfaceVariant),
              const SizedBox(width: AppSpacing.md),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      title,
                      style: Theme.of(context).textTheme.titleSmall?.copyWith(
                            fontWeight: FontWeight.w700,
                            color: emphasize ? scheme.primary : scheme.onSurface,
                          ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      subtitle,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: scheme.onSurfaceVariant,
                            height: 1.25,
                          ),
                    ),
                  ],
                ),
              ),
              Icon(Icons.chevron_right_rounded, color: scheme.onSurfaceVariant.withValues(alpha: 0.7)),
            ],
          ),
        ),
      ),
    );
  }
}
