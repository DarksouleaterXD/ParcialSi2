import 'package:flutter/material.dart';

/// Semantic aliases over [ThemeData.textTheme] (values tuned in [AppTheme]).
abstract final class AppTextStyles {
  static TextStyle title(BuildContext context) => Theme.of(context).textTheme.titleLarge!;

  static TextStyle subtitle(BuildContext context) => Theme.of(context).textTheme.titleMedium!;

  /// Section titles inside forms and cards (e.g. "Datos personales").
  static TextStyle sectionTitle(BuildContext context) =>
      Theme.of(context).textTheme.titleMedium!.copyWith(
            fontWeight: FontWeight.w800,
            letterSpacing: -0.2,
          );

  static TextStyle body(BuildContext context) => Theme.of(context).textTheme.bodyLarge!;

  static TextStyle bodyMedium(BuildContext context) => Theme.of(context).textTheme.bodyMedium!;

  static TextStyle caption(BuildContext context) => Theme.of(context).textTheme.bodySmall!;
}
