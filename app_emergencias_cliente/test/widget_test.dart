import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:app_emergencias_cliente/main.dart';

void main() {
  testWidgets('EmergenciasApp builds', (WidgetTester tester) async {
    await tester.pumpWidget(const EmergenciasApp());
    await tester.pump();
    expect(find.byType(MaterialApp), findsOneWidget);
  });
}
