import 'package:flutter/material.dart';

import '../../core/api_config.dart';
import '../../core/auth_api.dart';
import '../../core/auth_storage.dart';
import 'client_home_screen.dart';
import 'technician_home_screen.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key, required this.storage, required this.api});

  final AuthStorage storage;
  final AuthApi api;

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _email = TextEditingController();
  final _password = TextEditingController();
  var _loading = false;
  String? _error;

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    setState(() => _error = null);
    if (!(_formKey.currentState?.validate() ?? false)) {
      return;
    }
    setState(() => _loading = true);
    try {
      final data = await widget.api.login(
        email: _email.text.trim(),
        password: _password.text,
      );
      final token = data['access_token'] as String?;
      final roles = (data['roles'] as List<dynamic>? ?? []).map((e) => e.toString()).toList();
      if (token == null) {
        throw AuthException(500, 'Respuesta inválida del servidor');
      }
      await widget.storage.saveSession(token: token, roles: roles);
      if (!mounted) {
        return;
      }
      _navigateByRole(roles);
    } on AuthException catch (e) {
      setState(() => _error = e.message);
    } catch (_) {
      setState(() => _error = 'Error de red. API: $kApiBase');
    } finally {
      if (mounted) {
        setState(() => _loading = false);
      }
    }
  }

  void _navigateByRole(List<String> roles) {
    if (roles.contains('Administrador')) {
      Navigator.of(context).pushReplacement(
        MaterialPageRoute<void>(
          builder: (_) => AdminNoticeScreen(storage: widget.storage, api: widget.api),
        ),
      );
      return;
    }
    if (roles.contains('Tecnico')) {
      Navigator.of(context).pushReplacement(
        MaterialPageRoute<void>(
          builder: (_) => TechnicianHomeScreen(storage: widget.storage, api: widget.api),
        ),
      );
      return;
    }
    Navigator.of(context).pushReplacement(
      MaterialPageRoute<void>(
        builder: (_) => ClientHomeScreen(storage: widget.storage, api: widget.api),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        width: double.infinity,
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            colors: [Color(0xFF0F172A), Color(0xFF1E293B), Color(0xFF0F172A)],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
        ),
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 400),
              child: Card(
                elevation: 8,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Form(
                    key: _formKey,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Text('Iniciar sesión', style: Theme.of(context).textTheme.headlineSmall),
                        const SizedBox(height: 8),
                        Text(
                          'Cliente / Técnico',
                          style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: Colors.black54),
                        ),
                        const SizedBox(height: 20),
                        TextFormField(
                          controller: _email,
                          decoration: const InputDecoration(labelText: 'Email'),
                          keyboardType: TextInputType.emailAddress,
                          validator: (v) =>
                              v == null || v.trim().isEmpty ? 'Ingresá el email' : null,
                        ),
                        const SizedBox(height: 12),
                        TextFormField(
                          controller: _password,
                          decoration: const InputDecoration(labelText: 'Contraseña'),
                          obscureText: true,
                          validator: (v) =>
                              v == null || v.length < 4 ? 'Contraseña demasiado corta' : null,
                        ),
                        if (_error != null) ...[
                          const SizedBox(height: 12),
                          Text(_error!, style: const TextStyle(color: Colors.red)),
                        ],
                        const SizedBox(height: 20),
                        FilledButton(
                          onPressed: _loading ? null : _submit,
                          child: Text(_loading ? 'Ingresando…' : 'Ingresar'),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          'API: $kApiBase',
                          style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Colors.black45),
                          textAlign: TextAlign.center,
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// Pantalla mínima si un administrador abre la app móvil.
class AdminNoticeScreen extends StatelessWidget {
  const AdminNoticeScreen({super.key, required this.storage, required this.api});

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
      appBar: AppBar(title: const Text('Administrador')),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Text(
                'La administración de usuarios está en la aplicación web.',
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 24),
              FilledButton(
                onPressed: () => _logout(context),
                child: const Text('Cerrar sesión'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
