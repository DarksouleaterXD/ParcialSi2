import 'dart:async';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../../core/auth_api.dart';
import '../../../core/auth_storage.dart';
import '../../../core/authorized_client.dart';
import '../../../core/widgets/floating_pill_nav_bar.dart';
import '../../../core/widgets/quick_actions_sheet.dart';
import '../data/profile_api.dart';
import '../data/vehicles_api.dart';
import 'client_home_tab.dart';
import 'profile_screen.dart';
import 'session_navigation.dart';
import '../../incidentes_servicios/offline/pending_incident_sync_service.dart';
import '../../incidentes_servicios/offline/pending_incidents_store.dart';
import '../../incidentes_servicios/presentation/pending_outbox_screen.dart';
import '../../incidentes_servicios/presentation/activity_tab.dart';
import '../../incidentes_servicios/presentation/report_incident_screen.dart';
import 'vehicle_form_screen.dart';
import 'vehicles_list_tab.dart';

/// Shell principal: inicio, vehículos, actividad o asignados, perfil y barra flotante.
class ClientShellScreen extends StatefulWidget {
  const ClientShellScreen({
    super.key,
    required this.storage,
    required this.authApi,
    this.isTechnician = false,
  });

  final AuthStorage storage;
  final AuthApi authApi;
  final bool isTechnician;

  @override
  State<ClientShellScreen> createState() => _ClientShellScreenState();
}

class _ClientShellScreenState extends State<ClientShellScreen> {
  late final AuthorizedClient _authorized = AuthorizedClient(storage: widget.storage);
  late final VehiclesApi _vehiclesApi = VehiclesApi(_authorized);
  late final ProfileApi _profileApi = ProfileApi(_authorized);
  final GlobalKey<VehiclesListTabState> _vehiclesKey = GlobalKey();
  StreamSubscription<List<ConnectivityResult>>? _connectivitySub;

  /// Pestaña inferior: `0` Inicio, `1` Vehículos, `3` Actividad, `4` Perfil. El FAB `+` es contextual.
  var _slot = 0;

  int _stackIndex() {
    if (_slot <= 1) {
      return _slot;
    }
    if (_slot == 3) {
      return 2;
    }
    return 3;
  }

  String _title() {
    switch (_slot) {
      case 0:
        return 'Inicio';
      case 1:
        return 'Mis vehículos';
      case 3:
        return widget.isTechnician ? 'Mis asignados' : 'Mis emergencias';
      case 4:
        return 'Mi perfil';
      default:
        return 'Emergencias';
    }
  }

  void _goToLogin() {
    navigateToLoginReplacingStack(
      context: context,
      storage: widget.storage,
      authApi: widget.authApi,
    );
  }

  Future<void> _logoutFromShell() async {
    await logoutAndNavigateToLogin(
      context: context,
      storage: widget.storage,
      authApi: widget.authApi,
    );
  }

  String _fabTooltipForCurrentTab() {
    switch (_slot) {
      case 0:
        return 'Reportar emergencia';
      case 1:
        return 'Agregar vehículo';
      case 3:
      case 4:
        return 'Acciones rápidas';
      default:
        return 'Acciones rápidas';
    }
  }

  void _handleCenterTap() {
    switch (_slot) {
      case 0:
        _openReportEmergency();
        break;
      case 1:
        unawaited(_openCreateVehicle());
        break;
      case 3:
      case 4:
        _openQuickActions();
        break;
      default:
        _openQuickActions();
    }
  }

  void _handleCenterLongPress() {
    HapticFeedback.mediumImpact();
    _openQuickActions();
  }

  void _openQuickActions() {
    QuickActionsSheet.show(
      context: context,
      onAddVehicle: _openCreateVehicle,
      onReportEmergency: _openReportEmergency,
    );
  }

  void _openReportEmergency() {
    if (widget.isTechnician) {
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Reportar emergencia solo está disponible para clientes.')),
      );
      return;
    }
    Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (_) => ReportIncidentScreen(
          storage: widget.storage,
          authApi: widget.authApi,
          vehiclesApi: _vehiclesApi,
        ),
      ),
    );
  }

  @override
  void initState() {
    super.initState();
    _connectivitySub = Connectivity().onConnectivityChanged.listen(_onConnectivityChanged);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!widget.isTechnician) {
        unawaited(_trySyncPending(showSnack: false));
      }
    });
  }

  @override
  void dispose() {
    _connectivitySub?.cancel();
    super.dispose();
  }

  void _onConnectivityChanged(List<ConnectivityResult> results) {
    if (widget.isTechnician) {
      return;
    }
    final offline = results.length == 1 && results.first == ConnectivityResult.none;
    if (!offline) {
      unawaited(_trySyncPending(showSnack: true));
    }
  }

  Future<void> _trySyncPending({bool showSnack = true}) async {
    if (widget.isTechnician || pendingIncidentsGlobal.count == 0) {
      return;
    }
    final sync = PendingIncidentSyncService(
      storage: widget.storage,
      store: pendingIncidentsGlobal,
    );
    final n = await sync.syncAll();
    if (!mounted) {
      return;
    }
    setState(() {});
    if (showSnack && n > 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(n == 1 ? 'Se envió 1 reporte pendiente.' : 'Se enviaron $n reportes pendientes.')),
      );
    }
  }

  void _openPendingOutbox() {
    Navigator.of(context)
        .push<void>(
      MaterialPageRoute<void>(
        builder: (_) => PendingOutboxScreen(storage: widget.storage),
      ),
    )
        .then((_) {
      if (mounted) {
        setState(() {});
      }
    });
  }

  Future<void> _openCreateVehicle() async {
    final ok = await Navigator.of(context).push<bool>(
      MaterialPageRoute<bool>(
        builder: (_) => VehicleFormScreen(
          api: _vehiclesApi,
          onSessionExpired: _goToLogin,
        ),
      ),
    );
    if (ok == true && mounted) {
      _vehiclesKey.currentState?.reload();
    }
  }

  @override
  Widget build(BuildContext context) {
    final bottomPad = MediaQuery.paddingOf(context).bottom;
    return Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      extendBody: true,
      appBar: AppBar(
        title: Text(_title()),
        centerTitle: false,
        automaticallyImplyLeading: false,
        actions: [
          if (!widget.isTechnician && pendingIncidentsGlobal.count > 0)
            IconButton(
              tooltip: 'Pendientes de envío',
              onPressed: _openPendingOutbox,
              icon: Badge.count(
                count: pendingIncidentsGlobal.count,
                child: const Icon(Icons.outbox_rounded),
              ),
            ),
          IconButton(
            tooltip: 'Cerrar sesión',
            icon: const Icon(Icons.logout_rounded),
            onPressed: _logoutFromShell,
          ),
        ],
        leading: _slot == 4
            ? IconButton(
                icon: const Icon(Icons.arrow_back_rounded),
                tooltip: 'Volver',
                onPressed: () => setState(() => _slot = 0),
              )
            : null,
      ),
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (!widget.isTechnician && pendingIncidentsGlobal.count > 0)
            Material(
              color: Theme.of(context).colorScheme.secondaryContainer.withValues(alpha: 0.5),
              child: ListTile(
                leading: Icon(Icons.schedule_send_rounded, color: Theme.of(context).colorScheme.onSecondaryContainer),
                title: Text(
                  'Pendiente de envío',
                  style: TextStyle(
                    fontWeight: FontWeight.w700,
                    color: Theme.of(context).colorScheme.onSecondaryContainer,
                  ),
                ),
                subtitle: Text(
                  '${pendingIncidentsGlobal.count} reporte(s) en cola en este dispositivo.',
                  style: TextStyle(color: Theme.of(context).colorScheme.onSecondaryContainer),
                ),
                trailing: FilledButton.tonal(
                  onPressed: () => unawaited(_trySyncPending(showSnack: true)),
                  child: const Text('Reintentar ahora'),
                ),
                onTap: _openPendingOutbox,
              ),
            ),
          Expanded(
            child: IndexedStack(
              index: _stackIndex(),
              children: [
          ClientHomeTab(
            profileApi: _profileApi,
            onSessionExpired: _goToLogin,
            onOpenVehicles: () => setState(() => _slot = 1),
            onOpenIncidents: () => setState(() => _slot = 3),
            onAddVehicle: _openCreateVehicle,
            onReportEmergency: widget.isTechnician ? null : _openReportEmergency,
            isTechnician: widget.isTechnician,
          ),
          VehiclesListTab(
            key: _vehiclesKey,
            api: _vehiclesApi,
            onSessionExpired: _goToLogin,
            onAddVehicle: _openCreateVehicle,
          ),
          ActivityTab(
            storage: widget.storage,
            authApi: widget.authApi,
            onSessionExpired: _goToLogin,
            onGoToInicioTab: () => setState(() => _slot = 0),
            isTechnician: widget.isTechnician,
          ),
          ProfileScreen(
            storage: widget.storage,
            authApi: widget.authApi,
            embeddedInShell: true,
          ),
              ],
            ),
          ),
        ],
      ),
      bottomNavigationBar: Padding(
        padding: EdgeInsets.fromLTRB(20, 0, 20, 12 + bottomPad),
        child: FloatingPillNavBar(
          selectedSlot: _slot,
          onSlotTap: (s) => setState(() => _slot = s),
          onCenterTap: _handleCenterTap,
          onCenterLongPress: _handleCenterLongPress,
          centerTooltip: _fabTooltipForCurrentTab(),
          activityNavLabel: widget.isTechnician ? 'Asignados' : 'Actividad',
        ),
      ),
    );
  }
}
