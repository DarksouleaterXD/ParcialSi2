import 'package:flutter/material.dart';

import '../../core/auth_api.dart';
import '../../core/auth_storage.dart';
import 'login_screen.dart';

class TechnicianHomeScreen extends StatelessWidget {
  const TechnicianHomeScreen({super.key, required this.storage, required this.api});

  final AuthStorage storage;
  final AuthApi api;

  Future<void> _logout(BuildContext context) async {
    final token = await storage.readToken();
    if (token != null) {
      try {
        await api.logout(token);
      } catch (_) {}
    }
    await storage.clear();
    if (context.mounted) {
      Navigator.of(context).pushAndRemoveUntil(
        MaterialPageRoute<void>(
          builder: (_) => LoginScreen(storage: storage, api: api),
        ),
        (_) => false,
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Técnico'),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: () => _logout(context),
            tooltip: 'Cerrar sesión',
          ),
        ],
      ),
      body: const Center(
        child: Padding(
          padding: EdgeInsets.all(24),
          child: Text(
            'Sesión iniciada como Técnico.\nAquí irán asignaciones y estados de servicio.',
            textAlign: TextAlign.center,
          ),
        ),
      ),
    );
  }
}
