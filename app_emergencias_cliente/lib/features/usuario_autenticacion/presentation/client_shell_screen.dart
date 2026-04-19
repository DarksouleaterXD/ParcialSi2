import 'package:flutter/material.dart';

import '../../../core/auth_api.dart';
import '../../../core/auth_storage.dart';
import '../../../core/authorized_client.dart';
import '../../../core/widgets/floating_pill_nav_bar.dart';
import '../data/profile_api.dart';
import '../data/vehicles_api.dart';
import 'client_home_tab.dart';
import 'profile_screen.dart';
import 'session_navigation.dart';
import 'vehicle_form_screen.dart';
import 'vehicles_list_tab.dart';

/// Client shell: home summary, vehicles (CU-05), activity placeholder, profile + pill nav.
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

  /// Bottom bar: `0` Inicio, `1` Vehículos, `3` Actividad, `4` Perfil (center = add vehicle).
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
        return 'Actividad';
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
      body: IndexedStack(
        index: _stackIndex(),
        children: [
          ClientHomeTab(
            profileApi: _profileApi,
            onSessionExpired: _goToLogin,
            onOpenVehicles: () => setState(() => _slot = 1),
            onAddVehicle: _openCreateVehicle,
          ),
          VehiclesListTab(
            key: _vehiclesKey,
            api: _vehiclesApi,
            onSessionExpired: _goToLogin,
            onAddVehicle: _openCreateVehicle,
          ),
          const _PlaceholderTab(
            icon: Icons.history_outlined,
            title: 'Actividad',
            subtitle: 'Acá verás el historial de auxilios e incidentes cuando esté disponible.',
          ),
          ProfileScreen(
            storage: widget.storage,
            authApi: widget.authApi,
            embeddedInShell: true,
          ),
        ],
      ),
      bottomNavigationBar: Padding(
        padding: EdgeInsets.fromLTRB(20, 0, 20, 12 + bottomPad),
        child: FloatingPillNavBar(
          selectedSlot: _slot,
          onSlotTap: (s) => setState(() => _slot = s),
          onCenterTap: _openCreateVehicle,
        ),
      ),
    );
  }
}

class _PlaceholderTab extends StatelessWidget {
  const _PlaceholderTab({
    required this.icon,
    required this.title,
    required this.subtitle,
  });

  final IconData icon;
  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, size: 56, color: Theme.of(context).colorScheme.outline),
            const SizedBox(height: 20),
            Text(
              title,
              style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w700),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 12),
            Text(
              subtitle,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}
