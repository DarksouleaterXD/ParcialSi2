import 'pagos_api.dart';

class PagosRepository {
  PagosRepository(this._api);

  final PagosApi _api;

  Future<PaymentIntentData> createPaymentIntent(int incidenteId) {
    return _api.createPaymentIntent(incidenteId);
  }

  Future<PagoProcesado> procesarPago(
    int incidenteId,
    double monto, {
    String metodoPago = 'TARJETA_SIMULADA',
  }) {
    return _api.procesarPago(incidenteId, monto, metodoPago: metodoPago);
  }
}

