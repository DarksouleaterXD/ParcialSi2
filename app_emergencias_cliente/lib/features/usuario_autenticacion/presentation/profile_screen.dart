import 'package:flutter/material.dart';

import '../../../core/auth_api.dart';
import '../../../core/auth_storage.dart';
import '../../../core/authorized_client.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/widgets/app_empty_state.dart';
import '../../../core/widgets/app_phone_field.dart';
import '../../../core/widgets/app_section_header.dart';
import '../../../core/widgets/app_snackbar.dart';
import '../../../core/widgets/app_text_field.dart';
import '../../../core/widgets/primary_button.dart';
import '../data/profile_api.dart';
import '../domain/user_profile.dart';
import 'change_password_sheet.dart';
import 'session_navigation.dart';

/// Perfil autenticado: lectura y edición vía `GET` / `PATCH` `/auth/me`.
class ProfileScreen extends StatefulWidget {
  const ProfileScreen({
    super.key,
    required this.storage,
    required this.authApi,
    this.embeddedInShell = false,
  });

  final AuthStorage storage;
  final AuthApi authApi;

  /// When `true`, omits [Scaffold]/[AppBar] (host shell provides chrome).
  final bool embeddedInShell;

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  late final AuthorizedClient _authorized = AuthorizedClient(storage: widget.storage);
  late final ProfileApi _profileApi = ProfileApi(_authorized);

  final _nombre = TextEditingController();
  final _apellido = TextEditingController();
  final _telefono = TextEditingController();
  final _foto = TextEditingController();
  final _formKey = GlobalKey<FormState>();

  UserProfile? _profile;
  var _loading = true;
  String? _loadError;
  var _editing = false;
  var _saving = false;
  String? _saveError;

  @override
  void initState() {
    super.initState();
    _loadProfile();
  }

  @override
  void dispose() {
    _nombre.dispose();
    _apellido.dispose();
    _telefono.dispose();
    _foto.dispose();
    super.dispose();
  }

  void _applyFromProfile(UserProfile p) {
    _nombre.text = p.nombre;
    _apellido.text = p.apellido;
    _telefono.text = p.telefono ?? '';
    _foto.text = p.fotoPerfil ?? '';
  }

  Future<void> _loadProfile() async {
    setState(() {
      _loading = true;
      _loadError = null;
    });
    try {
      final p = await _profileApi.fetchProfile();
      if (!mounted) {
        return;
      }
      setState(() {
        _profile = p;
        _applyFromProfile(p);
        _loading = false;
      });
    } on SessionExpiredException {
      if (mounted) {
        _goToLogin();
      }
    } on ApiClientException catch (e) {
      if (mounted) {
        setState(() {
          _loading = false;
          _loadError = e.message;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          _loading = false;
          _loadError = 'No se pudo conectar con el servidor';
        });
      }
    }
  }

  /// Re-fetch profile so UI matches persisted server state after PATCH.
  Future<void> _reloadProfileAfterSave() async {
    try {
      final p = await _profileApi.fetchProfile();
      if (!mounted) {
        return;
      }
      setState(() {
        _profile = p;
        _applyFromProfile(p);
      });
    } on SessionExpiredException {
      if (mounted) {
        _goToLogin();
      }
    } catch (_) {
      // PATCH succeeded; ignore transient GET failures.
    }
  }

  void _goToLogin() {
    navigateToLoginReplacingStack(
      context: context,
      storage: widget.storage,
      authApi: widget.authApi,
    );
  }

  Future<void> _logout() async {
    await logoutAndNavigateToLogin(
      context: context,
      storage: widget.storage,
      authApi: widget.authApi,
    );
  }

  void _openChangePassword() {
    showChangePasswordSheet(
      context,
      profileApi: _profileApi,
      onSessionExpired: _goToLogin,
    );
  }

  void _startEdit() {
    setState(() {
      _editing = true;
      _saveError = null;
    });
  }

  void _cancelEdit() {
    if (_profile != null) {
      _applyFromProfile(_profile!);
    }
    setState(() {
      _editing = false;
      _saveError = null;
    });
  }

  Future<void> _saveProfile() async {
    setState(() => _saveError = null);
    if (!(_formKey.currentState?.validate() ?? false)) {
      return;
    }
    final p = _profile;
    if (p == null) {
      return;
    }
    final patch = <String, dynamic>{};
    final nombre = _nombre.text.trim();
    final apellido = _apellido.text.trim();
    final tel = _telefono.text.trim();
    final foto = _foto.text.trim();

    if (nombre != p.nombre) {
      patch['nombre'] = nombre;
    }
    if (apellido != p.apellido) {
      patch['apellido'] = apellido;
    }
    final prevTel = p.telefono ?? '';
    if (tel != prevTel) {
      patch['telefono'] = tel.isEmpty ? '' : tel;
    }
    final prevFoto = p.fotoPerfil ?? '';
    if (foto != prevFoto) {
      patch['foto_perfil'] = foto.isEmpty ? '' : foto;
    }

    if (patch.isEmpty) {
      AppSnackBar.info(context, 'No hay cambios para guardar.');
      setState(() => _editing = false);
      return;
    }

    setState(() => _saving = true);
    try {
      await _profileApi.updateProfile(patch);
      if (!mounted) {
        return;
      }
      setState(() {
        _editing = false;
        _saving = false;
      });
      await _reloadProfileAfterSave();
      if (!mounted) {
        return;
      }
      AppSnackBar.success(context, 'Perfil actualizado correctamente.');
    } on SessionExpiredException {
      if (mounted) {
        _goToLogin();
      }
    } on ApiClientException catch (e) {
      if (mounted) {
        setState(() {
          _saving = false;
          _saveError = e.message;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          _saving = false;
          _saveError = 'No se pudo conectar con el servidor';
        });
      }
    }
  }

  String? _requiredName(String? v) {
    if (v == null || v.trim().isEmpty) {
      return 'Completá este campo.';
    }
    return null;
  }

  String? _telefonoValidator(String? v) {
    if (v == null || v.trim().isEmpty) {
      return null;
    }
    if (v.trim().length > 20) {
      return 'Máximo 20 caracteres.';
    }
    return null;
  }

  @override
  Widget build(BuildContext context) {
    final body = _buildBody(context);
    if (widget.embeddedInShell) {
      return body;
    }
    return Scaffold(
      appBar: AppBar(
        title: const Text('Mi perfil'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          tooltip: 'Volver',
          onPressed: () => Navigator.of(context).pop(),
        ),
        actions: [
          TextButton(
            onPressed: _logout,
            child: const Text('Cerrar sesión'),
          ),
        ],
      ),
      body: body,
    );
  }

  Widget _buildBody(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;

    if (_loading) {
      return const _ProfileSkeleton();
    }
    if (_loadError != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
          child: AppEmptyState(
            icon: Icons.cloud_off_outlined,
            iconColor: scheme.onSurfaceVariant,
            title: 'No pudimos cargar tu perfil',
            subtitle: _loadError!,
            action: SecondaryButton(
              label: 'Reintentar',
              icon: Icons.refresh_rounded,
              onPressed: _loadProfile,
            ),
          ),
        ),
      );
    }

    final p = _profile!;
    final keyboardInset = MediaQuery.viewInsetsOf(context).bottom;
    final bottomPad =
        (widget.embeddedInShell ? 100.0 : AppSpacing.xxl + 16) + keyboardInset;
    return SafeArea(
      top: true,
      bottom: false,
      left: true,
      right: true,
      minimum: EdgeInsets.zero,
      child: SingleChildScrollView(
        padding: EdgeInsets.fromLTRB(AppSpacing.lg, AppSpacing.md, AppSpacing.lg, bottomPad),
        child: Form(
          key: _formKey,
          autovalidateMode: AutovalidateMode.onUserInteraction,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(AppSpacing.lg),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      const AppSectionHeader(title: 'Información de la cuenta'),
                      const SizedBox(height: AppSpacing.md),
                      Text(
                        'Correo electrónico',
                        style: Theme.of(context).textTheme.labelLarge?.copyWith(
                              color: scheme.onSurfaceVariant,
                              fontWeight: FontWeight.w600,
                            ),
                      ),
                      const SizedBox(height: AppSpacing.xxs),
                      SelectableText(
                        p.email,
                        style: Theme.of(context).textTheme.bodyLarge?.copyWith(fontWeight: FontWeight.w600),
                      ),
                      if (p.roles.isNotEmpty) ...[
                        const SizedBox(height: AppSpacing.sm),
                        Text(
                          'Roles',
                          style: Theme.of(context).textTheme.labelLarge?.copyWith(
                                color: scheme.onSurfaceVariant,
                                fontWeight: FontWeight.w600,
                              ),
                        ),
                        const SizedBox(height: AppSpacing.xxs),
                        Text(p.roles.join(', '), style: Theme.of(context).textTheme.bodyMedium),
                      ],
                      if (p.estado != null && p.estado!.isNotEmpty) ...[
                        const SizedBox(height: AppSpacing.sm),
                        Wrap(
                          spacing: AppSpacing.xs,
                          runSpacing: AppSpacing.xs,
                          crossAxisAlignment: WrapCrossAlignment.center,
                          children: [
                            Text(
                              'Estado',
                              style: Theme.of(context).textTheme.labelLarge?.copyWith(
                                    color: scheme.onSurfaceVariant,
                                    fontWeight: FontWeight.w600,
                                  ),
                            ),
                            _SoftBadge(label: p.estado!),
                          ],
                        ),
                      ],
                      if (p.fechaRegistro != null && p.fechaRegistro!.isNotEmpty) ...[
                        const SizedBox(height: AppSpacing.sm),
                        Text(
                          'Registro: ${p.fechaRegistro}',
                          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                color: scheme.onSurfaceVariant,
                              ),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
              const SizedBox(height: AppSpacing.md),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(AppSpacing.lg),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      const AppSectionHeader(title: 'Datos personales'),
                      if (!_editing) ...[
                        const SizedBox(height: AppSpacing.sm),
                        SizedBox(
                          width: double.infinity,
                          child: FilledButton.tonal(
                            onPressed: _startEdit,
                            child: const Text('Editar perfil'),
                          ),
                        ),
                      ],
                      const SizedBox(height: AppSpacing.md),
                      AppTextField(
                        controller: _nombre,
                        label: 'Nombre',
                        readOnly: !_editing,
                        prefixIcon: Icons.person_outline_rounded,
                        validator: _requiredName,
                      ),
                      const SizedBox(height: AppSpacing.sm),
                      AppTextField(
                        controller: _apellido,
                        label: 'Apellido',
                        readOnly: !_editing,
                        prefixIcon: Icons.badge_outlined,
                        validator: _requiredName,
                      ),
                      const SizedBox(height: AppSpacing.sm),
                      AppPhoneField(
                        controller: _telefono,
                        label: 'Teléfono',
                        helperText: 'Opcional. Hasta 20 caracteres.',
                        readOnly: !_editing,
                        validator: _telefonoValidator,
                      ),
                      const SizedBox(height: AppSpacing.sm),
                      AppTextField(
                        controller: _foto,
                        label: 'Foto de perfil (URL)',
                        helperText: 'Opcional. Máximo 255 caracteres.',
                        readOnly: !_editing,
                        prefixIcon: Icons.link_rounded,
                        keyboardType: TextInputType.url,
                        maxLines: 2,
                        validator: (v) {
                          if (v == null || v.trim().isEmpty) {
                            return null;
                          }
                          if (v.trim().length > 255) {
                            return 'Máximo 255 caracteres.';
                          }
                          return null;
                        },
                      ),
                      if (_saveError != null) ...[
                        const SizedBox(height: AppSpacing.sm),
                        Text(
                          _saveError!,
                          style: TextStyle(
                            color: scheme.error,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                      if (_editing) ...[
                        const SizedBox(height: AppSpacing.lg),
                        Row(
                          children: [
                            Expanded(
                              child: SecondaryButton(
                                label: 'Cancelar',
                                onPressed: _saving ? null : _cancelEdit,
                              ),
                            ),
                            const SizedBox(width: AppSpacing.sm),
                            Expanded(
                              child: PrimaryButton(
                                label: 'Guardar cambios',
                                loadingLabel: 'Guardando…',
                                isLoading: _saving,
                                onPressed: _saving ? null : _saveProfile,
                              ),
                            ),
                          ],
                        ),
                      ],
                    ],
                  ),
                ),
              ),
              const SizedBox(height: AppSpacing.md),
              SecondaryButton(
                label: 'Cambiar contraseña',
                icon: Icons.lock_reset_rounded,
                onPressed: _openChangePassword,
              ),
              if (widget.embeddedInShell) ...[
                const SizedBox(height: AppSpacing.sm),
                SecondaryButton(
                  label: 'Cerrar sesión',
                  icon: Icons.logout_rounded,
                  onPressed: _logout,
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _SoftBadge extends StatelessWidget {
  const _SoftBadge({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.sm, vertical: AppSpacing.xxs),
      decoration: BoxDecoration(
        color: scheme.primary.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: scheme.outlineVariant.withValues(alpha: 0.65)),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelLarge?.copyWith(
              color: scheme.primary,
              fontWeight: FontWeight.w700,
            ),
      ),
    );
  }
}

class _ProfileSkeleton extends StatelessWidget {
  const _ProfileSkeleton();

  @override
  Widget build(BuildContext context) {
    final base = Theme.of(context).colorScheme.surfaceContainerHighest.withValues(alpha: 0.6);
    Widget bar(double h) => Padding(
          padding: const EdgeInsets.only(bottom: AppSpacing.sm),
          child: Container(
            height: h,
            decoration: BoxDecoration(
              color: base,
              borderRadius: BorderRadius.circular(AppSpacing.xs),
            ),
          ),
        );
    return ListView(
      padding: const EdgeInsets.all(AppSpacing.lg),
      children: [
        bar(18),
        bar(24),
        bar(48),
        bar(48),
        bar(48),
        const SizedBox(height: AppSpacing.xl),
        Center(
          child: SizedBox(
            width: 28,
            height: 28,
            child: CircularProgressIndicator(
              strokeWidth: 2,
              color: Theme.of(context).colorScheme.primary,
            ),
          ),
        ),
        const SizedBox(height: AppSpacing.sm),
        Center(
          child: Text(
            'Cargando perfil…',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
          ),
        ),
      ],
    );
  }
}
