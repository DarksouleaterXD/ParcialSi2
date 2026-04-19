import 'package:flutter/material.dart';

import '../theme/app_spacing.dart';
import '../theme/app_typography.dart';

/// Live checklist for password policy (length, letter, digit).
class PasswordRulesChecklist extends StatelessWidget {
  const PasswordRulesChecklist({super.key, required this.password});

  final String password;

  bool get _lenOk => password.length >= 8;
  bool get _letterOk => RegExp('[A-Za-z]').hasMatch(password);
  bool get _digitOk => RegExp(r'\d').hasMatch(password);

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return DecoratedBox(
      decoration: BoxDecoration(
        color: scheme.surfaceContainerHighest.withValues(alpha: 0.35),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: scheme.outlineVariant.withValues(alpha: 0.65)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              'Requisitos de la nueva contraseña',
              style: AppTextStyles.subtitle(context).copyWith(fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: AppSpacing.sm),
            _RuleRow(
              label: 'Al menos 8 caracteres',
              ok: _lenOk,
            ),
            const SizedBox(height: AppSpacing.xs),
            _RuleRow(
              label: 'Incluye al menos una letra',
              ok: _letterOk,
            ),
            const SizedBox(height: AppSpacing.xs),
            _RuleRow(
              label: 'Incluye al menos un número',
              ok: _digitOk,
            ),
          ],
        ),
      ),
    );
  }
}

class _RuleRow extends StatelessWidget {
  const _RuleRow({required this.label, required this.ok});

  final String label;
  final bool ok;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final icon = ok ? Icons.check_circle_rounded : Icons.radio_button_unchecked_rounded;
    final iconColor = ok ? scheme.primary : scheme.outline;
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, size: 20, color: iconColor),
        const SizedBox(width: AppSpacing.xs),
        Expanded(
          child: Text(
            label,
            style: AppTextStyles.caption(context).copyWith(
              fontWeight: FontWeight.w600,
              height: 1.35,
              color: ok ? scheme.onSurface : scheme.onSurfaceVariant,
            ),
          ),
        ),
      ],
    );
  }
}
