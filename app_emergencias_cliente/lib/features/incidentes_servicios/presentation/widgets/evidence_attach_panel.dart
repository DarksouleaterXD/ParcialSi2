import 'package:flutter/material.dart';

import '../../../../core/theme/app_spacing.dart';
import '../../../../core/widgets/app_section_header.dart';

/// Panel paso 3: descripción, foto, audio, nota de texto adicional.
class EvidenceAttachPanel extends StatelessWidget {
  const EvidenceAttachPanel({
    super.key,
    required this.descriptionController,
    required this.extraTextController,
    required this.hasPhoto,
    required this.hasAudio,
    required this.isRecording,
    required this.recordingSeconds,
    required this.onPickPhoto,
    required this.onClearPhoto,
    required this.onToggleRecord,
    required this.onClearAudio,
  });

  final TextEditingController descriptionController;
  final TextEditingController extraTextController;
  final bool hasPhoto;
  final bool hasAudio;
  final bool isRecording;
  final int recordingSeconds;
  final VoidCallback onPickPhoto;
  final VoidCallback onClearPhoto;
  final VoidCallback onToggleRecord;
  final VoidCallback onClearAudio;

  String get _recordLabel {
    if (isRecording) {
      final s = recordingSeconds;
      final m = (s ~/ 60).toString().padLeft(2, '0');
      final r = (s % 60).toString().padLeft(2, '0');
      return 'Detener ($m:$r)';
    }
    return hasAudio ? 'Volver a grabar' : 'Grabar audio';
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const AppSectionHeader(title: 'Descripción del incidente'),
        const SizedBox(height: AppSpacing.sm),
        TextField(
          controller: descriptionController,
          maxLines: 4,
          maxLength: 1000,
          decoration: const InputDecoration(
            hintText: '¿Qué pasó? (opcional, hasta 1000 caracteres)',
            alignLabelWithHint: true,
          ),
        ),
        const SizedBox(height: AppSpacing.lg),
        const AppSectionHeader(title: 'Nota de texto adicional'),
        const SizedBox(height: AppSpacing.xs),
        Text(
          'Opcional: se guarda como evidencia tipo texto, aparte de la descripción.',
          style: Theme.of(context).textTheme.bodySmall?.copyWith(color: scheme.onSurfaceVariant),
        ),
        const SizedBox(height: AppSpacing.sm),
        TextField(
          controller: extraTextController,
          maxLines: 3,
          maxLength: 10000,
          decoration: const InputDecoration(
            hintText: 'Detalle extra para el taller (opcional)',
          ),
        ),
        const SizedBox(height: AppSpacing.lg),
        const AppSectionHeader(title: 'Archivos'),
        const SizedBox(height: AppSpacing.sm),
        Wrap(
          spacing: AppSpacing.sm,
          runSpacing: AppSpacing.sm,
          children: [
            OutlinedButton.icon(
              onPressed: onPickPhoto,
              icon: const Icon(Icons.add_a_photo_outlined),
              label: const Text('Agregar foto'),
            ),
            OutlinedButton.icon(
              onPressed: onToggleRecord,
              icon: Icon(isRecording ? Icons.stop_circle_outlined : Icons.mic_none_rounded),
              label: Text(_recordLabel),
            ),
          ],
        ),
        if (hasPhoto || hasAudio) ...[
          const SizedBox(height: AppSpacing.md),
          Wrap(
            spacing: AppSpacing.xs,
            runSpacing: AppSpacing.xs,
            children: [
              if (hasPhoto)
                InputChip(
                  label: const Text('Foto lista'),
                  avatar: Icon(Icons.image_outlined, size: 18, color: scheme.primary),
                  deleteIcon: const Icon(Icons.close_rounded, size: 18),
                  onDeleted: onClearPhoto,
                ),
              if (hasAudio)
                InputChip(
                  label: const Text('Audio listo'),
                  avatar: Icon(Icons.audiotrack_rounded, size: 18, color: scheme.primary),
                  deleteIcon: const Icon(Icons.close_rounded, size: 18),
                  onDeleted: onClearAudio,
                ),
            ],
          ),
        ],
      ],
    );
  }
}
