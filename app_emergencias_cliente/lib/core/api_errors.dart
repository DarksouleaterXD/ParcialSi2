/// Maps API error payloads to user-facing messages (FastAPI `detail`).
String messageFromResponseBody(Object? decodedBody, {String fallback = 'Ocurrió un error.'}) {
  if (decodedBody is! Map) {
    return fallback;
  }
  final detail = decodedBody['detail'];
  if (detail is String) {
    return detail;
  }
  if (detail is List) {
    final parts = <String>[];
    for (final item in detail) {
      if (item is Map) {
        final msg = item['msg'];
        if (msg is String) {
          parts.add(msg);
        } else if (msg != null) {
          parts.add(msg.toString());
        } else {
          final t = item['type'];
          if (t is String) {
            parts.add(t);
          } else if (t != null) {
            parts.add(t.toString());
          }
        }
      } else if (item is String) {
        parts.add(item);
      }
    }
    if (parts.isNotEmpty) {
      return parts.join(' ');
    }
  }
  return fallback;
}

/// Centralized UX for [POST /auth/login] failures (aligned with web `LoginComponent`).
String messageForLoginFailure(int statusCode, Object? decodedBody) {
  switch (statusCode) {
    case 401:
      return 'Credenciales inválidas';
    case 403:
      return messageFromResponseBody(decodedBody, fallback: 'Cuenta deshabilitada');
    case 422:
      return messageFromResponseBody(decodedBody, fallback: 'Revisá los datos ingresados.');
    default:
      if (statusCode >= 500) {
        return 'No se pudo conectar con el servidor';
      }
      final fromBody = messageFromResponseBody(decodedBody, fallback: '');
      if (fromBody.isNotEmpty) {
        return fromBody;
      }
      return 'Credenciales inválidas o error de red.';
  }
}
