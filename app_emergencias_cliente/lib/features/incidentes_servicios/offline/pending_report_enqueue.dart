import 'dart:io';

import 'package:path_provider/path_provider.dart';
import 'package:uuid/uuid.dart';

import '../data/incidents_repository.dart';
import 'pending_incident_draft.dart';
import 'pending_photo_info.dart';
import 'pending_incidents_store.dart';

/// Copia adjuntos al almacenamiento de la app y persiste el borrador en Hive.
Future<PendingIncidentDraft> enqueuePendingReport({
  required PendingIncidentsStore store,
  required ReportSubmitPayload payload,
  required String incidentIdempotencyKey,
  required String vehiculoLabel,
}) async {
  final localId = const Uuid().v4();
  final root = await getApplicationDocumentsDirectory();
  final dir = Directory('${root.path}/pending_incidents/$localId');
  await dir.create(recursive: true);

  final photoEntries = <PendingPhotoInfo>[];
  for (var i = 0; i < payload.photos.length; i++) {
    final p = payload.photos[i];
    if (p.bytes.isEmpty) {
      continue;
    }
    final path = '${dir.path}/photo_$i.bin';
    await File(path).writeAsBytes(p.bytes, flush: true);
    photoEntries.add(
      PendingPhotoInfo(absPath: path, mime: p.mime, filename: p.filename, evidenceDone: false),
    );
  }

  String? audioPath;
  if (payload.audioBytes != null && payload.audioBytes!.isNotEmpty) {
    audioPath = '${dir.path}/audio.bin';
    await File(audioPath).writeAsBytes(payload.audioBytes!, flush: true);
  }

  final draft = PendingIncidentDraft(
    localId: localId,
    savedAt: DateTime.now(),
    incidentIdempotencyKey: incidentIdempotencyKey,
    storageDir: dir.path,
    vehiculoId: payload.vehiculoId,
    vehiculoLabel: vehiculoLabel,
    latitud: payload.latitud,
    longitud: payload.longitud,
    descripcionTexto: payload.descripcionTexto,
    extraTextEvidence: payload.extraTextEvidence,
    photos: photoEntries,
    audioAbsPath: audioPath,
    audioMimeType: payload.audioMimeType,
    audioFilename: payload.audioFilename,
    lastErrorMessage: 'Pendiente de envío',
  );
  await store.put(draft);
  return draft;
}
