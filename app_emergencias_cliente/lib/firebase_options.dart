// Reemplazá este archivo con la salida de: `dart run flutterfire configure`
// (mismo proyecto y app Android con package com.example.app_emergencias_cliente)
//
// Mientras tengas valores de ejemplo, FCM no entregará mensajes reales hasta
// sincronizar con [android/app/google-services.json].

import 'package:firebase_core/firebase_core.dart' show FirebaseOptions;
import 'package:flutter/foundation.dart' show defaultTargetPlatform, kIsWeb, TargetPlatform;

/// [FirebaseOptions] for use with [FirebaseCore.initializeApp].
class DefaultFirebaseOptions {
  static FirebaseOptions get currentPlatform {
    if (kIsWeb) {
      throw UnsupportedError('FCM: web no soportado en este proyecto.');
    }
    switch (defaultTargetPlatform) {
      case TargetPlatform.android:
        return android;
      default:
        throw UnsupportedError(
          'FCM: configurar iOS con `flutterfire configure` y añadí GoogleService-Info.plist a Runner.',
        );
    }
  }

  static const FirebaseOptions android = FirebaseOptions(
    apiKey: 'REEMPLAZA_CON_TU_API_KEY',
    appId: '1:0:android:0',
    messagingSenderId: '0',
    projectId: 'reemplaza-proyecto-firebase',
    storageBucket: 'reemplaza-proyecto-firebase.firebasestorage.app',
  );
}
