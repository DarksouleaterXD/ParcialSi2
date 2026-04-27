import 'pending_photo_info.dart';

/// Borrador persistido para reintentar `POST /incidentes` y evidencias sin duplicar (misma `Idempotency-Key`).
class PendingIncidentDraft {
  const PendingIncidentDraft({
    required this.localId,
    required this.savedAt,
    required this.incidentIdempotencyKey,
    required this.storageDir,
    required this.vehiculoId,
    required this.vehiculoLabel,
    required this.latitud,
    required this.longitud,
    this.descripcionTexto,
    this.extraTextEvidence,
    this.photos = const [],
    this.audioAbsPath,
    this.audioMimeType,
    this.audioFilename,
    this.serverIncidentId,
    this.textEvidenceDone = false,
    this.audioEvidenceDone = false,
    this.lastErrorMessage,
  });

  final String localId;
  final DateTime savedAt;
  final String incidentIdempotencyKey;
  final String storageDir;
  final int vehiculoId;
  final String vehiculoLabel;
  final double latitud;
  final double longitud;
  final String? descripcionTexto;
  final String? extraTextEvidence;
  final List<PendingPhotoInfo> photos;
  final String? audioAbsPath;
  final String? audioMimeType;
  final String? audioFilename;

  final int? serverIncidentId;
  final bool textEvidenceDone;
  final bool audioEvidenceDone;
  final String? lastErrorMessage;

  bool get needsCreate => serverIncidentId == null;

  bool get needsTextEvidence =>
      extraTextEvidence != null && extraTextEvidence!.trim().isNotEmpty && !textEvidenceDone;

  bool get needsAnyPhotoUpload => photos.any((p) => p.isPendingUpload);

  bool get needsAudioEvidence =>
      audioAbsPath != null &&
      audioAbsPath!.isNotEmpty &&
      audioMimeType != null &&
      audioFilename != null &&
      !audioEvidenceDone;

  bool get isComplete =>
      !needsCreate &&
      (!needsTextEvidence) &&
      !needsAnyPhotoUpload &&
      (!needsAudioEvidence);

  PendingIncidentDraft copyWith({
    int? serverIncidentId,
    bool? textEvidenceDone,
    bool? audioEvidenceDone,
    String? lastErrorMessage,
    bool clearLastError = false,
    List<PendingPhotoInfo>? photos,
  }) {
    return PendingIncidentDraft(
      localId: localId,
      savedAt: savedAt,
      incidentIdempotencyKey: incidentIdempotencyKey,
      storageDir: storageDir,
      vehiculoId: vehiculoId,
      vehiculoLabel: vehiculoLabel,
      latitud: latitud,
      longitud: longitud,
      descripcionTexto: descripcionTexto,
      extraTextEvidence: extraTextEvidence,
      photos: photos ?? this.photos,
      audioAbsPath: audioAbsPath,
      audioMimeType: audioMimeType,
      audioFilename: audioFilename,
      serverIncidentId: serverIncidentId ?? this.serverIncidentId,
      textEvidenceDone: textEvidenceDone ?? this.textEvidenceDone,
      audioEvidenceDone: audioEvidenceDone ?? this.audioEvidenceDone,
      lastErrorMessage: clearLastError ? null : (lastErrorMessage ?? this.lastErrorMessage),
    );
  }

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'localId': localId,
      'savedAt': savedAt.toIso8601String(),
      'incidentIdempotencyKey': incidentIdempotencyKey,
      'storageDir': storageDir,
      'vehiculoId': vehiculoId,
      'vehiculoLabel': vehiculoLabel,
      'latitud': latitud,
      'longitud': longitud,
      'descripcionTexto': descripcionTexto,
      'extraTextEvidence': extraTextEvidence,
      'photos': photos.map((e) => e.toJson()).toList(),
      'audioAbsPath': audioAbsPath,
      'audioMimeType': audioMimeType,
      'audioFilename': audioFilename,
      'serverIncidentId': serverIncidentId,
      'textEvidenceDone': textEvidenceDone,
      'audioEvidenceDone': audioEvidenceDone,
      'lastErrorMessage': lastErrorMessage,
    };
  }

  factory PendingIncidentDraft.fromJson(Map<String, dynamic> j) {
    var photos = <PendingPhotoInfo>[];
    final rawPhotos = j['photos'];
    if (rawPhotos is List && rawPhotos.isNotEmpty) {
      for (final e in rawPhotos) {
        if (e is Map<String, dynamic>) {
          photos.add(PendingPhotoInfo.fromJson(e));
        } else if (e is Map) {
          photos.add(PendingPhotoInfo.fromJson(Map<String, dynamic>.from(e)));
        }
      }
    }
    if (photos.isEmpty) {
      final legacy = j['photoAbsPath'] as String?;
      if (legacy != null && legacy.isNotEmpty) {
        photos = [
          PendingPhotoInfo(
            absPath: legacy,
            mime: j['photoMimeType'] as String? ?? 'image/jpeg',
            filename: j['photoFilename'] as String? ?? 'foto.jpg',
            evidenceDone: j['photoEvidenceDone'] as bool? ?? false,
          ),
        ];
      }
    }
    return PendingIncidentDraft(
      localId: j['localId'] as String? ?? '',
      savedAt: DateTime.tryParse(j['savedAt'] as String? ?? '') ?? DateTime.now(),
      incidentIdempotencyKey: j['incidentIdempotencyKey'] as String? ?? '',
      storageDir: j['storageDir'] as String? ?? '',
      vehiculoId: (j['vehiculoId'] as num?)?.toInt() ?? 0,
      vehiculoLabel: j['vehiculoLabel'] as String? ?? '',
      latitud: (j['latitud'] as num?)?.toDouble() ?? 0,
      longitud: (j['longitud'] as num?)?.toDouble() ?? 0,
      descripcionTexto: j['descripcionTexto'] as String?,
      extraTextEvidence: j['extraTextEvidence'] as String?,
      photos: photos,
      audioAbsPath: j['audioAbsPath'] as String?,
      audioMimeType: j['audioMimeType'] as String?,
      audioFilename: j['audioFilename'] as String?,
      serverIncidentId: (j['serverIncidentId'] as num?)?.toInt(),
      textEvidenceDone: j['textEvidenceDone'] as bool? ?? false,
      audioEvidenceDone: j['audioEvidenceDone'] as bool? ?? false,
      lastErrorMessage: j['lastErrorMessage'] as String?,
    );
  }
}
