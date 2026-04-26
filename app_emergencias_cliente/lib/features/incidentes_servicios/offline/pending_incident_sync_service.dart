import 'dart:io';

import '../../../core/auth_storage.dart';
import '../../../core/authorized_client.dart';
import '../data/incident_dto.dart';
import '../data/incidents_api.dart';
import '../data/incidents_repository.dart';
import 'pending_incident_draft.dart';
import 'pending_incidents_store.dart';

/// Sincroniza borradores: misma `Idempotency-Key` en creación; evidencias idempotentes por huella en servidor.
class PendingIncidentSyncService {
  PendingIncidentSyncService({
    required AuthStorage storage,
    required PendingIncidentsStore store,
  })  : _storage = storage,
        _store = store;

  final AuthStorage _storage;
  final PendingIncidentsStore _store;

  IncidentsRepository _repo() => IncidentsRepository(
        IncidentsApi(AuthorizedClient(storage: _storage)),
      );

  /// Cantidad de borradores completamente enviados y eliminados de la cola.
  Future<int> syncAll() async {
    final token = await _storage.readToken();
    if (token == null || token.isEmpty) {
      return 0;
    }

    var completed = 0;
    final drafts = _store.listOrdered();
    final repo = _repo();

    for (final draft in drafts) {
      final ok = await _syncOne(repo, draft);
      if (ok) {
        completed++;
      }
    }
    return completed;
  }

  Future<bool> syncDraftByLocalId(String localId) async {
    final token = await _storage.readToken();
    if (token == null || token.isEmpty) {
      return false;
    }
    final all = _store.listOrdered();
    PendingIncidentDraft? match;
    for (final d in all) {
      if (d.localId == localId) {
        match = d;
        break;
      }
    }
    if (match == null) {
      return false;
    }
    return _syncOne(_repo(), match);
  }

  Future<bool> _syncOne(IncidentsRepository repo, PendingIncidentDraft initial) async {
    var w = initial;
    final api = repo.incidentsApi;
    try {
      if (w.needsCreate) {
        final created = await repo.createIncidentOnly(
          IncidentCreateDto(
            vehiculoId: w.vehiculoId,
            latitud: w.latitud,
            longitud: w.longitud,
            descripcionTexto: w.descripcionTexto,
          ),
          idempotencyKey: w.incidentIdempotencyKey,
        );
        w = w.copyWith(serverIncidentId: created.id, clearLastError: true);
        await _store.put(w);
      }

      final incidenteId = w.serverIncidentId;
      if (incidenteId == null) {
        return false;
      }

      if (w.needsTextEvidence) {
        await api.addEvidenceText(
          incidenteId: incidenteId,
          contenidoTexto: w.extraTextEvidence!.trim(),
        );
        w = w.copyWith(textEvidenceDone: true, clearLastError: true);
        await _store.put(w);
      }

      if (w.needsPhotoEvidence) {
        final file = File(w.photoAbsPath!);
        if (!await file.exists()) {
          await _store.put(
            w.copyWith(
              lastErrorMessage:
                  'No se encontró el archivo de foto guardado. Podés descartar el borrador.',
            ),
          );
          return false;
        }
        final bytes = await file.readAsBytes();
        if (bytes.length > ReportSubmitPayload.maxPhotoBytes) {
          await _store.put(
            w.copyWith(lastErrorMessage: 'La foto guardada supera el tamaño máximo permitido.'),
          );
          return false;
        }
        await api.addEvidenceFile(
          incidenteId: incidenteId,
          tipo: 'foto',
          bytes: bytes,
          filename: w.photoFilename!,
          mimeType: w.photoMimeType!,
        );
        w = w.copyWith(photoEvidenceDone: true, clearLastError: true);
        await _store.put(w);
      }

      if (w.needsAudioEvidence) {
        final file = File(w.audioAbsPath!);
        if (!await file.exists()) {
          await _store.put(
            w.copyWith(
              lastErrorMessage:
                  'No se encontró el archivo de audio guardado. Podés descartar el borrador.',
            ),
          );
          return false;
        }
        final bytes = await file.readAsBytes();
        if (bytes.length > ReportSubmitPayload.maxAudioBytes) {
          await _store.put(
            w.copyWith(lastErrorMessage: 'El audio guardado supera el tamaño máximo permitido.'),
          );
          return false;
        }
        await api.addEvidenceFile(
          incidenteId: incidenteId,
          tipo: 'audio',
          bytes: bytes,
          filename: w.audioFilename!,
          mimeType: w.audioMimeType!,
        );
        w = w.copyWith(audioEvidenceDone: true, clearLastError: true);
        await _store.put(w);
      }

      if (w.isComplete) {
        await _store.delete(w.localId);
        return true;
      }
    } on SessionExpiredException {
      await _store.put(
        w.copyWith(
          lastErrorMessage: 'Sesión expirada. Iniciá sesión de nuevo y tocá «Reintentar ahora».',
        ),
      );
    } on ApiClientException catch (e) {
      await _store.put(w.copyWith(lastErrorMessage: e.message));
    } catch (e) {
      await _store.put(w.copyWith(lastErrorMessage: 'Error: $e'));
    }
    return false;
  }
}
