import 'package:flutter/material.dart';

import 'core/auth_api.dart';
import 'core/auth_storage.dart';
import 'features/usuario_autenticacion/client_home_screen.dart';
import 'features/usuario_autenticacion/login_screen.dart';
import 'features/usuario_autenticacion/technician_home_screen.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const EmergenciasApp());
}

class EmergenciasApp extends StatelessWidget {
  const EmergenciasApp({super.key});

  @override
  Widget build(BuildContext context) {
    final storage = AuthStorage();
    final api = AuthApi();
    return MaterialApp(
      title: 'Emergencias Cliente',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF2563EB)),
        useMaterial3: true,
      ),
      home: _SessionGate(storage: storage, api: api),
    );
  }
}

class _SessionGate extends StatelessWidget {
  const _SessionGate({required this.storage, required this.api});

  final AuthStorage storage;
  final AuthApi api;

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<String?>(
      future: storage.readToken(),
      builder: (context, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return const Scaffold(
            body: Center(child: CircularProgressIndicator()),
          );
        }
        final token = snap.data;
        if (token == null || token.isEmpty) {
          return LoginScreen(storage: storage, api: api);
        }
        return FutureBuilder<List<String>>(
          future: storage.readRoles(),
          builder: (context, roleSnap) {
            if (roleSnap.connectionState != ConnectionState.done) {
              return const Scaffold(
                body: Center(child: CircularProgressIndicator()),
              );
            }
            final roles = roleSnap.data ?? [];
            if (roles.contains('Administrador')) {
              return AdminNoticeScreen(storage: storage, api: api);
            }
            if (roles.contains('Tecnico')) {
              return TechnicianHomeScreen(storage: storage, api: api);
            }
            return ClientHomeScreen(storage: storage, api: api);
          },
        );
      },
    );
  }
}
