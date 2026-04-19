import 'dart:math' as math;
import 'dart:ui' as ui;

import 'package:flutter/material.dart';

import '../../../core/app_colors.dart';

/// Abstract mark for the mobile app (distinct from the web login artwork).
class _MobileAppMarkPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final w = size.width;
    final h = size.height;
    final p = Path()
      ..moveTo(0, h * 0.85)
      ..quadraticBezierTo(w * 0.35, h * 0.35, w * 0.72, h * 0.55)
      ..quadraticBezierTo(w * 0.92, h * 0.65, w, h * 0.25)
      ..lineTo(w, h)
      ..lineTo(0, h)
      ..close();

    final paint = Paint()
      ..shader = ui.Gradient.linear(
        Offset(0, h * 0.3),
        Offset(w, h),
        const [AppColors.orange400, AppColors.orange500],
      );
    canvas.drawPath(p, paint);

    canvas.drawCircle(
      Offset(w * 0.22, h * 0.42),
      math.min(w, h) * 0.09,
      Paint()..color = Colors.white.withValues(alpha: 0.22),
    );
    canvas.drawCircle(
      Offset(w * 0.78, h * 0.38),
      math.min(w, h) * 0.06,
      Paint()..color = Colors.white.withValues(alpha: 0.18),
    );
  }

  @override
  bool shouldRepaint(covariant _MobileAppMarkPainter oldDelegate) => false;
}

/// Compact mobile-first header (own layout + palette, not the web split hero).
class MobileLoginHeader extends StatelessWidget {
  const MobileLoginHeader({super.key});

  static const _ink = Color(0xFF0C2D48);
  static const _inkDeep = Color(0xFF061824);

  @override
  Widget build(BuildContext context) {
    final primary = Theme.of(context).colorScheme.primary;
    return Material(
      color: Colors.transparent,
      child: Container(
        width: double.infinity,
        constraints: const BoxConstraints(minHeight: 128),
        decoration: const BoxDecoration(
          borderRadius: BorderRadius.vertical(bottom: Radius.circular(28)),
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [_ink, _inkDeep],
          ),
        ),
        child: Stack(
          clipBehavior: Clip.none,
          children: [
            Positioned(
              right: -16,
              top: -8,
              width: 170,
              height: 110,
              child: Opacity(
                opacity: 0.32,
                child: CustomPaint(painter: _MobileAppMarkPainter()),
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 20, 20, 22),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  DecoratedBox(
                    decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(18),
                      border: Border.all(color: Colors.white24),
                    ),
                    child: const Padding(
                      padding: EdgeInsets.all(14),
                      child: Icon(Icons.support_agent_rounded, color: Color(0xFFFFEDD5), size: 30),
                    ),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisAlignment: MainAxisAlignment.center,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          'Emergencias',
                          style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                                color: Colors.white,
                                fontWeight: FontWeight.w800,
                                letterSpacing: -0.6,
                              ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          'App móvil · asistencia en ruta',
                          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                color: const Color(0xFF94A3B8),
                                fontWeight: FontWeight.w500,
                              ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            Positioned(
              left: 20,
              right: 20,
              bottom: 0,
              height: 3,
              child: DecoratedBox(
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(2),
                  gradient: LinearGradient(
                    colors: [primary, primary.withValues(alpha: 0.45)],
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
