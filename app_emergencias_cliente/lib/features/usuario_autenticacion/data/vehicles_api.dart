import '../../../core/authorized_client.dart';
import '../domain/vehicle.dart';

/// CU-05: API `/vehiculos` (listado paginado y CRUD).
class VehiclesApi {
  VehiclesApi(this._client);

  final AuthorizedClient _client;

  Future<VehicleListPage> list({int page = 1, int pageSize = 20}) async {
    final path = '/vehiculos?page=$page&page_size=$pageSize';
    final json = await _client.getJson(path);
    return VehicleListPage.fromJson(json);
  }

  Future<Vehicle> getById(int id) async {
    final json = await _client.getJson('/vehiculos/$id');
    return Vehicle.fromJson(json);
  }

  Future<Vehicle> create(Map<String, dynamic> body) async {
    final json = await _client.postJson('/vehiculos', body: body);
    return Vehicle.fromJson(json);
  }

  Future<Vehicle> update(int id, Map<String, dynamic> body) async {
    final json = await _client.patchJson('/vehiculos/$id', body);
    return Vehicle.fromJson(json);
  }

  Future<void> delete(int id) async {
    await _client.delete('/vehiculos/$id');
  }
}
