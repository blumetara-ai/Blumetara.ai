import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import '../lib/logic/app_state.dart';
import '../lib/main.dart';
import '../lib/presentation/screens/onboarding_screen.dart';

void main() {
  testWidgets('App displays OnboardingScreen when unauthenticated', (WidgetTester tester) async {
    // Build our app and trigger a frame.
    await tester.pumpWidget(
      ChangeNotifierProvider(
        create: (_) => AppState(),
        child: const BlumetaraApp(),
      ),
    );

    // Verify Onboarding Screen is shown on startup when AppState is unauthenticated
    expect(find.text('Blumetara.ai'), findsOneWidget);
    expect(find.text('Your Premium AI Health Co-Pilot'), findsOneWidget);
    expect(find.byType(OnboardingScreen), findsOneWidget);
  });
}
