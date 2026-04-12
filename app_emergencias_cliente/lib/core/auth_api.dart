import 'dart:convert';

import 'package:http/http.dart' as http;

import 'api_config.dart';

class AuthApi {
  AuthApi({http.Client? client}) : _client = client ?? http.Client();

  final http.Client _client;

  Uri _u(String path) => Uri.parse('$kApiBase$path');

  Future<Map<String, dynamic>> login({required String email, required String password}) async {
    final res = await _client.post(
      _u('/auth/login'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'email': email, 'password': password}),
    );
    final body = res.body.isEmpty ? <String, dynamic>{} : jsonDecode(res.body) as Map<String, dynamic>;
    if (res.statusCode >= 400) {
      final detail = body['detail'];
      throw AuthException(res.statusCode, detail is String ? detail : 'Error de autenticación');
    }
    return body;
  }

  Future<void> logout(String bearerToken) async {
    final res = await _client.post(
      _u('/auth/logout'),
      headers: {
        'Authorization': 'Bearer $bearerToken',
        'Content-Type': 'application/json',
      },
    );
    if (res.statusCode >= 400 && res.statusCode != 401) {
      throw AuthException(res.statusCode, 'No se pudo cerrar sesión');
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
