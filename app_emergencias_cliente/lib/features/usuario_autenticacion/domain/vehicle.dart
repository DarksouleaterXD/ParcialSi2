/// Mirrors backend [VehiculoItem].
class Vehicle {
  const Vehicle({
    required this.id,
    required this.idUsuario,
    required this.placa,
    required this.marca,
    required this.modelo,
    required this.anio,
    this.color,
    this.tipoSeguro,
    this.fotoFrontal,
    this.propietarioNombre,
    this.propietarioEmail,
  });

  final int id;
  final int idUsuario;
  final String placa;
  final String marca;
  final String modelo;
  final int anio;
  final String? color;
  final String? tipoSeguro;
  final String? fotoFrontal;
  final String? propietarioNombre;
  final String? propietarioEmail;

  factory Vehicle.fromJson(Map<String, dynamic> json) {
    final anioRaw = json['anio'];
    final anio = anioRaw is int ? anioRaw : (anioRaw is num ? anioRaw.toInt() : 0);
    return Vehicle(
      id: (json['id'] as num?)?.toInt() ?? 0,
      idUsuario: (json['id_usuario'] as num?)?.toInt() ?? 0,
      placa: _jsonReqStr(json['placa']),
      marca: _jsonReqStr(json['marca']),
      modelo: _jsonReqStr(json['modelo']),
      anio: anio,
      color: _jsonOptStr(json['color']),
      tipoSeguro: _jsonOptStr(json['tipo_seguro']),
      fotoFrontal: _jsonOptStr(json['foto_frontal']),
      propietarioNombre: _jsonOptStr(json['propietario_nombre']),
      propietarioEmail: _jsonOptStr(json['propietario_email']),
    );
  }

  static String _jsonReqStr(Object? v) {
    if (v == null) {
      return '';
    }
    if (v is String) {
      return v;
    }
    return v.toString();
  }

  static String? _jsonOptStr(Object? v) {
    if (v == null) {
      return null;
    }
    if (v is String) {
      return v;
    }
    return v.toString();
  }
}

class VehicleListPage {
  const VehicleListPage({
    required this.items,
    required this.total,
    required this.page,
    required this.pageSize,
  });

  final List<Vehicle> items;
  final int total;
  final int page;
  final int pageSize;

  factory VehicleListPage.fromJson(Map<String, dynamic> json) {
    final raw = json['items'];
    final items = <Vehicle>[];
    if (raw is List) {
      for (final e in raw) {
        if (e is Map<String, dynamic>) {
          items.add(Vehicle.fromJson(e));
        }
      }
    }
    return VehicleListPage(
      items: items,
      total: (json['total'] as num?)?.toInt() ?? 0,
      page: (json['page'] as num?)?.toInt() ?? 1,
      pageSize: (json['page_size'] as num?)?.toInt() ?? 20,
    );
  }
}
