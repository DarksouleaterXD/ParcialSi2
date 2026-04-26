import 'dart:convert';
import 'dart:io';

import 'package:hive_flutter/hive_flutter.dart';

import 'pending_incident_draft.dart';

const String kPendingIncidentsHiveBox = 'pending_incidents_box';

/// Instancia compartida (shell, reporte, outbox).
final PendingIncidentsStore pendingIncidentsGlobal = PendingIncidentsStore();

/// Cola local de borradores CU-09 (Hive: id → JSON).
class PendingIncidentsStore {
  PendingIncidentsStore();

  Box<String> get _box => Hive.box<String>(kPendingIncidentsHiveBox);

  List<PendingIncidentDraft> listOrdered() {
    final out = <PendingIncidentDraft>[];
    for (final key in _box.keys) {
      final raw = _box.get(key);
      if (raw == null || raw.isEmpty) {
        continue;
      }
      try {
        final map = jsonDecode(raw) as Map<String, dynamic>;
        out.add(PendingIncidentDraft.fromJson(map));
      } catch (_) {}
    }
    out.sort((a, b) => b.savedAt.compareTo(a.savedAt));
    return out;
  }

  int get count => listOrdered().length;

  Future<void> put(PendingIncidentDraft draft) async {
    await _box.put(draft.localId, jsonEncode(draft.toJson()));
  }

  Future<void> delete(String localId) async {
    final raw = _box.get(localId);
    if (raw != null) {
      try {
        final map = jsonDecode(raw) as Map<String, dynamic>;
        final d = PendingIncidentDraft.fromJson(map);
        final dir = Directory(d.storageDir);
        if (dir.existsSync()) {
          await dir.delete(recursive: true);
        }
      } catch (_) {}
    }
    await _box.delete(localId);
  }
}
