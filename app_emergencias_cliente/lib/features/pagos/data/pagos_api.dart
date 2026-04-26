import '../../../core/authorized_client.dart' show ApiClientException, AuthorizedClient;

class PagoProcesado {
  const PagoProcesado({
    required this.id,
    required this.incidenteId,
    required this.clienteId,
    required this.tecnicoId,
    required this.montoTotal,
    required this.montoTaller,
    required this.comisionPlataforma,
    required this.metodoPago,
    required this.estado,
    this.createdAt,
  });

  final int id;
  final int incidenteId;
  final int clienteId;
  final int tecnicoId;
  final double montoTotal;
  final double montoTaller;
  final double comisionPlataforma;
  final String metodoPago;
  final String estado;
  final DateTime? createdAt;

  factory PagoProcesado.fromJson(Map<String, dynamic> json) {
    DateTime? parseDate(Object? v) {
      if (v is String && v.isNotEmpty) {
        return DateTime.tryParse(v);
      }
      return null;
    }

    return PagoProcesado(
      id: (json['id'] as num?)?.toInt() ?? 0,
      incidenteId: (json['incidente_id'] as num?)?.toInt() ?? 0,
      clienteId: (json['cliente_id'] as num?)?.toInt() ?? 0,
      tecnicoId: (json['tecnico_id'] as num?)?.toInt() ?? 0,
      montoTotal: (json['monto_total'] as num?)?.toDouble() ?? 0,
      montoTaller: (json['monto_taller'] as num?)?.toDouble() ?? 0,
      comisionPlataforma: (json['comision_plataforma'] as num?)?.toDouble() ?? 0,
      metodoPago: (json['metodo_pago'] as String?)?.trim() ?? 'TARJETA_SIMULADA',
      estado: (json['estado'] as String?)?.trim() ?? 'COMPLETADO',
      createdAt: parseDate(json['created_at']),
    );
  }
}

class PagosApi {
  PagosApi(this._client);

  final AuthorizedClient _client;

  static const String _base = '/pagos';

  Future<String> createPaymentIntent(int incidenteId) async {
    final json = await _client.postJson(
      '$_base/create-payment-intent/$incidenteId',
    );
    final fromSnake = json['client_secret'];
    if (fromSnake is String && fromSnake.trim().isNotEmpty) {
      return fromSnake;
    }
    final fromCamel = json['clientSecret'];
    if (fromCamel is String && fromCamel.trim().isNotEmpty) {
      return fromCamel;
    }
    throw ApiClientException(statusCode: 500, message: 'Respuesta inválida al crear PaymentIntent');
  }

  Future<PagoProcesado> procesarPago(
    int incidenteId,
    double monto, {
    String metodoPago = 'TARJETA_SIMULADA',
  }) async {
    final json = await _client.postJson(
      '$_base/incidentes/$incidenteId/procesar',
      body: <String, dynamic>{
        'monto_total': monto,
        'metodo_pago': metodoPago,
      },
    );
    return PagoProcesado.fromJson(json);
  }
}

