import 'dart:io';

import 'package:app_emergencias_cliente/features/incidentes_servicios/offline/pending_incidents_store.dart';
import 'package:app_emergencias_cliente/main.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hive/hive.dart';

void main() {
  Directory? hiveDir;

  setUpAll(() async {
    TestWidgetsFlutterBinding.ensureInitialized();
    hiveDir = Directory.systemTemp.createTempSync('emergencias_hive_test');
    Hive.init(hiveDir!.path);
    await Hive.openBox<String>(kPendingIncidentsHiveBox);
  });

  tearDownAll(() async {
    await Hive.close();
    if (hiveDir != null && hiveDir!.existsSync()) {
      hiveDir!.deleteSync(recursive: true);
    }
  });

  testWidgets('EmergenciasApp builds', (WidgetTester tester) async {
    await tester.pumpWidget(const EmergenciasApp());
    await tester.pump();
    expect(find.byType(MaterialApp), findsOneWidget);
  });
}
