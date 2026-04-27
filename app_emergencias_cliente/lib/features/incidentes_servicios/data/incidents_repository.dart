import '../../../core/authorized_client.dart';
import '../domain/incident.dart';
import 'incident_dto.dart';
import 'incidents_api.dart';

/// Un archivo de imagen a enviar como evidencia tipo `foto`.
class ReportPhotoItem {
  const ReportPhotoItem({required this.bytes, required this.mime, required this.filename});

  final List<int> bytes;
  final String mime;
  final String filename;
}

/// Payload armado en el wizard antes de enviar.
class ReportSubmitPayload {
  ReportSubmitPayload({
    required this.vehiculoId,
    required this.latitud,
    required this.longitud,
    this.descripcionTexto,
    this.photos = const [],
    this.audioBytes,
    this.audioMimeType,
    this.audioFilename,
    this.extraTextEvidence,
  });

  final int vehiculoId;
  final double latitud;
  final double longitud;
  final String? descripcionTexto;
  final List<ReportPhotoItem> photos;
  final List<int>? audioBytes;
  final String? audioMimeType;
  final String? audioFilename;
  final String? extraTextEvidence;

  static const int maxDescriptionChars = 1000;
  static const int maxExtraTextEvidenceChars = 10000;
  static const int maxPhotoBytes = 5 * 1024 * 1024;
  static const int maxAudioBytes = 15 * 1024 * 1024;
  static const int maxPhotosPerReport = 8;

  static const Set<String> allowedPhotoMimes = {
    'image/jpeg',
    'image/jpg',
    'image/pjpeg',
    'image/png',
    'image/webp',
  };
  static const Set<String> allowedAudioMimes = {
    'audio/mpeg',
    'audio/mp4',
    'audio/webm',
    'audio/wav',
    'audio/x-wav',
  };

  String? validateClientSide() {
    if (descripcionTexto != null && descripcionTexto!.length > maxDescriptionChars) {
      return 'La descripción no puede superar $maxDescriptionChars caracteres.';
    }
    if (extraTextEvidence != null && extraTextEvidence!.length > maxExtraTextEvidenceChars) {
      return 'El texto de evidencia es demasiado largo.';
    }
    if (photos.length > maxPhotosPerReport) {
      return 'Podés adjuntar como máximo $maxPhotosPerReport fotos en un mismo reporte.';
    }
    for (var i = 0; i < photos.length; i++) {
      final p = photos[i];
      if (!allowedPhotoMimes.contains(p.mime)) {
        return 'Foto ${i + 1}: formato no permitido (usá JPEG, PNG o WEBP).';
      }
      if (p.bytes.length > maxPhotoBytes) {
        return 'Foto ${i + 1}: supera 5 MB.';
      }
    }
    if (audioBytes != null && audioBytes!.isNotEmpty) {
      if (audioMimeType == null || !allowedAudioMimes.contains(audioMimeType)) {
        return 'Formato de audio no permitido.';
      }
      if (audioBytes!.length > maxAudioBytes) {
        return 'El audio supera el tamaño máximo permitido (15 MB).';
      }
    }
    return null;
  }
}

/// Resultado de envío: detalle final y advertencias de evidencias fallidas.
class SubmitIncidentOutcome {
  const SubmitIncidentOutcome({
    required this.detail,
    this.warnings = const [],
  });

  final IncidentDetail detail;
  final List<String> warnings;
}

class IncidentsRepository {
  IncidentsRepository(this._api);

  final IncidentsApi _api;

  IncidentsApi get incidentsApi => _api;

  Future<IncidentDetail> cancelIncident(int id) => _api.cancelIncident(id);
  Future<void> deleteIncident(int id) => _api.deleteIncident(id);

  Future<Map<String, dynamic>> getAssignmentCandidates(int id) => _api.getAssignmentCandidates(id);

  Future<IncidentDetail> markAsEnCamino(int id) => _api.markAsEnCamino(id);

  Future<IncidentDetail> markAsEnProceso(int id) => _api.markAsEnProceso(id);

  Future<IncidentDetail> markAsFinalizado(int id, {String? diagnosticoFinal, double? precioBase}) {
    final body = <String, dynamic>{};
    if (diagnosticoFinal != null && diagnosticoFinal.trim().isNotEmpty) {
      body['diagnostico_final'] = diagnosticoFinal.trim();
    }
    if (precioBase != null) {
      body['precio_base'] = precioBase;
    }
    return _api.markAsFinalizado(id, body: body);
  }

  Future<void> calificarIncidente(String id, int puntuacion, String comentario) async {
    final parsedId = int.tryParse(id);
    if (parsedId == null || parsedId < 1) {
      throw ApiClientException(statusCode: 422, message: 'ID de incidente inválido.');
    }
    await _api.calificarIncidente(
      parsedId,
      puntuacion: puntuacion,
      comentario: comentario.trim(),
    );
  }

  Future<IncidentSummary> createIncidentOnly(
    IncidentCreateDto dto, {
    required String idempotencyKey,
  }) {
    return _api.createIncident(dto, idempotencyKey: idempotencyKey);
  }

  Future<SubmitIncidentOutcome> submitReport(
    ReportSubmitPayload payload, {
    required String incidentIdempotencyKey,
  }) async {
    final clientErr = payload.validateClientSide();
    if (clientErr != null) {
      throw ApiClientException(statusCode: 422, message: clientErr);
    }

    final created = await _api.createIncident(
      IncidentCreateDto(
        vehiculoId: payload.vehiculoId,
        latitud: payload.latitud,
        longitud: payload.longitud,
        descripcionTexto: payload.descripcionTexto,
      ),
      idempotencyKey: incidentIdempotencyKey,
    );

    final warnings = <String>[];

    Future<void> runEvidence(String label, Future<void> Function() action) async {
      try {
        await action();
      } on ApiClientException catch (e) {
        warnings.add('$label: ${e.message}');
      } catch (e) {
        warnings.add('$label: $e');
      }
    }

    if (payload.extraTextEvidence != null && payload.extraTextEvidence!.trim().isNotEmpty) {
      await runEvidence(
        'Nota de texto',
        () async {
          await _api.addEvidenceText(
            incidenteId: created.id,
            contenidoTexto: payload.extraTextEvidence!.trim(),
          );
        },
      );
    }

    for (var i = 0; i < payload.photos.length; i++) {
      final p = payload.photos[i];
      final n = i + 1;
      if (p.bytes.isEmpty) {
        continue;
      }
      await runEvidence(
        'Foto $n',
        () async {
          await _api.addEvidenceFile(
            incidenteId: created.id,
            tipo: 'foto',
            bytes: p.bytes,
            filename: p.filename,
            mimeType: p.mime,
          );
        },
      );
    }

    if (payload.audioBytes != null &&
        payload.audioMimeType != null &&
        payload.audioFilename != null &&
        payload.audioBytes!.isNotEmpty) {
      await runEvidence(
        'Audio',
        () async {
          await _api.addEvidenceFile(
            incidenteId: created.id,
            tipo: 'audio',
            bytes: payload.audioBytes!,
            filename: payload.audioFilename!,
            mimeType: payload.audioMimeType!,
          );
        },
      );
    }

    final detail = await _api.getIncidentById(created.id);
    return SubmitIncidentOutcome(detail: detail, warnings: warnings);
  }
}
