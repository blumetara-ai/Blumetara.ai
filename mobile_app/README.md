# Blumetara AI - Flutter Mobile App

This directory contains the source code for the Blumetara patient co-pilot application.

## Getting Started

1. Ensure the Flutter SDK is installed and added to your environment path.
2. In this folder, restore project dependencies:
   ```bash
   flutter pub get
   ```
3. Run the development target:
   * **Chrome Web**: `flutter run -d chrome`
   * **macOS Desktop**: `flutter run -d macos`
   * **Mobile Emulator**: `flutter run`

## Environment Configuration
API endpoints can be toggled by passing compile-time variables:
* **Development**: defaults to `http://localhost:8000/api/v1`
* **Production**: `flutter run --dart-define=isProduction=true`

## Features
* **Firebase Authentication Client**: Integrated with mock login overrides for swift local evaluations.
* **Light Theme Style**: Implemented to support clean branded color palettes.
* **Interactive Dials & Modal Progress Logger**: Logs user statistics dynamically.
