import 'package:flutter/material.dart';

import '../../../core/authorized_client.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/widgets/app_password_field.dart';
import '../../../core/widgets/app_section_header.dart';
import '../../../core/widgets/app_snackbar.dart';
import '../../../core/widgets/password_rules_checklist.dart';
import '../../../core/widgets/primary_button.dart';
import '../data/profile_api.dart';

Future<void> showChangePasswordSheet(
  BuildContext context, {
  required ProfileApi profileApi,
  required VoidCallback onSessionExpired,
}) {
  return showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    showDragHandle: true,
    useSafeArea: true,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
    ),
    builder: (ctx) => Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.viewInsetsOf(ctx).bottom),
      child: _ChangePasswordSheetBody(
        profileApi: profileApi,
        onSessionExpired: () {
          Navigator.of(ctx).pop();
          onSessionExpired();
        },
      ),
    ),
  );
}

class _ChangePasswordSheetBody extends StatefulWidget {
  const _ChangePasswordSheetBody({
    required this.profileApi,
    required this.onSessionExpired,
  });

  final ProfileApi profileApi;
  final VoidCallback onSessionExpired;

  @override
  State<_ChangePasswordSheetBody> createState() => _ChangePasswordSheetBodyState();
}

class _ChangePasswordSheetBodyState extends State<_ChangePasswordSheetBody> {
  final _formKey = GlobalKey<FormState>();
  final _actual = TextEditingController();
  final _nueva = TextEditingController();
  final _confirm = TextEditingController();
  var _saving = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _nueva.addListener(_onNuevaChanged);
  }

  void _onNuevaChanged() {
    setState(() {});
  }

  @override
  void dispose() {
    _nueva.removeListener(_onNuevaChanged);
    _actual.dispose();
    _nueva.dispose();
    _confirm.dispose();
    super.dispose();
  }

  String? _policy(String? v) {
    if (v == null || v.isEmpty) {
      return 'Completá este campo.';
    }
    if (v.length < 8) {
      return 'Mínimo 8 caracteres.';
    }
    if (!RegExp(r'[A-Za-z]').hasMatch(v)) {
      return 'Incluí al menos una letra.';
    }
    if (!RegExp(r'\d').hasMatch(v)) {
      return 'Incluí al menos un número.';
    }
    return null;
  }

  Future<void> _submit() async {
    setState(() => _error = null);
    if (!(_formKey.currentState?.validate() ?? false)) {
      return;
    }
    setState(() => _saving = true);
    try {
      await widget.profileApi.changePassword(
        passwordActual: _actual.text,
        passwordNueva: _nueva.text,
        passwordConfirmacion: _confirm.text,
      );
      if (!mounted) {
        return;
      }
      AppSnackBar.success(context, 'Contraseña actualizada correctamente.');
      Navigator.of(context).pop();
    } on SessionExpiredException {
      widget.onSessionExpired();
    } on ApiClientException catch (e) {
      setState(() => _error = e.message);
    } catch (_) {
      setState(() => _error = 'No se pudo conectar con el servidor');
    } finally {
      if (mounted) {
        setState(() => _saving = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(AppSpacing.lg, AppSpacing.xs, AppSpacing.lg, AppSpacing.xl),
      child: Form(
        key: _formKey,
        autovalidateMode: AutovalidateMode.onUserInteraction,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          mainAxisSize: MainAxisSize.min,
          children: [
            const AppSectionHeader(
              title: 'Cambiar contraseña',
              subtitle: 'Elegí una contraseña fuerte y no la compartas con nadie.',
            ),
            const SizedBox(height: AppSpacing.lg),
            AppPasswordField(
              controller: _actual,
              label: 'Contraseña actual',
              textInputAction: TextInputAction.next,
              validator: (v) => (v == null || v.isEmpty) ? 'Ingresá tu contraseña actual.' : null,
            ),
            const SizedBox(height: AppSpacing.sm),
            AppPasswordField(
              controller: _nueva,
              label: 'Nueva contraseña',
              textInputAction: TextInputAction.next,
              validator: _policy,
              onChanged: (_) => setState(() {}),
            ),
            const SizedBox(height: AppSpacing.sm),
            PasswordRulesChecklist(password: _nueva.text),
            const SizedBox(height: AppSpacing.sm),
            AppPasswordField(
              controller: _confirm,
              label: 'Confirmar nueva contraseña',
              textInputAction: TextInputAction.done,
              onFieldSubmitted: (_) => _submit(),
              validator: (v) {
                final p = _policy(v);
                if (p != null) {
                  return p;
                }
                if (v != _nueva.text) {
                  return 'Las contraseñas nuevas no coinciden.';
                }
                return null;
              },
            ),
            if (_error != null) ...[
              const SizedBox(height: AppSpacing.sm),
              DecoratedBox(
                decoration: BoxDecoration(
                  color: scheme.errorContainer.withValues(alpha: 0.45),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: scheme.error.withValues(alpha: 0.25)),
                ),
                child: Padding(
                  padding: const EdgeInsets.all(AppSpacing.md),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Icon(Icons.error_outline_rounded, color: scheme.error),
                      const SizedBox(width: AppSpacing.sm),
                      Expanded(
                        child: Text(
                          _error!,
                          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                color: scheme.onErrorContainer,
                                fontWeight: FontWeight.w600,
                              ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
            const SizedBox(height: AppSpacing.lg),
            Row(
              children: [
                Expanded(
                  child: SecondaryButton(
                    label: 'Cancelar',
                    onPressed: _saving ? null : () => Navigator.of(context).pop(),
                  ),
                ),
                const SizedBox(width: AppSpacing.sm),
                Expanded(
                  child: PrimaryButton(
                    label: 'Guardar contraseña',
                    loadingLabel: 'Guardando…',
                    isLoading: _saving,
                    onPressed: _saving ? null : _submit,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
