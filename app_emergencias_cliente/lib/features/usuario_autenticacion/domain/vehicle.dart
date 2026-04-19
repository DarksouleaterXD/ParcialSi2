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
      placa: json['placa'] as String? ?? '',
      marca: json['marca'] as String? ?? '',
      modelo: json['modelo'] as String? ?? '',
      anio: anio,
      color: json['color'] as String?,
      tipoSeguro: json['tipo_seguro'] as String?,
      fotoFrontal: json['foto_frontal'] as String?,
      propietarioNombre: json['propietario_nombre'] as String?,
      propietarioEmail: json['propietario_email'] as String?,
    );
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
