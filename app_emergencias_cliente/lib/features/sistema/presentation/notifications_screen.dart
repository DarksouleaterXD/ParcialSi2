import 'dart:async' show unawaited;

import 'package:flutter/material.dart';

import '../../../core/authorized_client.dart';
import '../data/notifications_api.dart';
import '../domain/app_notification.dart';

class NotificationsScreen extends StatefulWidget {
  const NotificationsScreen({
    super.key,
    required this.authorized,
    this.onSessionExpired,
  });

  final AuthorizedClient authorized;
  final VoidCallback? onSessionExpired;

  @override
  State<NotificationsScreen> createState() => _NotificationsScreenState();
}

class _NotificationsScreenState extends State<NotificationsScreen> {
  late final NotificationsApi _api = NotificationsApi(widget.authorized);
  bool _loading = true;
  String? _error;
  List<AppNotification> _items = const [];
  int _unread = 0;

  @override
  void initState() {
    super.initState();
    unawaited(_load());
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final page = await _api.list(page: 1, pageSize: 50);
      final c = await _api.unreadCount();
      if (!mounted) {
        return;
      }
      setState(() {
        _items = page.items;
        _unread = c;
        _loading = false;
      });
    } on SessionExpiredException {
      widget.onSessionExpired?.call();
      if (mounted) {
        setState(() {
          _loading = false;
          _error = 'Sesión expirada.';
        });
      }
    } catch (e) {
      if (!mounted) {
        return;
      }
      setState(() {
        _loading = false;
        _error = e is ApiClientException ? e.message : e.toString();
      });
    }
  }

  Future<void> _markRead(AppNotification n) async {
    if (n.leida) {
      return;
    }
    try {
      final u = await _api.patchRead(n.id);
      if (!mounted) {
        return;
      }
      setState(() {
        _items = _items.map((x) => x.id == n.id ? u : x).toList();
        _unread = _unread > 0 ? _unread - 1 : 0;
      });
    } on SessionExpiredException {
      widget.onSessionExpired?.call();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(e is ApiClientException ? e.message : e.toString())),
        );
      }
    }
  }

  Future<void> _markAll() async {
    try {
      await _api.markAllRead();
      if (!mounted) {
        return;
      }
      await _load();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Todas las notificaciones marcadas como leídas.')),
        );
      }
    } on SessionExpiredException {
      widget.onSessionExpired?.call();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(e is ApiClientException ? e.message : e.toString())),
        );
      }
    }
  }

  String _formatDate(DateTime? d) {
    if (d == null) {
      return '';
    }
    final local = d.toLocal();
    return '${local.day.toString().padLeft(2, '0')}/${local.month.toString().padLeft(2, '0')}/${local.year} '
        '${local.hour.toString().padLeft(2, '0')}:${local.minute.toString().padLeft(2, '0')}';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Notificaciones'),
        actions: [
          if (_items.isNotEmpty && _unread > 0)
            TextButton(
              onPressed: _markAll,
              child: const Text('Marcar todas leídas'),
            ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _load,
        child: _buildBody(),
      ),
    );
  }

  Widget _buildBody() {
    if (_loading) {
      return ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        children: const [
          SizedBox(height: 120),
          Center(child: CircularProgressIndicator()),
        ],
      );
    }
    if (_error != null) {
      return ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        children: [
          const SizedBox(height: 48),
          Padding(
            padding: const EdgeInsets.all(24),
            child: Text(
              _error!,
              textAlign: TextAlign.center,
            ),
          ),
        ],
      );
    }
    if (_items.isEmpty) {
      return ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        children: [
          const SizedBox(height: 64),
          Icon(
            Icons.notifications_off_outlined,
            size: 56,
            color: Theme.of(context).colorScheme.outline,
          ),
          const SizedBox(height: 16),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 32),
            child: Text(
              'No tenés notificaciones. Cuando un técnico tome tu emergencia o avance el servicio,'
              ' los avisas aparecerán acá.',
              textAlign: TextAlign.center,
              style: TextStyle(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
                height: 1.4,
              ),
            ),
          ),
        ],
      );
    }
    return ListView.separated(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
      itemCount: _items.length,
      separatorBuilder: (_, __) => const SizedBox(height: 8),
      itemBuilder: (context, i) {
        final n = _items[i];
        return Material(
          color: n.leida
              ? Theme.of(context).colorScheme.surfaceContainerLowest
              : Theme.of(context).colorScheme.primaryContainer.withValues(alpha: 0.35),
          borderRadius: BorderRadius.circular(16),
          child: InkWell(
            borderRadius: BorderRadius.circular(16),
            onTap: () => unawaited(_markRead(n)),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      if (!n.leida)
                        Padding(
                          padding: const EdgeInsets.only(top: 6, right: 8),
                          child: Container(
                            width: 8,
                            height: 8,
                            decoration: BoxDecoration(
                              color: Theme.of(context).colorScheme.primary,
                              shape: BoxShape.circle,
                            ),
                          ),
                        ),
                      Expanded(
                        child: Text(
                          n.titulo,
                          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                fontWeight: n.leida ? FontWeight.w500 : FontWeight.w700,
                              ),
                        ),
                      ),
                    ],
                  ),
                  if (n.fechaHora != null) ...[
                    const SizedBox(height: 4),
                    Text(
                      _formatDate(n.fechaHora),
                      style: Theme.of(context).textTheme.labelSmall?.copyWith(
                            color: Theme.of(context).colorScheme.onSurfaceVariant,
                          ),
                    ),
                  ],
                  const SizedBox(height: 6),
                  Text(
                    n.mensaje,
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}
