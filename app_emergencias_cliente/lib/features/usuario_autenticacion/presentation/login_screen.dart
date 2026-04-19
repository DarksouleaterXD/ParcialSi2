import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import '../../../core/api_config.dart';
import '../../../core/app_colors.dart';
import '../../../core/auth_api.dart';
import '../../../core/auth_storage.dart';
import '../domain/login_validators.dart';
import 'client_shell_screen.dart';
import 'mobile_login_header.dart';
import 'session_navigation.dart';

/// Mobile-first login (distinct layout from the web panel; same API contract).
class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key, required this.storage, required this.api});

  final AuthStorage storage;
  final AuthApi api;

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  static const _border = Color(0xFFCBD5E1);
  static const _red50 = Color(0xFFFEF2F2);
  static const _red100 = Color(0xFFFEE2E2);
  static const _red800 = Color(0xFF991B1B);

  final _formKey = GlobalKey<FormState>();
  final _email = TextEditingController();
  final _password = TextEditingController();
  var _loading = false;
  var _obscurePassword = true;
  String? _error;

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_loading) {
      return;
    }
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
      if (token == null || token.isEmpty) {
        setState(() => _error = 'Respuesta inválida del servidor.');
        return;
      }
      await widget.storage.saveSession(token: token, roles: roles);
      if (!mounted) {
        return;
      }
      _navigateByRole(roles);
    } on AuthException catch (e) {
      setState(() => _error = e.message);
    } catch (_) {
      setState(() => _error = 'No se pudo conectar con el servidor');
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
          builder: (_) => ClientShellScreen(
            storage: widget.storage,
            authApi: widget.api,
            isTechnician: true,
          ),
        ),
      );
      return;
    }
    Navigator.of(context).pushReplacement(
      MaterialPageRoute<void>(
        builder: (_) => ClientShellScreen(
          storage: widget.storage,
          authApi: widget.api,
        ),
      ),
    );
  }

  void _registerHint() {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('El alta de nuevos usuarios la gestiona un administrador desde el panel web.'),
      ),
    );
  }

  InputDecorationTheme _inputTheme(ColorScheme scheme) {
    return InputDecorationTheme(
      filled: true,
      fillColor: scheme.surface,
      hintStyle: TextStyle(color: scheme.onSurfaceVariant),
      labelStyle: TextStyle(color: scheme.onSurface, fontWeight: FontWeight.w500, fontSize: 14),
      floatingLabelStyle: TextStyle(color: scheme.primary, fontWeight: FontWeight.w600),
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: const BorderSide(color: _border),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: const BorderSide(color: _border),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: BorderSide(color: scheme.primary, width: 2),
      ),
      errorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: BorderSide(color: scheme.error, width: 1),
      ),
      focusedErrorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: BorderSide(color: scheme.error, width: 2),
      ),
      errorStyle: TextStyle(color: scheme.error, fontSize: 13),
      prefixIconColor: scheme.onSurfaceVariant,
    );
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final loginTheme = Theme.of(context).copyWith(
      inputDecorationTheme: _inputTheme(scheme),
    );

    return Theme(
      data: loginTheme,
      child: Scaffold(
        backgroundColor: scheme.surfaceContainerLowest,
        body: SafeArea(
          child: CustomScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            slivers: [
              const SliverToBoxAdapter(child: MobileLoginHeader()),
              SliverPadding(
                padding: const EdgeInsets.fromLTRB(20, 20, 20, 32),
                sliver: SliverToBoxAdapter(
                  child: Center(
                    child: ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 420),
                      child: Material(
                        elevation: 2,
                        shadowColor: Colors.black26,
                        borderRadius: BorderRadius.circular(22),
                        color: scheme.surface,
                        child: Padding(
                          padding: const EdgeInsets.fromLTRB(22, 26, 22, 26),
                          child: Form(
                            key: _formKey,
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.stretch,
                              children: [
                                Text(
                                  'Bienvenido',
                                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                                        color: scheme.onSurface,
                                        fontWeight: FontWeight.w700,
                                        letterSpacing: -0.4,
                                      ),
                                ),
                                const SizedBox(height: 6),
                                Text(
                                  'Ingresá con tu correo para seguir el auxilio o tu trabajo en ruta.',
                                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                        color: scheme.onSurfaceVariant,
                                        height: 1.35,
                                      ),
                                ),
                                const SizedBox(height: 26),
                                TextFormField(
                                  controller: _email,
                                  decoration: const InputDecoration(
                                    labelText: 'Correo electrónico',
                                    hintText: 'nombre@empresa.com',
                                    prefixIcon: Icon(Icons.alternate_email_rounded),
                                  ),
                                  keyboardType: TextInputType.emailAddress,
                                  textInputAction: TextInputAction.next,
                                  autovalidateMode: AutovalidateMode.onUserInteraction,
                                  validator: validateLoginEmail,
                                  autocorrect: false,
                                ),
                                const SizedBox(height: 16),
                                TextFormField(
                                  controller: _password,
                                  decoration: InputDecoration(
                                    labelText: 'Contraseña',
                                    hintText: '••••••••',
                                    prefixIcon: const Icon(Icons.lock_outline_rounded),
                                    suffixIcon: IconButton(
                                      onPressed: () => setState(() => _obscurePassword = !_obscurePassword),
                                      tooltip: _obscurePassword ? 'Mostrar contraseña' : 'Ocultar contraseña',
                                      icon: Icon(
                                        _obscurePassword
                                            ? Icons.visibility_outlined
                                            : Icons.visibility_off_outlined,
                                        color: scheme.onSurfaceVariant,
                                      ),
                                    ),
                                  ),
                                  obscureText: _obscurePassword,
                                  autovalidateMode: AutovalidateMode.onUserInteraction,
                                  validator: validateLoginPassword,
                                  onFieldSubmitted: (_) => _submit(),
                                ),
                                if (_error != null) ...[
                                  const SizedBox(height: 18),
                                  DecoratedBox(
                                    decoration: BoxDecoration(
                                      color: _red50,
                                      borderRadius: BorderRadius.circular(14),
                                      border: Border.all(color: _red100),
                                    ),
                                    child: Padding(
                                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                                      child: Row(
                                        crossAxisAlignment: CrossAxisAlignment.start,
                                        children: [
                                          Icon(Icons.error_outline_rounded, color: scheme.error, size: 20),
                                          const SizedBox(width: 8),
                                          Expanded(
                                            child: Text(
                                              _error!,
                                              style: const TextStyle(
                                                color: _red800,
                                                fontSize: 14,
                                                height: 1.35,
                                              ),
                                            ),
                                          ),
                                        ],
                                      ),
                                    ),
                                  ),
                                ],
                                const SizedBox(height: 22),
                                FilledButton(
                                  style: FilledButton.styleFrom(
                                    backgroundColor: scheme.primary,
                                    foregroundColor: scheme.onPrimary,
                                    disabledBackgroundColor: scheme.primary.withValues(alpha: 0.5),
                                    padding: const EdgeInsets.symmetric(vertical: 15),
                                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                                    elevation: 0,
                                  ).copyWith(
                                    overlayColor: WidgetStateProperty.resolveWith(
                                      (states) =>
                                          states.contains(WidgetState.pressed) ? scheme.secondary : null,
                                    ),
                                  ),
                                  onPressed: _loading ? null : _submit,
                                  child: _loading
                                      ? const Row(
                                          mainAxisAlignment: MainAxisAlignment.center,
                                          children: [
                                            SizedBox(
                                              height: 20,
                                              width: 20,
                                              child: CircularProgressIndicator(
                                                strokeWidth: 2,
                                                color: Colors.white,
                                              ),
                                            ),
                                            SizedBox(width: 10),
                                            Text('Verificando credenciales...'),
                                          ],
                                        )
                                      : const Text('Ingresar', style: TextStyle(fontWeight: FontWeight.w700)),
                                ),
                                const SizedBox(height: 18),
                                Text.rich(
                                  TextSpan(
                                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: scheme.onSurfaceVariant),
                                    children: [
                                      const TextSpan(text: '¿Primera vez? '),
                                      WidgetSpan(
                                        alignment: PlaceholderAlignment.baseline,
                                        baseline: TextBaseline.alphabetic,
                                        child: GestureDetector(
                                          onTap: _registerHint,
                                          child: Text(
                                            'Cómo registrarme',
                                            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                                  color: AppColors.orange500,
                                                  fontWeight: FontWeight.w700,
                                                ),
                                          ),
                                        ),
                                      ),
                                    ],
                                  ),
                                  textAlign: TextAlign.center,
                                ),
                                if (kDebugMode) ...[
                                  const SizedBox(height: 14),
                                  SelectableText(
                                    'API: $kApiBase',
                                    textAlign: TextAlign.center,
                                    style: Theme.of(context).textTheme.bodySmall?.copyWith(color: scheme.onSurfaceVariant),
                                  ),
                                ],
                              ],
                            ),
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Administración: mismo aviso funcional que el flujo móvil para rol admin.
class AdminNoticeScreen extends StatelessWidget {
  const AdminNoticeScreen({super.key, required this.storage, required this.api});

  final AuthStorage storage;
  final AuthApi api;

  Future<void> _logout(BuildContext context) async {
    await logoutAndNavigateToLogin(
      context: context,
      storage: storage,
      authApi: api,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Panel web')),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.language, size: 48),
              const SizedBox(height: 16),
              Text(
                'La administración se realiza en la web.',
                style: Theme.of(context).textTheme.titleMedium,
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 24),
              FilledButton.icon(
                onPressed: () => _logout(context),
                icon: const Icon(Icons.logout),
                label: const Text('Cerrar sesión'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
