import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';

import '../../../../core/theme/app_spacing.dart';
import '../../../../core/widgets/app_section_header.dart';

/// Panel paso 3: descripción, varias fotos, audio, nota de texto adicional.
class EvidenceAttachPanel extends StatefulWidget {
  const EvidenceAttachPanel({
    super.key,
    required this.descriptionController,
    required this.extraTextController,
    required this.photoCount,
    required this.maxPhotos,
    required this.hasAudio,
    required this.isRecordStarting,
    required this.isRecording,
    required this.recordingSeconds,
    required this.onPickPhoto,
    required this.onRemovePhoto,
    required this.onToggleRecord,
    required this.onClearAudio,
  });

  final TextEditingController descriptionController;
  final TextEditingController extraTextController;
  final int photoCount;
  final int maxPhotos;
  final bool hasAudio;
  final bool isRecordStarting;
  final bool isRecording;
  final int recordingSeconds;
  final VoidCallback onPickPhoto;
  final void Function(int index) onRemovePhoto;
  final VoidCallback onToggleRecord;
  final VoidCallback onClearAudio;

  @override
  State<EvidenceAttachPanel> createState() => _EvidenceAttachPanelState();
}

class _EvidenceAttachPanelState extends State<EvidenceAttachPanel> with TickerProviderStateMixin {
  late final AnimationController _pulse = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 750),
  )..addStatusListener((s) {
      if (s == AnimationStatus.completed) {
        _pulse.reverse();
      } else if (s == AnimationStatus.dismissed) {
        _pulse.forward();
      }
    });
  final GlobalKey _recordingBarKey = GlobalKey();

  @override
  void didUpdateWidget(EvidenceAttachPanel old) {
    super.didUpdateWidget(old);
    if (!old.isRecording && widget.isRecording) {
      _pulse.forward();
      SchedulerBinding.instance.addPostFrameCallback((_) {
        final ctx = _recordingBarKey.currentContext;
        if (ctx != null && mounted) {
          Scrollable.ensureVisible(
            ctx,
            duration: const Duration(milliseconds: 300),
            curve: Curves.easeOutCubic,
            alignment: 0.2,
          );
        }
      });
    }
    if (old.isRecording && !widget.isRecording) {
      _pulse
        ..stop()
        ..reset();
    }
  }

  @override
  void dispose() {
    _pulse.dispose();
    super.dispose();
  }

  String _timeLabel() {
    final s = widget.recordingSeconds;
    final m = (s ~/ 60).toString().padLeft(2, '0');
    final r = (s % 60).toString().padLeft(2, '0');
    return '$m:$r';
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final w = widget;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const AppSectionHeader(title: 'Descripción del incidente'),
        const SizedBox(height: AppSpacing.sm),
        TextField(
          controller: w.descriptionController,
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
          controller: w.extraTextController,
          maxLines: 3,
          maxLength: 10000,
          decoration: const InputDecoration(
            hintText: 'Detalle extra para el taller (opcional)',
          ),
        ),
        const SizedBox(height: AppSpacing.lg),
        const AppSectionHeader(title: 'Archivos'),
        const SizedBox(height: AppSpacing.xs),
        Text(
          'Podés sumar hasta ${w.maxPhotos} fotos (cada una máx. 5 MB).'
          ' El audio es opcional y reemplazable.',
          style: Theme.of(context).textTheme.bodySmall?.copyWith(color: scheme.onSurfaceVariant, height: 1.35),
        ),
        const SizedBox(height: AppSpacing.md),
        if (kIsWeb) ...[
          Card(
            color: scheme.surfaceContainerHighest,
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Row(
                children: [
                  Icon(Icons.info_outline_rounded, color: scheme.primary),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      'La grabación de audio no está disponible en el navegador. Usá la app en un teléfono (Android o iOS).',
                      style: TextStyle(color: scheme.onSurface, height: 1.35),
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: AppSpacing.md),
        ],
        if (w.isRecording) ...[
          _RecordingInProgress(
            key: _recordingBarKey,
            timeLabel: _timeLabel,
            pulsing: _pulse,
            scheme: scheme,
            onStop: w.onToggleRecord,
          ),
          const SizedBox(height: AppSpacing.md),
        ],
        if (w.isRecordStarting && !w.isRecording) ...[
          Card(
            color: scheme.primaryContainer.withValues(alpha: 0.45),
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Row(
                children: [
                  SizedBox(
                    width: 24,
                    height: 24,
                    child: CircularProgressIndicator(
                      strokeWidth: 2.5,
                      color: scheme.onPrimaryContainer,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      'Iniciando micrófono…',
                      style: TextStyle(
                        color: scheme.onPrimaryContainer,
                        fontWeight: FontWeight.w700,
                        fontSize: 15,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: AppSpacing.md),
        ],
        if (!w.isRecording)
          Wrap(
            spacing: AppSpacing.sm,
            runSpacing: AppSpacing.sm,
            children: [
              OutlinedButton.icon(
                onPressed: w.photoCount < w.maxPhotos ? w.onPickPhoto : null,
                icon: const Icon(Icons.add_a_photo_outlined),
                label: Text(w.photoCount < w.maxPhotos ? 'Agregar foto' : 'Máx. de fotos'),
              ),
              if (!kIsWeb)
                w.isRecordStarting
                    ? OutlinedButton.icon(
                        onPressed: null,
                        icon: const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        ),
                        label: const Text('Iniciando…'),
                      )
                    : OutlinedButton.icon(
                        onPressed: w.isRecordStarting ? null : w.onToggleRecord,
                        icon: const Icon(Icons.mic_outlined),
                        label: Text(
                          w.hasAudio ? 'Volver a grabar' : 'Grabar audio',
                        ),
                      ),
            ],
          )
        else
          const SizedBox.shrink(),
        if (w.photoCount > 0 || w.hasAudio) ...[
          const SizedBox(height: AppSpacing.md),
          Text(
            w.photoCount > 0 ? 'Fotos (${w.photoCount})' : 'Adjuntos',
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
                  color: scheme.onSurfaceVariant,
                  fontWeight: FontWeight.w600,
                ),
          ),
          const SizedBox(height: AppSpacing.xs),
          Wrap(
            spacing: AppSpacing.xs,
            runSpacing: AppSpacing.xs,
            children: [
              for (var i = 0; i < w.photoCount; i++)
                InputChip(
                  label: Text('Foto ${i + 1}'),
                  avatar: Icon(Icons.image_outlined, size: 18, color: scheme.primary),
                  deleteIcon: const Icon(Icons.close_rounded, size: 18),
                  onDeleted: w.isRecording ? null : () => w.onRemovePhoto(i),
                ),
              if (w.hasAudio)
                InputChip(
                  label: const Text('Audio listo'),
                  avatar: Icon(Icons.audiotrack_rounded, size: 18, color: scheme.primary),
                  deleteIcon: const Icon(Icons.close_rounded, size: 18),
                  onDeleted: w.isRecording ? null : w.onClearAudio,
                ),
            ],
          ),
        ] else
          Padding(
            padding: const EdgeInsets.only(top: AppSpacing.sm),
            child: Text(
              'Aún no hay archivos. Las fotos y el audio se envían como evidencia junto al reporte.',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(color: scheme.onSurfaceVariant),
            ),
          ),
      ],
    );
  }
}

class _RecordingInProgress extends StatelessWidget {
  const _RecordingInProgress({
    super.key,
    required this.timeLabel,
    required this.pulsing,
    required this.scheme,
    required this.onStop,
  });

  final String Function() timeLabel;
  final AnimationController pulsing;
  final ColorScheme scheme;
  final VoidCallback onStop;

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 3,
      color: scheme.error,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                FadeTransition(
                  opacity: Tween<double>(begin: 0.55, end: 1).animate(
                    CurvedAnimation(parent: pulsing, curve: Curves.easeInOut),
                  ),
                  child: const Icon(Icons.fiber_manual_record, color: Colors.white, size: 22),
                ),
                const SizedBox(width: 10),
                Text(
                  'GRABANDO',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        color: Colors.white,
                        fontWeight: FontWeight.w900,
                        letterSpacing: 0.5,
                      ),
                ),
                const Spacer(),
                Text(
                  timeLabel(),
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                        color: Colors.white,
                        fontWeight: FontWeight.w800,
                      ),
                ),
              ],
            ),
            const SizedBox(height: 14),
            FilledButton.icon(
              onPressed: onStop,
              style: FilledButton.styleFrom(
                backgroundColor: Colors.white,
                foregroundColor: scheme.error,
                padding: const EdgeInsets.symmetric(vertical: 14),
              ),
              icon: const Icon(Icons.stop_circle_outlined, size: 26),
              label: const Text(
                'Detener y guardar',
                style: TextStyle(fontWeight: FontWeight.w800, fontSize: 16),
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Hablá cerca del micrófono. Tocá el botón blanco arriba cuando termines.',
              textAlign: TextAlign.center,
              style: TextStyle(
                color: Colors.white.withValues(alpha: 0.92),
                fontSize: 12.5,
                height: 1.3,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
