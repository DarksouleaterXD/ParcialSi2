import 'package:flutter/material.dart';

import '../theme/app_spacing.dart';

/// Shared [TextFormField] styling: spacing, radii, helper/error lines, prefix/suffix hit targets.
class AppTextField extends StatelessWidget {
  const AppTextField({
    super.key,
    required this.controller,
    required this.label,
    this.helperText,
    this.hintText,
    this.validator,
    this.keyboardType,
    this.textCapitalization = TextCapitalization.none,
    this.obscureText = false,
    this.maxLines = 1,
    this.minLines,
    this.readOnly = false,
    this.enabled = true,
    this.autovalidateMode = AutovalidateMode.onUserInteraction,
    this.prefixIcon,
    this.suffix,
    this.onChanged,
    this.textInputAction,
    this.onFieldSubmitted,
    this.autocorrect = true,
    this.enableSuggestions = true,
  });

  /// Minimum touch target for prefix/suffix controls (accessibility).
  static const formIconConstraints = BoxConstraints(minWidth: 48, minHeight: 48);

  final TextEditingController controller;
  final String label;
  final String? helperText;
  final String? hintText;
  final FormFieldValidator<String>? validator;
  final TextInputType? keyboardType;
  final TextCapitalization textCapitalization;
  final bool obscureText;
  final int? maxLines;
  final int? minLines;
  final bool readOnly;
  final bool enabled;
  final AutovalidateMode autovalidateMode;
  final IconData? prefixIcon;
  final Widget? suffix;
  final ValueChanged<String>? onChanged;
  final TextInputAction? textInputAction;
  final ValueChanged<String>? onFieldSubmitted;
  final bool autocorrect;
  final bool enableSuggestions;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final base = theme.inputDecorationTheme;

    final decoration = InputDecoration(
      labelText: label,
      hintText: hintText,
      helperText: helperText,
      helperMaxLines: 3,
      errorMaxLines: 3,
      floatingLabelBehavior: FloatingLabelBehavior.auto,
      alignLabelWithHint: (maxLines ?? 1) > 1,
      contentPadding: const EdgeInsets.symmetric(horizontal: AppSpacing.md, vertical: AppSpacing.md),
      prefixIcon: prefixIcon == null
          ? null
          : Icon(
              prefixIcon,
              size: 22,
              color: enabled ? theme.colorScheme.onSurfaceVariant : theme.colorScheme.onSurfaceVariant.withValues(alpha: 0.45),
            ),
      prefixIconConstraints: prefixIcon == null ? null : formIconConstraints,
      suffixIcon: suffix == null
          ? null
          : Align(
              widthFactor: 1,
              heightFactor: 1,
              child: suffix,
            ),
      suffixIconConstraints: suffix == null ? null : formIconConstraints,
    ).applyDefaults(base);

    return TextFormField(
      controller: controller,
      enabled: enabled,
      readOnly: readOnly,
      obscureText: obscureText,
      autocorrect: autocorrect,
      enableSuggestions: enableSuggestions,
      keyboardType: keyboardType,
      textCapitalization: textCapitalization,
      maxLines: maxLines,
      minLines: minLines,
      autovalidateMode: autovalidateMode,
      validator: validator,
      onChanged: onChanged,
      textInputAction: textInputAction,
      onFieldSubmitted: onFieldSubmitted,
      style: theme.textTheme.bodyLarge?.copyWith(
        color: enabled ? null : theme.colorScheme.onSurface.withValues(alpha: 0.45),
      ),
      decoration: decoration,
    );
  }
}
