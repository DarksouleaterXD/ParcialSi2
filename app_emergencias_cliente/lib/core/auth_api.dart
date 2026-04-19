import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;

import 'api_config.dart';
import 'api_errors.dart';

/// Result of [AuthApi.validateSession] (GET /auth/me).
enum SessionStatus {
  /// 200 — token accepted.
  valid,

  /// 401/403 — clear local session.
  unauthorized,

  /// Network / 5xx / unexpected — keep token, allow user to retry.
  transientFailure,
}

class AuthApi {
  AuthApi({http.Client? client}) : _client = client ?? http.Client();

  final http.Client _client;

  Uri _u(String path) => Uri.parse('$kApiBase$path');

  /// Calls [GET /auth/me]. Does not throw for transport errors; returns [SessionStatus].
  Future<SessionStatus> validateSession(String bearerToken) async {
    try {
      final res = await _client.get(
        _u('/auth/me'),
        headers: {
          'Authorization': 'Bearer $bearerToken',
          'Accept': 'application/json',
        },
      );
      if (res.statusCode == 200) {
        return SessionStatus.valid;
      }
      if (res.statusCode == 401 || res.statusCode == 403) {
        return SessionStatus.unauthorized;
      }
      if (res.statusCode >= 500) {
        return SessionStatus.transientFailure;
      }
      // Other 4xx on /me: do not clear token (likely routing/version mismatch).
      return SessionStatus.transientFailure;
    } on SocketException {
      return SessionStatus.transientFailure;
    } on http.ClientException {
      return SessionStatus.transientFailure;
    } catch (_) {
      return SessionStatus.transientFailure;
    }
  }

  Future<Map<String, dynamic>> login({required String email, required String password}) async {
    final body = jsonEncode({
      'email': email.trim().toLowerCase(),
      'password': password,
    });
    late final http.Response res;
    try {
      res = await _client.post(
        _u('/auth/login'),
        headers: {'Content-Type': 'application/json', 'Accept': 'application/json'},
        body: body,
      );
    } on SocketException {
      throw AuthException(0, 'No se pudo conectar con el servidor');
    } on http.ClientException {
      throw AuthException(0, 'No se pudo conectar con el servidor');
    }

    Object? decoded = const <String, dynamic>{};
    if (res.body.isNotEmpty) {
      try {
        decoded = jsonDecode(res.body);
      } catch (_) {
        throw AuthException(res.statusCode, 'Respuesta del servidor no válida.');
      }
    }
    if (res.statusCode == 200 && decoded is Map<String, dynamic>) {
      return decoded;
    }
    final msg = messageForLoginFailure(res.statusCode, decoded);
    throw AuthException(res.statusCode, msg);
  }

  /// Best-effort [POST /auth/logout]; never throws (local storage is cleared by the caller).
  Future<void> logout(String bearerToken) async {
    try {
      final res = await _client.post(
        _u('/auth/logout'),
        headers: {
          'Authorization': 'Bearer $bearerToken',
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
      );
      if (res.statusCode >= 200 && res.statusCode < 300) {
        return;
      }
      if (res.statusCode == 401) {
        return;
      }
      if (res.statusCode >= 400 && res.body.isNotEmpty) {
        try {
          jsonDecode(res.body);
        } catch (_) {
          /* ignore malformed body */
        }
      }
    } on SocketException {
      return;
    } on http.ClientException {
      return;
    } catch (_) {
      return;
    }
  }
}

class AuthException implements Exception {
  AuthException(this.statusCode, this.message);
  final int statusCode;
  final String message;

  @override
  String toString() => message;
}
