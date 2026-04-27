import '../../../core/authorized_client.dart' show ApiClientException, AuthorizedClient;
import 'package:flutter/foundation.dart';

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

class PagoListItem {
  const PagoListItem({
    required this.id,
    required this.incidenteId,
    required this.estado,
    required this.montoTotal,
  });

  final int id;
  final int incidenteId;
  final String estado;
  final double montoTotal;

  factory PagoListItem.fromJson(Map<String, dynamic> json) {
    return PagoListItem(
      id: (json['id'] as num?)?.toInt() ?? 0,
      incidenteId: (json['incidente_id'] as num?)?.toInt() ?? 0,
      estado: ((json['estado'] as String?) ?? '').trim(),
      montoTotal: (json['monto_total'] as num?)?.toDouble() ?? 0,
    );
  }
}

class PagoListPage {
  const PagoListPage({
    required this.items,
    required this.total,
    required this.page,
    required this.pageSize,
  });

  final List<PagoListItem> items;
  final int total;
  final int page;
  final int pageSize;

  factory PagoListPage.fromJson(Map<String, dynamic> json) {
    final raw = json['items'];
    final items = <PagoListItem>[];
    if (raw is List) {
      for (final e in raw) {
        if (e is Map<String, dynamic>) {
          items.add(PagoListItem.fromJson(e));
        } else if (e is Map) {
          items.add(PagoListItem.fromJson(e.map((k, v) => MapEntry(k.toString(), v))));
        }
      }
    }
    return PagoListPage(
      items: items,
      total: (json['total'] as num?)?.toInt() ?? 0,
      page: (json['page'] as num?)?.toInt() ?? 1,
      pageSize: (json['page_size'] as num?)?.toInt() ?? 10,
    );
  }
}

class PagosApi {
  PagosApi(this._client);

  final AuthorizedClient _client;

  static const String _base = '/pagos';

  Future<PaymentIntentData> createPaymentIntent(int incidenteId) async {
    late final Map<String, dynamic> json;
    try {
      json = await _client.postJson(
        '$_base/create-payment-intent/$incidenteId',
      );
    } on ApiClientException catch (e) {
      if (kDebugMode) {
        debugPrint('createPaymentIntent($incidenteId) failed: ${e.statusCode} ${e.message}');
      }
      rethrow;
    }
    final fromSnake = json['client_secret'];
    if (fromSnake is String && fromSnake.trim().isNotEmpty) {
      return PaymentIntentData.fromJson(json);
    }
    final fromCamel = json['clientSecret'];
    if (fromCamel is String && fromCamel.trim().isNotEmpty) {
      return PaymentIntentData.fromJson(json);
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

  Future<PagoListPage> listPagos({int page = 1, int pageSize = 100}) async {
    final json = await _client.getJson('$_base?page=$page&page_size=$pageSize');
    return PagoListPage.fromJson(json);
  }
}

class PaymentIntentData {
  const PaymentIntentData({
    required this.clientSecret,
    required this.montoTotal,
    required this.currency,
  });

  final String clientSecret;
  final double montoTotal;
  final String currency;

  factory PaymentIntentData.fromJson(Map<String, dynamic> json) {
    final fromSnake = (json['client_secret'] as String?)?.trim();
    final fromCamel = (json['clientSecret'] as String?)?.trim();
    final secret = (fromSnake?.isNotEmpty == true ? fromSnake : fromCamel) ?? '';
    final monto = (json['monto_total'] as num?)?.toDouble() ?? 0;
    final currency = ((json['currency'] as String?) ?? 'usd').trim().toUpperCase();
    if (secret.isEmpty || monto <= 0) {
      throw ApiClientException(
        statusCode: 500,
        message: 'Respuesta inválida al crear PaymentIntent',
      );
    }
    return PaymentIntentData(
      clientSecret: secret,
      montoTotal: monto,
      currency: currency,
    );
  }
}

