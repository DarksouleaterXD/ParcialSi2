/// Mirrors backend [MeResponse] (`GET/PATCH /auth/me`).
class UserProfile {
  const UserProfile({
    required this.id,
    required this.nombre,
    required this.apellido,
    required this.email,
    this.telefono,
    this.estado,
    required this.roles,
    this.fotoPerfil,
    this.fechaRegistro,
  });

  final int id;
  final String nombre;
  final String apellido;
  final String email;
  final String? telefono;
  final String? estado;
  final List<String> roles;
  final String? fotoPerfil;
  final String? fechaRegistro;

  factory UserProfile.fromJson(Map<String, dynamic> json) {
    final rolesRaw = json['roles'];
    final roles = rolesRaw is List ? rolesRaw.map((e) => e.toString()).toList() : <String>[];
    final idRaw = json['id'];
    final id = idRaw is int ? idRaw : (idRaw is num ? idRaw.toInt() : 0);
    final fechaRaw = json['fecha_registro'];
    final fechaStr = fechaRaw == null
        ? null
        : fechaRaw is String
            ? fechaRaw
            : fechaRaw.toString();
    return UserProfile(
      id: id,
      nombre: _jsonReqStr(json['nombre']),
      apellido: _jsonReqStr(json['apellido']),
      email: _jsonReqStr(json['email']),
      telefono: _jsonOptStr(json['telefono']),
      estado: _jsonOptStr(json['estado']),
      roles: roles,
      fotoPerfil: _jsonOptStr(json['foto_perfil']),
      fechaRegistro: fechaStr,
    );
  }

  static String _jsonReqStr(Object? v) {
    if (v == null) {
      return '';
    }
    if (v is String) {
      return v;
    }
    return v.toString();
  }

  static String? _jsonOptStr(Object? v) {
    if (v == null) {
      return null;
    }
    if (v is String) {
      return v;
    }
    return v.toString();
  }
}
