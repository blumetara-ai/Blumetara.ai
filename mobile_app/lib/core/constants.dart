import 'package:flutter/material.dart';

class AppConstants {
  // API Config
  static const bool isProduction = bool.fromEnvironment('isProduction', defaultValue: false);
  static const String apiBaseUrl = isProduction 
      ? "https://api.blumetara.ai/api/v1" 
      : "http://localhost:8000/api/v1";

  // Visual Theme Colors (Light Theme - Blumetara Mint)
  static const Color primaryDark = Color(0xFFFFFFFF); // White background
  static const Color primaryGreenDark = Color(0xFFF0F7F3); // Soft mint green card surface
  static const Color accentMint = Color(0xFF4EAD73); // Blumetara Logo Mint Green
  static const Color textWhite = Color(0xFF1C211D); // Dark gray body text
  static const Color textGray = Color(0xFF6B726D); // Muted gray secondary text
  static const Color errorRed = Color(0xFFBA1A1A); // Darker red for light-mode visibility

  // Layout Padding
  static const double defaultPadding = 16.0;
  static const double defaultRadius = 12.0;

  // Linear Gradient background for high-fidelity look
  static const Gradient appBackgroundGradient = LinearGradient(
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
    colors: [
      Color(0xFFFFFFFF),
      Color(0xFFE8F3ED), // Fades to a very soft light-mint green
    ],
  );
}
