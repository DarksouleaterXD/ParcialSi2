import '../../../core/auth_api.dart';

/// Thin wrapper over [AuthApi] for the `usuario_autenticacion` feature (testable seam).
class AuthRemoteDataSource {
  AuthRemoteDataSource(this._api);
  final AuthApi _api;

  Future<SessionStatus> validateSession(String token) => _api.validateSession(token);

  Future<Map<String, dynamic>> login({required String email, required String password}) =>
      _api.login(email: email, password: password);

  Future<void> logout(String token) => _api.logout(token);
}
