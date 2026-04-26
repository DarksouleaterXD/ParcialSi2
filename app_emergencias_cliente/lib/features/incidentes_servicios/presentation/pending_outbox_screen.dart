import 'package:flutter/material.dart';

import '../../../core/auth_storage.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/widgets/primary_button.dart';
import '../offline/pending_incident_draft.dart';
import '../offline/pending_incident_sync_service.dart';
import '../offline/pending_incidents_store.dart';

/// Cola CU-09: borradores sin enviar con reintento manual y descarte.
class PendingOutboxScreen extends StatefulWidget {
  const PendingOutboxScreen({
    super.key,
    required this.storage,
  });

  final AuthStorage storage;

  @override
  State<PendingOutboxScreen> createState() => _PendingOutboxScreenState();
}

class _PendingOutboxScreenState extends State<PendingOutboxScreen> {
  final _store = pendingIncidentsGlobal;
  late final PendingIncidentSyncService _sync = PendingIncidentSyncService(
    storage: widget.storage,
    store: _store,
  );

  var _busy = false;
  String? _busyId;

  List<PendingIncidentDraft> _items() => _store.listOrdered();

  Future<void> _refresh() async {
    setState(() {});
  }

  Future<void> _retryAll() async {
    setState(() => _busy = true);
    try {
      await _sync.syncAll();
    } finally {
      if (mounted) {
        setState(() => _busy = false);
      }
    }
  }

  Future<void> _retryOne(String localId) async {
    setState(() {
      _busy = true;
      _busyId = localId;
    });
    try {
      await _sync.syncDraftByLocalId(localId);
    } finally {
      if (mounted) {
        setState(() {
          _busy = false;
          _busyId = null;
        });
      }
    }
  }

  Future<void> _discard(PendingIncidentDraft d) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Descartar borrador'),
        content: const Text(
          'Se va a eliminar el reporte guardado en este dispositivo y los archivos adjuntos copiados. '
          'Esta acción no se puede deshacer.',
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancelar')),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Descartar'),
          ),
        ],
      ),
    );
    if (ok != true || !mounted) {
      return;
    }
    await _store.delete(d.localId);
    setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final items = _items();
    return Scaffold(
      appBar: AppBar(
        title: const Text('Pendientes de envío'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_rounded),
          onPressed: () => Navigator.of(context).pop(),
        ),
        actions: [
          IconButton(
            tooltip: 'Sincronizar todo',
            onPressed: _busy ? null : _retryAll,
            icon: _busy && _busyId == null
                ? const SizedBox(
                    width: 22,
                    height: 22,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.sync_rounded),
          ),
        ],
      ),
      body: items.isEmpty
          ? Center(
              child: Padding(
                padding: const EdgeInsets.all(AppSpacing.xl),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(Icons.cloud_done_outlined, size: 56, color: scheme.primary),
                    const SizedBox(height: AppSpacing.md),
                    Text(
                      'No hay reportes pendientes',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: AppSpacing.sm),
                    Text(
                      'Cuando no haya internet al enviar, el borrador aparece acá para reintentar.',
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: scheme.onSurfaceVariant),
                      textAlign: TextAlign.center,
                    ),
                  ],
                ),
              ),
            )
          : RefreshIndicator(
              onRefresh: _refresh,
              child: ListView.separated(
                padding: const EdgeInsets.all(AppSpacing.lg),
                itemCount: items.length + 1,
                separatorBuilder: (_, __) => const SizedBox(height: AppSpacing.md),
                itemBuilder: (context, i) {
                  if (i == 0) {
                    return Card(
                      color: scheme.secondaryContainer.withValues(alpha: 0.35),
                      child: Padding(
                        padding: const EdgeInsets.all(AppSpacing.md),
                        child: Text(
                          'Los reportes usan la misma clave de idempotencia hasta enviarse: '
                          'no se duplican incidentes al reintentar.',
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      ),
                    );
                  }
                  final d = items[i - 1];
                  final oneBusy = _busy && _busyId == d.localId;
                  return Card(
                    child: Padding(
                      padding: const EdgeInsets.all(AppSpacing.md),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          Row(
                            children: [
                              Icon(Icons.schedule_send_rounded, color: scheme.tertiary),
                              const SizedBox(width: AppSpacing.sm),
                              Expanded(
                                child: Text(
                                  'Pendiente de envío',
                                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                                        fontWeight: FontWeight.w800,
                                        color: scheme.onSurface,
                                      ),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: AppSpacing.sm),
                          Text(d.vehiculoLabel, style: Theme.of(context).textTheme.bodyLarge?.copyWith(fontWeight: FontWeight.w600)),
                          const SizedBox(height: AppSpacing.xxs),
                          Text(
                            'Guardado: ${_formatDate(d.savedAt)}',
                            style: Theme.of(context).textTheme.bodySmall?.copyWith(color: scheme.onSurfaceVariant),
                          ),
                          if (d.serverIncidentId != null) ...[
                            const SizedBox(height: AppSpacing.xxs),
                            Text(
                              'Incidente en servidor: #${d.serverIncidentId} (subiendo evidencias…)',
                              style: Theme.of(context).textTheme.bodySmall,
                            ),
                          ],
                          if (d.lastErrorMessage != null && d.lastErrorMessage!.isNotEmpty) ...[
                            const SizedBox(height: AppSpacing.sm),
                            Text(
                              d.lastErrorMessage!,
                              style: Theme.of(context).textTheme.bodySmall?.copyWith(color: scheme.error),
                            ),
                          ],
                          const SizedBox(height: AppSpacing.md),
                          PrimaryButton(
                            label: 'Reintentar ahora',
                            icon: Icons.upload_rounded,
                            isLoading: oneBusy,
                            loadingLabel: 'Enviando…',
                            onPressed: (_busy && !oneBusy) ? null : () => _retryOne(d.localId),
                          ),
                          const SizedBox(height: AppSpacing.sm),
                          SecondaryButton(
                            label: 'Descartar borrador',
                            icon: Icons.delete_outline_rounded,
                            onPressed: _busy ? null : () => _discard(d),
                          ),
                        ],
                      ),
                    ),
                  );
                },
              ),
            ),
    );
  }

  String _formatDate(DateTime d) {
    final l = d.toLocal();
    return '${l.day}/${l.month}/${l.year} ${l.hour.toString().padLeft(2, '0')}:${l.minute.toString().padLeft(2, '0')}';
  }
}
