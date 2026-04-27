import 'package:http/http.dart' as http;

import '../../../core/authorized_client.dart';
import '../domain/incident.dart';
import 'incident_dto.dart';

/// Cliente HTTP para `/api/incidentes-servicios`.
class IncidentsApi {
  IncidentsApi(this._client);

  final AuthorizedClient _client;

  static const String _base = '/incidentes-servicios';

  Future<IncidentListPage> listIncidents({
    int page = 1,
    int pageSize = 20,
  }) async {
    final json = await _client.getJson('$_base/incidentes?page=$page&page_size=$pageSize');
    return IncidentListPage.fromJson(json);
  }

  Future<IncidentListPage> getIncidents({int page = 1, int pageSize = 20}) =>
      listIncidents(page: page, pageSize: pageSize);

  Future<IncidentDetail> getIncidentById(int incidenteId) => getIncident(incidenteId);

  Future<IncidentSummary> createIncident(
    IncidentCreateDto dto, {
    required String idempotencyKey,
  }) async {
    final json = await _client.postJson(
      '$_base/incidentes',
      body: dto.toJson(),
      extraHeaders: <String, String>{'Idempotency-Key': idempotencyKey},
    );
    return IncidentSummary.fromJson(json);
  }

  Future<IncidentDetail> getIncident(int incidenteId) async {
    final json = await _client.getJson('$_base/incidentes/$incidenteId');
    return IncidentDetail.fromJson(json);
  }

  Future<IncidentDetail> cancelIncident(int incidenteId) async {
    final json = await _client.postJson('$_base/incidentes/$incidenteId/cancelar');
    return IncidentDetail.fromJson(json);
  }

  Future<void> deleteIncident(int incidenteId) async {
    await _client.delete('$_base/incidentes/$incidenteId');
  }

  /// Motor 1.5.5: candidatos persistidos (tras IA completada).
  Future<Map<String, dynamic>> getAssignmentCandidates(int incidenteId) async {
    return _client.getJson('$_base/incidentes/$incidenteId/asignacion/candidatos');
  }

  Future<IncidentDetail> markAsEnCamino(int incidenteId) async {
    final json = await _client.postJson(
      '$_base/incidentes/$incidenteId/en-camino',
      body: <String, dynamic>{},
    );
    return IncidentDetail.fromJson(json);
  }

  Future<IncidentDetail> markAsEnProceso(int incidenteId) async {
    final json = await _client.postJson(
      '$_base/incidentes/$incidenteId/en-proceso',
      body: <String, dynamic>{},
    );
    return IncidentDetail.fromJson(json);
  }

  Future<IncidentDetail> markAsFinalizado(int incidenteId, {Map<String, dynamic> body = const {}}) async {
    final json = await _client.postJson(
      '$_base/incidentes/$incidenteId/finalizar',
      body: Map<String, dynamic>.from(body),
    );
    return IncidentDetail.fromJson(json);
  }

  Future<Map<String, dynamic>> calificarIncidente(
    int incidenteId, {
    required int puntuacion,
    String? comentario,
  }) {
    final body = <String, dynamic>{
      'puntuacion': puntuacion,
      if (comentario != null && comentario.trim().isNotEmpty) 'comentario': comentario.trim(),
    };
    // Debug temporal solicitado.
    // ignore: avoid_print
    print('CALIFICACION URL: $_base/$incidenteId/calificacion');
    // ignore: avoid_print
    print('CALIFICACION BODY: $body');
    return _client.postJson(
      '$_base/$incidenteId/calificacion',
      body: body,
    );
  }

  /// `tipo`: `foto` | `audio` | `texto`
  Future<Map<String, dynamic>> addEvidenceText({
    required int incidenteId,
    required String contenidoTexto,
  }) async {
    return _client.postMultipart(
      '$_base/incidentes/$incidenteId/evidencias',
      fields: <String, String>{
        'tipo': 'texto',
        'contenido_texto': contenidoTexto,
      },
    );
  }

  Future<Map<String, dynamic>> addEvidenceFile({
    required int incidenteId,
    required String tipo,
    required List<int> bytes,
    required String filename,
    required String mimeType,
  }) async {
    var mt = mimeType.trim();
    if (mt == 'image/jpg' || mt == 'image/pjpeg') {
      mt = 'image/jpeg';
    }
    if (tipo == 'audio' && (mt == 'video/mp4' || mt == 'application/mp4')) {
      mt = 'audio/mp4';
    }
    final file = AuthorizedClient.fileField(
      fieldName: 'archivo',
      bytes: bytes,
      filename: filename,
      mimeType: mt,
    );
    return _client.postMultipart(
      '$_base/incidentes/$incidenteId/evidencias',
      fields: <String, String>{'tipo': tipo},
      files: <http.MultipartFile>[file],
    );
  }
}
