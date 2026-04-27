class AppNotification {
  const AppNotification({
    required this.id,
    required this.titulo,
    required this.mensaje,
    required this.leida,
    this.tipo,
    this.fechaHora,
  });

  final int id;
  final String titulo;
  final String mensaje;
  final bool leida;
  final String? tipo;
  final DateTime? fechaHora;

  factory AppNotification.fromJson(Map<String, dynamic> json) {
    DateTime? dt;
    final raw = json['fecha_hora'];
    if (raw is String) {
      dt = DateTime.tryParse(raw);
    }
    return AppNotification(
      id: (json['id'] as num).toInt(),
      titulo: (json['titulo'] as String?) ?? '',
      mensaje: (json['mensaje'] as String?) ?? '',
      leida: json['leida'] == true,
      tipo: json['tipo'] as String?,
      fechaHora: dt,
    );
  }
}

class AppNotificationListPage {
  const AppNotificationListPage({
    required this.items,
    required this.total,
    required this.page,
    required this.pageSize,
  });

  final List<AppNotification> items;
  final int total;
  final int page;
  final int pageSize;

  factory AppNotificationListPage.fromJson(Map<String, dynamic> json) {
    final raw = json['items'];
    final list = <AppNotification>[];
    if (raw is List) {
      for (final e in raw) {
        if (e is Map<String, dynamic>) {
          list.add(AppNotification.fromJson(e));
        }
      }
    }
    return AppNotificationListPage(
      items: list,
      total: (json['total'] as num?)?.toInt() ?? 0,
      page: (json['page'] as num?)?.toInt() ?? 1,
      pageSize: (json['page_size'] as num?)?.toInt() ?? 0,
    );
  }
}
