/// Base URL del API FastAPI (debe terminar en `/api`, sin barra final extra).
///
/// - PC / Chrome: `http://localhost:8000/api`
/// - Emulador Android: `http://10.0.2.2:8000/api`
/// - **Teléfono físico (misma WiFi que el PC):** `http://<IP_LAN_DEL_PC>:8000/api`
///   Ejemplo: `http://192.168.0.15:8000/api`. En Windows: `ipconfig` → IPv4.
///
/// Sobrescribir al ejecutar:
/// `flutter run --dart-define=API_BASE=http://192.168.0.15:8000/api`
///
/// El backend debe escuchar en todas las interfaces, p. ej.:
/// `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
const String kApiBase = String.fromEnvironment(
  'API_BASE',
  defaultValue: 'http://localhost:8000/api',
);
