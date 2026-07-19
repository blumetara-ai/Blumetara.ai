#!/bin/zsh

# =====================================================================
# Developer helper script to run Blumetara Web Target safely.
# Avoids permission errors inside root-owned .config directories.
# =====================================================================

export XDG_CONFIG_HOME="$HOME/development/config"

echo "🚀 Booting Blumetara App on Chrome..."
flutter run -d chrome
