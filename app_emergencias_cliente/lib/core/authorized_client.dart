import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';

import 'api_config.dart';
import 'api_errors.dart';
import 'auth_storage.dart';

/// Thrown when the server returns 401 and local session was cleared.
class SessionExpiredException implements Exception {
  SessionExpiredException([this.message = 'Sesión expirada. Iniciá sesión de nuevo.']);
  final String message;
}

/// HTTP helper for authenticated routes: injects Bearer token and clears storage on 401.
class AuthorizedClient {
  AuthorizedClient({required AuthStorage storage, http.Client? httpClient})
      : _storage = storage,
        _http = httpClient ?? http.Client();

  final AuthStorage _storage;
  final http.Client _http;

  Uri _uri(String path) => Uri.parse('$kApiBase$path');

  Future<http.Response> _send(Future<http.Response> Function() request) async {
    try {
      return await request();
    } on SocketException {
      throw ApiClientException(statusCode: 0, message: 'No se pudo conectar con el servidor');
    } on http.ClientException {
      throw ApiClientException(statusCode: 0, message: 'No se pudo conectar con el servidor');
    }
  }

  Future<Map<String, dynamic>> getJson(String path) async {
    final token = await _storage.readToken();
    if (token == null || token.isEmpty) {
      throw SessionExpiredException('No hay sesión activa.');
    }
    final res = await _send(
      () => _http.get(
        _uri(path),
        headers: {
          'Authorization': 'Bearer $token',
          'Accept': 'application/json',
        },
      ),
    );
    return _handleJson(res);
  }

  /// Multipart POST (e.g. evidencias con `archivo`). Field names must match el backend.
  Future<Map<String, dynamic>> postMultipart(
    String path, {
    required Map<String, String> fields,
    List<http.MultipartFile> files = const [],
    Map<String, String> extraHeaders = const {},
  }) async {
    final token = await _storage.readToken();
    if (token == null || token.isEmpty) {
      throw SessionExpiredException('No hay sesión activa.');
    }
    final uri = _uri(path);
    final req = http.MultipartRequest('POST', uri)
      ..headers['Authorization'] = 'Bearer $token'
      ..headers['Accept'] = 'application/json'
      ..headers.addAll(extraHeaders)
      ..fields.addAll(fields)
      ..files.addAll(files);
    late http.Response res;
    try {
      final streamed = await _http.send(req);
      res = await http.Response.fromStream(streamed);
    } on SocketException {
      throw ApiClientException(statusCode: 0, message: 'No se pudo conectar con el servidor');
    } on http.ClientException {
      throw ApiClientException(statusCode: 0, message: 'No se pudo conectar con el servidor');
    }
    return _handleJson(res);
  }

  /// Helper for a single file field `archivo` (CU-09 evidencias).
  static http.MultipartFile fileField({
    required String fieldName,
    required List<int> bytes,
    required String filename,
    required String mimeType,
  }) {
    final ct = MediaType.parse(mimeType);
    return http.MultipartFile.fromBytes(
      fieldName,
      bytes,
      filename: filename,
      contentType: ct,
    );
  }

  Future<Map<String, dynamic>> postJson(
    String path, {
    Map<String, dynamic>? body,
    Map<String, String> extraHeaders = const {},
  }) async {
    final token = await _storage.readToken();
    if (token == null || token.isEmpty) {
      throw SessionExpiredException('No hay sesión activa.');
    }
    final headers = <String, String>{
      'Authorization': 'Bearer $token',
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      ...extraHeaders,
    };
    final res = await _send(
      () => _http.post(
        _uri(path),
        headers: headers,
        body: body == null ? null : jsonEncode(body),
      ),
    );
    return _handleJson(res);
  }

  Future<Map<String, dynamic>> patchJson(String path, Map<String, dynamic> body) async {
    final token = await _storage.readToken();
    if (token == null || token.isEmpty) {
      throw SessionExpiredException('No hay sesión activa.');
    }
    final res = await _send(
      () => _http.patch(
        _uri(path),
        headers: {
          'Authorization': 'Bearer $token',
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: jsonEncode(body),
      ),
    );
    return _handleJson(res);
  }

  Future<Map<String, dynamic>> delete(String path) async {
    final token = await _storage.readToken();
    if (token == null || token.isEmpty) {
      throw SessionExpiredException('No hay sesión activa.');
    }
    final res = await _send(
      () => _http.delete(
        _uri(path),
        headers: {
          'Authorization': 'Bearer $token',
          'Accept': 'application/json',
        },
      ),
    );
    return _handleJson(res);
  }

  Future<Map<String, dynamic>> _handleJson(http.Response res) async {
    if (res.statusCode == 204) {
      return <String, dynamic>{};
    }
    final raw = res.body;
    Object? decoded = const <String, dynamic>{};
    if (raw.isNotEmpty) {
      try {
        decoded = jsonDecode(raw);
      } catch (_) {
        decoded = const <String, dynamic>{};
      }
    }

    if (res.statusCode == 401) {
      await _storage.clear();
      throw SessionExpiredException(
        messageFromResponseBody(decoded, fallback: 'Sesión inválida o expirada.'),
      );
    }

    if (res.statusCode >= 400) {
      final msg = messageFromResponseBody(decoded, fallback: _defaultForStatus(res.statusCode));
      throw ApiClientException(statusCode: res.statusCode, message: msg);
    }

    if (decoded is Map<String, dynamic>) {
      return decoded;
    }
    return <String, dynamic>{};
  }

  String _defaultForStatus(int code) {
    return switch (code) {
      403 => 'No tenés permiso para esta acción.',
      404 => 'Recurso no encontrado.',
      409 => 'Conflicto: la operación no se puede completar.',
      422 => 'Los datos enviados no son válidos.',
      _ => code >= 500 ? 'No se pudo conectar con el servidor' : 'Solicitud no procesada.',
    };
  }
}

class ApiClientException implements Exception {
  ApiClientException({required this.statusCode, required this.message});
  final int statusCode;
  final String message;

  @override
  String toString() => message;
}
