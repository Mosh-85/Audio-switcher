#!/usr/bin/env bash
# Installs the app, menu entry and Plasma widget for the current user.
set -euo pipefail
cd "$(dirname "$0")"

python3 -m pip install --user --upgrade .
install -Dm644 data/audio-switcher.desktop "$HOME/.local/share/applications/audio-switcher.desktop"
kpackagetool6 --type Plasma/Applet --install plasmoid/org.audioswitcher.widget 2>/dev/null \
  || kpackagetool6 --type Plasma/Applet --upgrade plasmoid/org.audioswitcher.widget

echo "Done. Make sure ~/.local/bin is in PATH, run 'audio-switcher', and add the"
echo "'Audio Switcher' widget via Edit Mode > Add Widgets."
