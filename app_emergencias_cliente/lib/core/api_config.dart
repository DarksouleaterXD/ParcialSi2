import 'package:flutter/foundation.dart';

/// Base URL del API FastAPI (debe terminar en `/api`, sin barra final extra).
///
/// - **Release sin `--dart-define`:** usa [kDefaultReleaseApiBase] (producción en Render);
///   cambiá esa constante si el deploy cambia o preferí compilar con `API_BASE`.
/// - **Debug / profile sin variable:** `http://localhost:8000/api` (o emulador con `10.0.2.2`).
///
/// Sobrescribir al ejecutar o al buildear APK:
/// `flutter run --dart-define=API_BASE=https://parcialsi2.onrender.com/api`
const String kDefaultReleaseApiBase = 'https://parcialsi2.onrender.com/api';

/// Resuelve la URL: `API_BASE` (si se definió) > release por defecto > localhost en debug.
String get kApiBase {
  const fromEnv = String.fromEnvironment('API_BASE', defaultValue: '');
  if (fromEnv.isNotEmpty) {
    return fromEnv;
  }
  if (kReleaseMode) {
    return kDefaultReleaseApiBase;
  }
  return 'http://localhost:8000/api';
}
