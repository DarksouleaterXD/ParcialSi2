import 'package:flutter/material.dart';

import '../../../../core/theme/app_spacing.dart';

/// Indicador de pasos 1–4 del wizard CU-09.
class ReportStepIndicator extends StatelessWidget {
  const ReportStepIndicator({
    super.key,
    required this.currentStep,
    this.labels = const ['Vehículo', 'Ubicación', 'Evidencias', 'Confirmar'],
  });

  /// 0-based index (0..3).
  final int currentStep;
  final List<String> labels;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Row(
      children: List.generate(labels.length, (i) {
        final active = i <= currentStep;
        final isCurrent = i == currentStep;
        return Expanded(
          child: Column(
            children: [
              Container(
                height: 4,
                decoration: BoxDecoration(
                  color: active ? scheme.primary : scheme.outlineVariant.withValues(alpha: 0.6),
                  borderRadius: BorderRadius.circular(999),
                ),
              ),
              const SizedBox(height: AppSpacing.xs),
              Text(
                labels[i],
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.labelSmall?.copyWith(
                      fontWeight: isCurrent ? FontWeight.w800 : FontWeight.w500,
                      color: isCurrent ? scheme.primary : scheme.onSurfaceVariant,
                    ),
              ),
            ],
          ),
        );
      }),
    );
  }
}
