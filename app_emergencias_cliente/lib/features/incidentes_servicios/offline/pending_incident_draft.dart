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
    this.photoAbsPath,
    this.photoMimeType,
    this.photoFilename,
    this.audioAbsPath,
    this.audioMimeType,
    this.audioFilename,
    this.serverIncidentId,
    this.textEvidenceDone = false,
    this.photoEvidenceDone = false,
    this.audioEvidenceDone = false,
    this.lastErrorMessage,
  });

  final String localId;
  final DateTime savedAt;
  final String incidentIdempotencyKey;
  /// Carpeta dedicada (`…/pending_incidents/{localId}`) para borrar al descartar o completar.
  final String storageDir;
  final int vehiculoId;
  final String vehiculoLabel;
  final double latitud;
  final double longitud;
  final String? descripcionTexto;
  final String? extraTextEvidence;
  final String? photoAbsPath;
  final String? photoMimeType;
  final String? photoFilename;
  final String? audioAbsPath;
  final String? audioMimeType;
  final String? audioFilename;

  final int? serverIncidentId;
  final bool textEvidenceDone;
  final bool photoEvidenceDone;
  final bool audioEvidenceDone;
  final String? lastErrorMessage;

  bool get needsCreate => serverIncidentId == null;

  bool get needsTextEvidence =>
      extraTextEvidence != null && extraTextEvidence!.trim().isNotEmpty && !textEvidenceDone;

  bool get needsPhotoEvidence =>
      photoAbsPath != null &&
      photoAbsPath!.isNotEmpty &&
      photoMimeType != null &&
      photoFilename != null &&
      !photoEvidenceDone;

  bool get needsAudioEvidence =>
      audioAbsPath != null &&
      audioAbsPath!.isNotEmpty &&
      audioMimeType != null &&
      audioFilename != null &&
      !audioEvidenceDone;

  bool get isComplete =>
      !needsCreate &&
      (!needsTextEvidence) &&
      (!needsPhotoEvidence) &&
      (!needsAudioEvidence);

  PendingIncidentDraft copyWith({
    int? serverIncidentId,
    bool? textEvidenceDone,
    bool? photoEvidenceDone,
    bool? audioEvidenceDone,
    String? lastErrorMessage,
    bool clearLastError = false,
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
      photoAbsPath: photoAbsPath,
      photoMimeType: photoMimeType,
      photoFilename: photoFilename,
      audioAbsPath: audioAbsPath,
      audioMimeType: audioMimeType,
      audioFilename: audioFilename,
      serverIncidentId: serverIncidentId ?? this.serverIncidentId,
      textEvidenceDone: textEvidenceDone ?? this.textEvidenceDone,
      photoEvidenceDone: photoEvidenceDone ?? this.photoEvidenceDone,
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
      'photoAbsPath': photoAbsPath,
      'photoMimeType': photoMimeType,
      'photoFilename': photoFilename,
      'audioAbsPath': audioAbsPath,
      'audioMimeType': audioMimeType,
      'audioFilename': audioFilename,
      'serverIncidentId': serverIncidentId,
      'textEvidenceDone': textEvidenceDone,
      'photoEvidenceDone': photoEvidenceDone,
      'audioEvidenceDone': audioEvidenceDone,
      'lastErrorMessage': lastErrorMessage,
    };
  }

  factory PendingIncidentDraft.fromJson(Map<String, dynamic> j) {
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
      photoAbsPath: j['photoAbsPath'] as String?,
      photoMimeType: j['photoMimeType'] as String?,
      photoFilename: j['photoFilename'] as String?,
      audioAbsPath: j['audioAbsPath'] as String?,
      audioMimeType: j['audioMimeType'] as String?,
      audioFilename: j['audioFilename'] as String?,
      serverIncidentId: (j['serverIncidentId'] as num?)?.toInt(),
      textEvidenceDone: j['textEvidenceDone'] as bool? ?? false,
      photoEvidenceDone: j['photoEvidenceDone'] as bool? ?? false,
      audioEvidenceDone: j['audioEvidenceDone'] as bool? ?? false,
      lastErrorMessage: j['lastErrorMessage'] as String?,
    );
  }
}
