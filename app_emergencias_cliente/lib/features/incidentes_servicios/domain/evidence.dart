/// Evidencia adjunta a un incidente (respuesta API).
class EvidenceItem {
  const EvidenceItem({
    required this.id,
    required this.incidenteId,
    required this.tipo,
    required this.urlOrPath,
    this.createdAt,
  });

  final int id;
  final int incidenteId;
  final String tipo;
  final String urlOrPath;
  final DateTime? createdAt;

  factory EvidenceItem.fromJson(Map<String, dynamic> json) {
    return EvidenceItem(
      id: (json['id'] as num?)?.toInt() ?? 0,
      incidenteId: (json['incidente_id'] as num?)?.toInt() ?? 0,
      tipo: json['tipo'] as String? ?? '',
      urlOrPath: json['url_or_path'] as String? ?? '',
      createdAt: _parseDate(json['created_at']),
    );
  }

  static DateTime? _parseDate(Object? v) {
    if (v is String && v.isNotEmpty) {
      return DateTime.tryParse(v);
    }
    return null;
  }
}
