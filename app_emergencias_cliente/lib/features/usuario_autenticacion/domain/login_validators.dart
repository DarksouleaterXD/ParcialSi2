/// Same rules as [frontend_talleres_web/.../login.validators.ts] `emailFlexibleValidator`.
String? validateLoginEmail(String? value) {
  if (value == null || value.trim().isEmpty) {
    return 'Ingresá tu correo.';
  }
  final v = value.trim().toLowerCase();
  if (!v.contains('@')) {
    return 'El formato del correo no es válido.';
  }
  final parts = v.split('@');
  if (parts.length != 2 || parts[0].isEmpty || parts[1].isEmpty) {
    return 'El formato del correo no es válido.';
  }
  return null;
}

/// Same rules as web login: [Validators.required, Validators.minLength(4)].
String? validateLoginPassword(String? value) {
  if (value == null || value.isEmpty) {
    return 'Ingresá tu contraseña.';
  }
  if (value.length < 4) {
    return 'Mínimo 4 caracteres.';
  }
  return null;
}
