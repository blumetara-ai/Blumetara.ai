import 'package:flutter/material.dart';

class AppConstants {
  // API Config
  static const String apiBaseUrl = "http://localhost:8000/api/v1";

  // Visual Theme Colors
  static const Color primaryDark = Color(0xFF0B0E0C);
  static const Color primaryGreenDark = Color(0xFF1E392A);
  static const Color accentMint = Color(0xFF4EAD73);
  static const Color textWhite = Color(0xFFF4F6F4);
  static const Color textGray = Color(0xFFA0A5A0);
  static const Color errorRed = Color(0xFFCF6679);

  // Layout Padding
  static const double defaultPadding = 16.0;
  static const double defaultRadius = 12.0;

  // Linear Gradient background for high-fidelity look
  static const Gradient appBackgroundGradient = LinearGradient(
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
    colors: [
      Color(0xFF0B0E0C),
      Color(0xFF152219),
    ],
  );
}
