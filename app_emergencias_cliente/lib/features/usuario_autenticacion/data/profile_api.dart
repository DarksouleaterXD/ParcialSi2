import '../../../core/authorized_client.dart';
import '../domain/user_profile.dart';

/// CU-04: perfil autenticado (`GET` / `PATCH` / `POST` bajo `/auth/me`).
class ProfileApi {
  ProfileApi(this._client);

  final AuthorizedClient _client;

  Future<UserProfile> fetchProfile() async {
    final json = await _client.getJson('/auth/me');
    return UserProfile.fromJson(json);
  }

  /// Sends only keys present in [fields] (backend requires at least one field).
  Future<UserProfile> updateProfile(Map<String, dynamic> fields) async {
    if (fields.isEmpty) {
      throw StateError('No fields to update');
    }
    final json = await _client.patchJson('/auth/me', fields);
    return UserProfile.fromJson(json);
  }

  Future<void> changePassword({
    required String passwordActual,
    required String passwordNueva,
    required String passwordConfirmacion,
  }) async {
    await _client.postJson(
      '/auth/me/change-password',
      body: {
        'password_actual': passwordActual,
        'password_nueva': passwordNueva,
        'password_confirmacion': passwordConfirmacion,
      },
    );
  }
}
