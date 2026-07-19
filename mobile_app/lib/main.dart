import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:google_fonts/google_fonts.dart';

import 'core/constants.dart';
import 'logic/app_state.dart';
import 'presentation/screens/onboarding_screen.dart';
import 'presentation/screens/dashboard_screen.dart';
import 'presentation/screens/chat_screen.dart';
import 'presentation/screens/reminders_screen.dart';
import 'presentation/screens/workouts_screen.dart';
import 'presentation/screens/settings_screen.dart';

import 'package:firebase_core/firebase_core.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp();
  runApp(
    ChangeNotifierProvider(
      create: (_) => AppState(),
      child: const BlumetaraApp(),
    ),
  );
}

class BlumetaraApp extends StatelessWidget {
  const BlumetaraApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Blumetara AI',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        brightness: Brightness.light,
        scaffoldBackgroundColor: AppConstants.primaryDark,
        primaryColor: AppConstants.accentMint,
        colorScheme: ColorScheme.light(
          primary: AppConstants.accentMint,
          secondary: AppConstants.primaryGreenDark,
          background: AppConstants.primaryDark,
        ),
        textTheme: GoogleFonts.outfitTextTheme(
          ThemeData.light().textTheme.apply(
                bodyColor: AppConstants.textWhite,
                displayColor: AppConstants.textWhite,
              ),
        ),
        cardTheme: CardTheme(
          color: AppConstants.primaryGreenDark,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppConstants.defaultRadius),
            side: BorderSide(
              color: AppConstants.accentMint.withOpacity(0.2),
              width: 1,
            ),
          ),
        ),
      ),
      home: Consumer<AppState>(
        builder: (context, state, _) {
          if (!state.isAuthenticated) {
            return const OnboardingScreen();
          }
          // If authenticated but profile details are not configured (default is 'User' or empty), force demographic onboarding
          if (state.profile == null || state.profile!.name == 'User' || state.profile!.name.trim().isEmpty) {
            return const OnboardingScreen(startAtProfileStep: true);
          }
          return const NavigationContainer();
        },
      ),
    );
  }
}

class NavigationContainer extends StatefulWidget {
  const NavigationContainer({super.key});

  @override
  State<NavigationContainer> createState() => _NavigationContainerState();
}

class _NavigationContainerState extends State<NavigationContainer> {
  int _currentIndex = 0;

  final List<Widget> _screens = [
    const DashboardScreen(),
    const ChatScreen(),
    const RemindersScreen(),
    const WorkoutsScreen(),
    const SettingsScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: AppConstants.appBackgroundGradient,
        ),
        child: SafeArea(
          child: _screens[_currentIndex],
        ),
      ),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _currentIndex,
        onTap: (index) {
          setState(() {
            _currentIndex = index;
          });
        },
        type: BottomNavigationBarType.fixed,
        backgroundColor: AppConstants.primaryDark,
        selectedItemColor: AppConstants.accentMint,
        unselectedItemColor: AppConstants.textGray,
        items: const [
          BottomNavigationBarItem(
            icon: Icon(Icons.dashboard_outlined),
            activeIcon: Icon(Icons.dashboard),
            label: 'Dashboard',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.chat_bubble_outline),
            activeIcon: Icon(Icons.chat_bubble),
            label: 'TARA Chat',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.alarm_on_outlined),
            activeIcon: Icon(Icons.alarm_on),
            label: 'Reminders',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.fitness_center_outlined),
            activeIcon: Icon(Icons.fitness_center),
            label: 'Workouts',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.settings_outlined),
            activeIcon: Icon(Icons.settings),
            label: 'Settings',
          ),
        ],
      ),
    );
  }
}
