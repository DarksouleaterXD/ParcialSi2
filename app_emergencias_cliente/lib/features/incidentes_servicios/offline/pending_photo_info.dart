class PendingPhotoInfo {
  const PendingPhotoInfo({
    required this.absPath,
    required this.mime,
    required this.filename,
    this.evidenceDone = false,
  });

  final String absPath;
  final String mime;
  final String filename;
  final bool evidenceDone;

  bool get isPendingUpload => absPath.isNotEmpty && mime.isNotEmpty && filename.isNotEmpty && !evidenceDone;

  PendingPhotoInfo copyWith({bool? evidenceDone}) {
    return PendingPhotoInfo(
      absPath: absPath,
      mime: mime,
      filename: filename,
      evidenceDone: evidenceDone ?? this.evidenceDone,
    );
  }

  Map<String, dynamic> toJson() => {
        'absPath': absPath,
        'mime': mime,
        'filename': filename,
        'evidenceDone': evidenceDone,
      };

  factory PendingPhotoInfo.fromJson(Map<String, dynamic> m) {
    return PendingPhotoInfo(
      absPath: m['absPath'] as String? ?? '',
      mime: m['mime'] as String? ?? '',
      filename: m['filename'] as String? ?? '',
      evidenceDone: m['evidenceDone'] as bool? ?? false,
    );
  }
}
