import 'package:flutter/material.dart';

import '../../../../core/theme/app_spacing.dart';

/// Muestra lat/lng obtenidos (paso 2).
class LocationSummaryTile extends StatelessWidget {
  const LocationSummaryTile({
    super.key,
    required this.latitud,
    required this.longitud,
    this.accuracyMeters,
  });

  final double latitud;
  final double longitud;
  final double? accuracyMeters;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Row(
          children: [
            Icon(Icons.location_on_rounded, color: scheme.primary, size: 28),
            const SizedBox(width: AppSpacing.md),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Ubicación actual',
                    style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: AppSpacing.xxs),
                  Text(
                    '${latitud.toStringAsFixed(6)}, ${longitud.toStringAsFixed(6)}',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                  if (accuracyMeters != null)
                    Text(
                      'Precisión aprox.: ${accuracyMeters!.toStringAsFixed(0)} m',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(color: scheme.onSurfaceVariant),
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
