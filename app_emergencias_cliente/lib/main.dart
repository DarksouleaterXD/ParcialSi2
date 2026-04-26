import 'package:app_emergencias_cliente/features/incidentes_servicios/offline/pending_incidents_store.dart';
import 'package:flutter/material.dart';
import 'package:flutter_stripe/flutter_stripe.dart';
import 'package:hive_flutter/hive_flutter.dart';

import 'core/auth_api.dart';
import 'core/auth_storage.dart';
import 'core/theme/app_spacing.dart';
import 'core/theme/app_theme.dart';
import 'core/widgets/app_empty_state.dart';
import 'core/widgets/primary_button.dart';
import 'features/usuario_autenticacion/presentation/client_shell_screen.dart';
import 'features/usuario_autenticacion/presentation/login_screen.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  Stripe.publishableKey = const String.fromEnvironment('STRIPE_PUB_KEY', defaultValue: '');
  await Hive.initFlutter();
  await Hive.openBox<String>(kPendingIncidentsHiveBox);
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
      theme: AppTheme.light(),
      home: _SessionGate(storage: storage, api: api),
    );
  }
}

class _SessionGate extends StatefulWidget {
  const _SessionGate({required this.storage, required this.api});

  final AuthStorage storage;
  final AuthApi api;

  @override
  State<_SessionGate> createState() => _SessionGateState();
}

class _SessionGateState extends State<_SessionGate> {
  late Future<_BootstrapResult> _future;

  @override
  void initState() {
    super.initState();
    _future = _bootstrap();
  }

  void _retryBootstrap() {
    setState(() => _future = _bootstrap());
  }

  Future<_BootstrapResult> _bootstrap() async {
    final token = await widget.storage.readToken();
    if (token == null || token.isEmpty) {
      return const _BootstrapResult.none();
    }
    final status = await widget.api.validateSession(token);
    switch (status) {
      case SessionStatus.valid:
        final roles = await widget.storage.readRoles();
        return _BootstrapResult.loggedIn(roles);
      case SessionStatus.unauthorized:
        await widget.storage.clear();
        return const _BootstrapResult.none();
      case SessionStatus.transientFailure:
        return const _BootstrapResult.retry();
    }
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<_BootstrapResult>(
      future: _future,
      builder: (context, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return const Scaffold(
            body: Center(child: AppLoadingState(message: 'Iniciando…')),
          );
        }
        final result = snap.data ?? const _BootstrapResult.none();
        if (result.needsRetry) {
          return Scaffold(
            backgroundColor: Theme.of(context).scaffoldBackgroundColor,
            body: Center(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: AppSpacing.xl),
                child: AppEmptyState(
                  icon: Icons.cloud_off_outlined,
                  title: 'No se pudo conectar con el servidor',
                  subtitle: 'Comprobá tu conexión y que el backend esté en ejecución.',
                  action: SecondaryButton(
                    label: 'Reintentar',
                    icon: Icons.refresh_rounded,
                    onPressed: _retryBootstrap,
                  ),
                ),
              ),
            ),
          );
        }
        if (!result.hasSession) {
          return LoginScreen(storage: widget.storage, api: widget.api);
        }
        final roles = result.roles;
        if (roles.contains('Administrador')) {
          return AdminNoticeScreen(storage: widget.storage, api: widget.api);
        }
        if (roles.contains('Tecnico')) {
          return ClientShellScreen(
            storage: widget.storage,
            authApi: widget.api,
            isTechnician: true,
          );
        }
        return ClientShellScreen(
          storage: widget.storage,
          authApi: widget.api,
        );
      },
    );
  }
}

class _BootstrapResult {
  const _BootstrapResult.loggedIn(this.roles)
      : hasSession = true,
        needsRetry = false;

  const _BootstrapResult.none()
      : hasSession = false,
        needsRetry = false,
        roles = const [];

  const _BootstrapResult.retry()
      : hasSession = false,
        needsRetry = true,
        roles = const [];

  final bool hasSession;
  final bool needsRetry;
  final List<String> roles;
}
