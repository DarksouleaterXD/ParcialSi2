import 'package:flutter/material.dart';

import '../../../core/auth_api.dart';
import '../../../core/auth_storage.dart';
import 'login_screen.dart';

/// Best-effort [POST /auth/logout] with Bearer token, always clears [AuthStorage], then shows [LoginScreen] as the only route.
///
/// Uses [rootNavigator] so this works from tabs, nested navigators, and modal sheets.
Future<void> logoutAndNavigateToLogin({
  required BuildContext context,
  required AuthStorage storage,
  required AuthApi authApi,
}) async {
  final token = await storage.readToken();
  try {
    if (token != null && token.isNotEmpty) {
      await authApi.logout(token);
    }
  } finally {
    await storage.clear();
  }
  if (!context.mounted) {
    return;
  }
  Navigator.of(context, rootNavigator: true).pushAndRemoveUntil(
    MaterialPageRoute<void>(
      builder: (_) => LoginScreen(storage: storage, api: authApi),
    ),
    (_) => false,
  );
}

/// After [AuthorizedClient] cleared storage on 401, replace the stack with login.
void navigateToLoginReplacingStack({
  required BuildContext context,
  required AuthStorage storage,
  required AuthApi authApi,
}) {
  Navigator.of(context, rootNavigator: true).pushAndRemoveUntil(
    MaterialPageRoute<void>(
      builder: (_) => LoginScreen(storage: storage, api: authApi),
    ),
    (_) => false,
  );
}
