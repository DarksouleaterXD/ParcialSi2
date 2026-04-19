import 'package:flutter/material.dart';

/// Accent oranges aligned with Tailwind on `frontend_talleres_web` (`orange-400` … `orange-600`).
abstract final class AppColors {
  /// `orange-300` — highlights, soft fills.
  static const orange300 = Color(0xFFFDBA74);

  /// `orange-400` — primary accent (clearer / less “brown” than seeding from `orange-500` alone in M3).
  static const orange400 = Color(0xFFFB923C);

  /// `orange-500` — same as web CTAs (`bg-orange-500`).
  static const orange500 = Color(0xFFF97316);

  /// `orange-600` — hover / pressed on web (`hover:bg-orange-600`).
  static const orange600 = Color(0xFFEA580C);
}
