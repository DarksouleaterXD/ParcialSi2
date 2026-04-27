import 'dart:async' show StreamSubscription;

import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:permission_handler/permission_handler.dart';

import '../features/sistema/data/notifications_api.dart';
import 'authorized_client.dart';

/// Manejador en segundo plano (debe ser función de nivel superior).
@pragma('vm:entry-point')
Future<void> firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  await Firebase.initializeApp();
  if (kDebugMode) {
    debugPrint('FCM background: ${message.messageId}');
  }
}

/// [FirebaseMessaging.onBackgroundMessage] debe registrarse en [main] antes de
/// [initializePushMessaging] y de [runApp].
Future<void> initializePushMessaging({required GlobalKey<NavigatorState> navigatorKey}) async {
  try {
    await Firebase.initializeApp();
  } on Object catch (e, st) {
    throw StateError('No se pudo inicializar Firebase. Verificá google-services.json. $e\n$st');
  }

  if (defaultTargetPlatform == TargetPlatform.android) {
    final status = await Permission.notification.status;
    if (status.isDenied) {
      await Permission.notification.request();
    }
  }
  if (defaultTargetPlatform == TargetPlatform.iOS) {
    await FirebaseMessaging.instance.requestPermission();
    await FirebaseMessaging.instance.setForegroundNotificationPresentationOptions(
      alert: true,
      badge: true,
      sound: true,
    );
  }
  FirebaseMessaging.onMessage.listen((m) => _showForegroundSnack(m, navigatorKey));
}

void _showForegroundSnack(RemoteMessage m, GlobalKey<NavigatorState> key) {
  final ctx = key.currentContext;
  if (ctx == null || !ctx.mounted) {
    return;
  }
  final title = m.notification?.title;
  final body = m.notification?.body ?? m.data['body']?.toString();
  if (body == null && title == null) {
    return;
  }
  final line = [if (title != null && title.isNotEmpty) title, if (body != null) body]
      .join(' — ');
  ScaffoldMessenger.maybeOf(ctx)?.showSnackBar(SnackBar(content: Text(line)));
}

StreamSubscription<String>? _tokenRefreshSub;

/// Sube el token FCM al backend (sesión requerida) y reintenta al renovarse.
Future<void> registerPushTokenWithBackend(AuthorizedClient client) async {
  await _tokenRefreshSub?.cancel();
  _tokenRefreshSub = null;
  try {
    final t = await _getDeviceToken();
    if (t == null || t.isEmpty) {
      return;
    }
    await _registerWithApi(client, t);
    _tokenRefreshSub = FirebaseMessaging.instance.onTokenRefresh.listen(
      (newT) {
        if (newT.isEmpty) {
          return;
        }
        // ignore: discarded_futures
        _registerWithApi(client, newT);
      },
    );
  } on Object catch (e) {
    if (kDebugMode) {
      debugPrint('registerPushTokenWithBackend: $e');
    }
  }
}

/// Best-effort desregistro en logout; el JWT aún debe ser válido.
Future<void> unregisterPushTokenOnLogout(AuthorizedClient client) async {
  await _tokenRefreshSub?.cancel();
  _tokenRefreshSub = null;
  try {
    final t = await FirebaseMessaging.instance.getToken();
    if (t == null || t.isEmpty) {
      return;
    }
    await NotificationsApi(client).unregisterPushToken(t);
  } on Object catch (_) {
    // Ignorar si el servidor o la sesión ya no están disponibles.
  }
}

Future<String?> _getDeviceToken() async {
  if (defaultTargetPlatform == TargetPlatform.iOS) {
    await FirebaseMessaging.instance.requestPermission();
  }
  return FirebaseMessaging.instance.getToken();
}

String _plataformaLabel() {
  if (defaultTargetPlatform == TargetPlatform.iOS) {
    return 'ios';
  }
  return 'android';
}

Future<void> _registerWithApi(AuthorizedClient client, String token) async {
  await NotificationsApi(client).registerPushToken(token, plataforma: _plataformaLabel());
}
