import '../../../core/authorized_client.dart';
import '../domain/app_notification.dart';

class NotificationsApi {
  NotificationsApi(this._client);

  final AuthorizedClient _client;

  static const String _base = '/sistema/notificaciones';

  Future<AppNotificationListPage> list({int page = 1, int pageSize = 30, bool soloNoLeidas = false}) async {
    final q = soloNoLeidas ? '&solo_no_leidas=true' : '';
    final json = await _client.getJson('$_base?page=$page&page_size=$pageSize$q');
    return AppNotificationListPage.fromJson(json);
  }

  Future<int> unreadCount() async {
    final json = await _client.getJson('$_base/no-leidas');
    return (json['count'] as num?)?.toInt() ?? 0;
  }

  Future<AppNotification> patchRead(int id, {bool leida = true}) async {
    final json = await _client.patchJson('$_base/$id', <String, dynamic>{'leida': leida});
    return AppNotification.fromJson(json);
  }

  Future<int> markAllRead() async {
    final json = await _client.postJson('$_base/marcar-todas-leidas', body: <String, dynamic>{});
    return (json['updated'] as num?)?.toInt() ?? 0;
  }

  Future<void> registerPushToken(String token, {String plataforma = 'android'}) async {
    await _client.postJson(
      '$_base/push-token',
      body: <String, dynamic>{'token': token, 'plataforma': plataforma},
    );
  }

  Future<void> unregisterPushToken(String token) async {
    await _client.postJson('$_base/push-token/desregistrar', body: <String, dynamic>{'token': token});
  }
}
