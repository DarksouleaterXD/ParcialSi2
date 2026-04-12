import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';

const _kToken = 'access_token';
const _kRoles = 'roles_json';

class AuthStorage {
  AuthStorage({FlutterSecureStorage? storage})
      : _storage = storage ?? const FlutterSecureStorage();

  final FlutterSecureStorage _storage;

  Future<void> saveSession({required String token, required List<String> roles}) async {
    await _storage.write(key: _kToken, value: token);
    await _storage.write(key: _kRoles, value: jsonEncode(roles));
  }

  Future<String?> readToken() => _storage.read(key: _kToken);

  Future<List<String>> readRoles() async {
    final raw = await _storage.read(key: _kRoles);
    if (raw == null || raw.isEmpty) {
      return [];
    }
    try {
      final list = jsonDecode(raw) as List<dynamic>;
      return list.map((e) => e.toString()).toList();
    } catch (_) {
      return [];
    }
  }

  Future<void> clear() async {
    await _storage.delete(key: _kToken);
    await _storage.delete(key: _kRoles);
  }
}
