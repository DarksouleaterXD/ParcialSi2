import 'package:flutter/material.dart';

import '../../../core/auth_storage.dart';
import '../../../core/authorized_client.dart';
import '../../../core/theme/app_spacing.dart';
import '../data/incidents_api.dart';
import '../data/incidents_repository.dart';

class CalificacionScreen extends StatefulWidget {
  const CalificacionScreen({
    super.key,
    required this.storage,
    required this.incidenteId,
    required this.onSessionExpired,
  });

  final AuthStorage storage;
  final int incidenteId;
  final VoidCallback onSessionExpired;

  @override
  State<CalificacionScreen> createState() => _CalificacionScreenState();
}

class _CalificacionScreenState extends State<CalificacionScreen> {
  late final AuthorizedClient _authorizedClient = AuthorizedClient(storage: widget.storage);
  late final IncidentsRepository _repo = IncidentsRepository(IncidentsApi(_authorizedClient));
  final TextEditingController _commentController = TextEditingController();

  int _rating = 5;
  bool _submitting = false;
  String? _inlineError;

  @override
  void dispose() {
    _commentController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_submitting) {
      return;
    }
    final messenger = ScaffoldMessenger.of(context);
    setState(() {
      _submitting = true;
      _inlineError = null;
    });
    try {
      await _repo.calificarIncidente(widget.incidenteId.toString(), _rating, _commentController.text);
      if (!mounted) {
        return;
      }
      messenger.showSnackBar(
        const SnackBar(content: Text('Gracias por tu calificación. Seguimos mejorando para vos.')),
      );
      Navigator.of(context).popUntil((route) => route.isFirst);
    } on SessionExpiredException {
      if (mounted) {
        widget.onSessionExpired();
      }
    } on ApiClientException catch (e) {
      if (mounted) {
        setState(() {
          _inlineError = e.message;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          _inlineError = 'No se pudo enviar la calificación.';
        });
      }
    } finally {
      if (mounted) {
        setState(() {
          _submitting = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(title: Text('Calificar servicio #${widget.incidenteId}')),
      body: ListView(
        padding: const EdgeInsets.all(AppSpacing.lg),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(AppSpacing.lg),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '¿Cómo fue tu experiencia?',
                    style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800),
                  ),
                  const SizedBox(height: AppSpacing.md),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: List<Widget>.generate(5, (index) {
                      final value = index + 1;
                      return IconButton(
                        onPressed: _submitting
                            ? null
                            : () {
                                setState(() {
                                  _rating = value;
                                });
                              },
                        iconSize: 34,
                        color: value <= _rating ? const Color(0xFFF59E0B) : scheme.outlineVariant,
                        icon: Icon(value <= _rating ? Icons.star_rounded : Icons.star_border_rounded),
                      );
                    }),
                  ),
                  const SizedBox(height: AppSpacing.sm),
                  Text(
                    'Puntuación: $_rating / 5',
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: scheme.onSurfaceVariant),
                  ),
                  const SizedBox(height: AppSpacing.lg),
                  TextField(
                    controller: _commentController,
                    enabled: !_submitting,
                    maxLength: 500,
                    minLines: 3,
                    maxLines: 5,
                    decoration: const InputDecoration(
                      labelText: 'Comentario (opcional)',
                      hintText: 'Contanos cómo fue la atención del técnico.',
                      border: OutlineInputBorder(),
                    ),
                  ),
                  if (_inlineError != null) ...[
                    const SizedBox(height: AppSpacing.sm),
                    Text(
                      _inlineError!,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: scheme.error),
                    ),
                  ],
                  const SizedBox(height: AppSpacing.md),
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton(
                      style: FilledButton.styleFrom(
                        backgroundColor: const Color(0xFFF97316),
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(vertical: 16),
                      ),
                      onPressed: _submitting ? null : _submit,
                      child: _submitting
                          ? const SizedBox(
                              width: 20,
                              height: 20,
                              child: CircularProgressIndicator(strokeWidth: 2.2, color: Colors.white),
                            )
                          : const Text('Enviar Calificación'),
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
