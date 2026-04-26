/// Cuerpo JSON `POST /incidentes-servicios/incidentes`.
class IncidentCreateDto {
  const IncidentCreateDto({
    required this.vehiculoId,
    required this.latitud,
    required this.longitud,
    this.descripcionTexto,
  });

  final int vehiculoId;
  final double latitud;
  final double longitud;
  final String? descripcionTexto;

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'vehiculo_id': vehiculoId,
      'latitud': latitud,
      'longitud': longitud,
      if (descripcionTexto != null && descripcionTexto!.trim().isNotEmpty) 'descripcion_texto': descripcionTexto!.trim(),
    };
  }
}
