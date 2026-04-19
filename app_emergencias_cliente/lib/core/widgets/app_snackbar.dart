import 'package:flutter/material.dart';

/// Consistent floating snackbars (success / error / info) using the app theme.
abstract final class AppSnackBar {
  static void success(BuildContext context, String message) {
    final s = Theme.of(context).colorScheme;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        behavior: SnackBarBehavior.floating,
        content: Text(
          message,
          style: TextStyle(color: s.onPrimaryContainer, fontWeight: FontWeight.w600),
        ),
        backgroundColor: s.primaryContainer,
      ),
    );
  }

  static void error(BuildContext context, String message) {
    final s = Theme.of(context).colorScheme;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        behavior: SnackBarBehavior.floating,
        content: Text(
          message,
          style: TextStyle(color: s.onErrorContainer, fontWeight: FontWeight.w600),
        ),
        backgroundColor: s.errorContainer,
      ),
    );
  }

  static void info(BuildContext context, String message) {
    final s = Theme.of(context).colorScheme;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        behavior: SnackBarBehavior.floating,
        content: Text(
          message,
          style: TextStyle(color: s.onInverseSurface, fontWeight: FontWeight.w600),
        ),
        backgroundColor: s.inverseSurface,
      ),
    );
  }
}
