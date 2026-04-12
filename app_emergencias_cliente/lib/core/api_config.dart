/// Base URL del API FastAPI.
/// - Chrome/desktop: `http://localhost:8000/api`
/// - Emulador Android: `http://10.0.2.2:8000/api`
/// Sobrescribir al ejecutar: `flutter run --dart-define=API_BASE=http://10.0.2.2:8000/api`
const String kApiBase = String.fromEnvironment(
  'API_BASE',
  defaultValue: 'http://localhost:8000/api',
);
