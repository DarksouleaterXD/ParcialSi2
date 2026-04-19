import 'package:flutter/material.dart';

import 'app_text_field.dart';

/// Phone entry with consistent icon and keyboard.
class AppPhoneField extends StatelessWidget {
  const AppPhoneField({
    super.key,
    required this.controller,
    required this.label,
    this.helperText,
    this.validator,
    this.readOnly = false,
    this.enabled = true,
    this.autovalidateMode = AutovalidateMode.onUserInteraction,
    this.onChanged,
  });

  final TextEditingController controller;
  final String label;
  final String? helperText;
  final FormFieldValidator<String>? validator;
  final bool readOnly;
  final bool enabled;
  final AutovalidateMode autovalidateMode;
  final ValueChanged<String>? onChanged;

  @override
  Widget build(BuildContext context) {
    return AppTextField(
      controller: controller,
      label: label,
      helperText: helperText,
      keyboardType: TextInputType.phone,
      prefixIcon: Icons.phone_outlined,
      readOnly: readOnly,
      enabled: enabled,
      autovalidateMode: autovalidateMode,
      validator: validator,
      onChanged: onChanged,
    );
  }
}
