import 'package:uuid/uuid.dart';

/// Cabecera `Idempotency-Key` del backend: `^[A-Za-z0-9._-]{8,128}$`.
String generateIncidentIdempotencyKey() {
  final raw = const Uuid().v4().replaceAll('-', '_');
  return 'idem_$raw';
}
