import 'package:flutter/material.dart';

import '../theme/app_radius.dart';
import '../theme/app_spacing.dart';

/// Floating pill navigation: Inicio, Vehículos, FAB (add vehicle), Actividad, Perfil.
class FloatingPillNavBar extends StatelessWidget {
  const FloatingPillNavBar({
    super.key,
    required this.selectedSlot,
    required this.onSlotTap,
    required this.onCenterTap,
  });

  /// `0` Inicio, `1` Vehículos, `3` Actividad, `4` Perfil (FAB is visual center, not a slot).
  final int selectedSlot;
  final ValueChanged<int> onSlotTap;
  final VoidCallback onCenterTap;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final surface = scheme.surface;
    final shadow = scheme.shadow.withValues(alpha: 0.12);

    return Material(
      elevation: 14,
      shadowColor: shadow,
      color: surface,
      surfaceTintColor: scheme.surfaceTint.withValues(alpha: 0.06),
      borderRadius: BorderRadius.circular(AppRadius.lg + 8),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(AppSpacing.xs, AppSpacing.sm, AppSpacing.xs, AppSpacing.sm),
        child: Row(
          children: [
            Expanded(
              child: _NavSlot(
                icon: selectedSlot == 0 ? Icons.home_rounded : Icons.home_outlined,
                label: 'Inicio',
                selected: selectedSlot == 0,
                onTap: () => onSlotTap(0),
              ),
            ),
            Expanded(
              child: _NavSlot(
                icon: selectedSlot == 1 ? Icons.directions_car_rounded : Icons.directions_car_outlined,
                label: 'Vehículos',
                selected: selectedSlot == 1,
                onTap: () => onSlotTap(1),
              ),
            ),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: AppSpacing.xxs),
              child: _CenterFab(onTap: onCenterTap),
            ),
            Expanded(
              child: _NavSlot(
                icon: selectedSlot == 3 ? Icons.history_rounded : Icons.history_outlined,
                label: 'Actividad',
                selected: selectedSlot == 3,
                onTap: () => onSlotTap(3),
              ),
            ),
            Expanded(
              child: _NavSlot(
                icon: selectedSlot == 4 ? Icons.person_rounded : Icons.person_outline_rounded,
                label: 'Perfil',
                selected: selectedSlot == 4,
                onTap: () => onSlotTap(4),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _NavSlot extends StatelessWidget {
  const _NavSlot({
    required this.icon,
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final primary = scheme.primary;
    final muted = scheme.onSurfaceVariant;

    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(AppRadius.md),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 220),
        curve: Curves.easeOutCubic,
        padding: const EdgeInsets.symmetric(vertical: AppSpacing.xs, horizontal: AppSpacing.xxs),
        decoration: BoxDecoration(
          color: selected ? primary.withValues(alpha: 0.12) : Colors.transparent,
          borderRadius: BorderRadius.circular(AppRadius.md),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              size: 26,
              color: selected ? primary : muted.withValues(alpha: 0.88),
            ),
            const SizedBox(height: 2),
            Text(
              label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 10.5,
                height: 1.1,
                fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
                letterSpacing: 0.1,
                color: selected ? primary : muted,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _CenterFab extends StatelessWidget {
  const _CenterFab({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final c = scheme.primary;

    return Tooltip(
      message: 'Agregar vehículo',
      child: Material(
        elevation: 8,
        shadowColor: c.withValues(alpha: 0.35),
        shape: const CircleBorder(),
        color: c,
        child: InkWell(
          customBorder: const CircleBorder(),
          onTap: onTap,
          child: SizedBox(
            width: 54,
            height: 54,
            child: Icon(Icons.add_rounded, color: scheme.onPrimary, size: 30),
          ),
        ),
      ),
    );
  }
}
