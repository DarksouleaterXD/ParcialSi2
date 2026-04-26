import 'evidence.dart';

/// Resumen / creación de incidente.
class IncidentSummary {
  const IncidentSummary({
    required this.id,
    required this.clienteId,
    required this.vehiculoId,
    required this.estado,
    required this.latitud,
    required this.longitud,
    this.descripcionTexto,
    this.createdAt,
    required this.evidenciasCount,
    this.tecnicoId,
  });

  final int id;
  final int clienteId;
  final int vehiculoId;
  final String estado;
  final double latitud;
  final double longitud;
  final String? descripcionTexto;
  final DateTime? createdAt;
  final int evidenciasCount;
  /// Usuario técnico asignado; null en bolsa / pendiente.
  final int? tecnicoId;

  factory IncidentSummary.fromJson(Map<String, dynamic> json) {
    return IncidentSummary(
      id: (json['id'] as num?)?.toInt() ?? 0,
      clienteId: (json['cliente_id'] as num?)?.toInt() ?? 0,
      vehiculoId: (json['vehiculo_id'] as num?)?.toInt() ?? 0,
      estado: json['estado'] as String? ?? '',
      latitud: (json['latitud'] as num?)?.toDouble() ?? 0,
      longitud: (json['longitud'] as num?)?.toDouble() ?? 0,
      descripcionTexto: json['descripcion_texto'] as String?,
      createdAt: _parseDate(json['created_at']),
      evidenciasCount: (json['evidencias_count'] as num?)?.toInt() ?? 0,
      tecnicoId: (json['tecnico_id'] as num?)?.toInt(),
    );
  }

  static DateTime? _parseDate(Object? v) {
    if (v is String && v.isNotEmpty) {
      return DateTime.tryParse(v);
    }
    return null;
  }
}

/// Detalle con evidencias (`GET /incidentes/{id}`).
class IncidentDetail extends IncidentSummary {
  const IncidentDetail({
    required super.id,
    required super.clienteId,
    required super.vehiculoId,
    required super.estado,
    required super.latitud,
    required super.longitud,
    super.descripcionTexto,
    super.createdAt,
    required super.evidenciasCount,
    super.tecnicoId,
    required this.evidencias,
    this.categoriaIa,
    this.prioridadIa,
    this.resumenIa,
    this.confianzaIa,
    this.aiStatus,
    this.aiProvider,
    this.aiModel,
    this.promptVersion,
    this.aiResult,
  });

  final List<EvidenceItem> evidencias;
  final String? categoriaIa;
  final String? prioridadIa;
  final String? resumenIa;
  final double? confianzaIa;
  final String? aiStatus;
  final String? aiProvider;
  final String? aiModel;
  final String? promptVersion;
  final Map<String, dynamic>? aiResult;

  static Map<String, dynamic>? _objectMap(Object? v) {
    if (v is Map<String, dynamic>) {
      return v;
    }
    if (v is Map) {
      return v.map((k, val) => MapEntry(k.toString(), val));
    }
    return null;
  }

  factory IncidentDetail.fromJson(Map<String, dynamic> json) {
    final raw = json['evidencias'];
    final list = <EvidenceItem>[];
    if (raw is List) {
      for (final e in raw) {
        if (e is Map<String, dynamic>) {
          list.add(EvidenceItem.fromJson(e));
        }
      }
    }
    return IncidentDetail(
      id: (json['id'] as num?)?.toInt() ?? 0,
      clienteId: (json['cliente_id'] as num?)?.toInt() ?? 0,
      vehiculoId: (json['vehiculo_id'] as num?)?.toInt() ?? 0,
      estado: json['estado'] as String? ?? '',
      latitud: (json['latitud'] as num?)?.toDouble() ?? 0,
      longitud: (json['longitud'] as num?)?.toDouble() ?? 0,
      descripcionTexto: json['descripcion_texto'] as String?,
      createdAt: IncidentSummary._parseDate(json['created_at']),
      evidenciasCount: (json['evidencias_count'] as num?)?.toInt() ?? list.length,
      tecnicoId: (json['tecnico_id'] as num?)?.toInt(),
      evidencias: list,
      categoriaIa: json['categoria_ia'] as String?,
      prioridadIa: json['prioridad_ia'] as String?,
      resumenIa: json['resumen_ia'] as String?,
      confianzaIa: (json['confianza_ia'] as num?)?.toDouble(),
      aiStatus: json['ai_status'] as String?,
      aiProvider: json['ai_provider'] as String?,
      aiModel: json['ai_model'] as String?,
      promptVersion: json['prompt_version'] as String?,
      aiResult: _objectMap(json['ai_result']),
    );
  }
}

/// Ítem de `GET /incidentes-servicios/incidentes` (listado paginado).
class IncidentListItem {
  const IncidentListItem({
    required this.id,
    required this.estado,
    required this.createdAt,
    required this.clienteNombre,
    required this.clienteEmail,
    required this.vehiculoPlaca,
    required this.vehiculoMarcaModelo,
    required this.evidenciasCount,
    this.tecnicoId,
  });

  final int id;
  final String estado;
  final DateTime? createdAt;
  final String clienteNombre;
  final String clienteEmail;
  final String vehiculoPlaca;
  final String vehiculoMarcaModelo;
  final int evidenciasCount;
  final int? tecnicoId;

  static Map<String, dynamic>? _asStrKeyMap(Object? v) {
    if (v is Map<String, dynamic>) {
      return v;
    }
    if (v is Map) {
      return v.map((k, val) => MapEntry(k.toString(), val));
    }
    return null;
  }

  factory IncidentListItem.fromJson(Map<String, dynamic> json) {
    final cli = _asStrKeyMap(json['cliente']) ?? {};
    final veh = _asStrKeyMap(json['vehiculo']) ?? {};
    return IncidentListItem(
      id: (json['id'] as num?)?.toInt() ?? 0,
      estado: json['estado'] as String? ?? '',
      createdAt: IncidentSummary._parseDate(json['created_at']),
      clienteNombre: (cli['nombre'] as String?)?.trim() ?? '',
      clienteEmail: (cli['email'] as String?)?.trim() ?? '',
      vehiculoPlaca: (veh['placa'] as String?)?.trim() ?? '',
      vehiculoMarcaModelo: (veh['marca_modelo'] as String?)?.trim() ?? '',
      evidenciasCount: (json['evidencias_count'] as num?)?.toInt() ?? 0,
      tecnicoId: (json['tecnico_id'] as num?)?.toInt(),
    );
  }
}

class IncidentListPage {
  const IncidentListPage({
    required this.items,
    required this.page,
    required this.pageSize,
    required this.total,
  });

  final List<IncidentListItem> items;
  final int page;
  final int pageSize;
  final int total;

  factory IncidentListPage.fromJson(Map<String, dynamic> json) {
    final raw = json['items'];
    final items = <IncidentListItem>[];
    if (raw is List) {
      for (final e in raw) {
        final m = IncidentListItem._asStrKeyMap(e);
        if (m != null) {
          items.add(IncidentListItem.fromJson(m));
        }
      }
    }
    return IncidentListPage(
      items: items,
      page: (json['page'] as num?)?.toInt() ?? 1,
      pageSize: (json['page_size'] as num?)?.toInt() ?? 20,
      total: (json['total'] as num?)?.toInt() ?? 0,
    );
  }
}
