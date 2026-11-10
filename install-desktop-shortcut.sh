#!/bin/bash
# ==============================================================================
# Nokia N900 Flasher - Application Menu Shortcut Installer
# ==============================================================================
# Installs a desktop launcher into ~/.local/share/applications/ so the app appears
# in your Linux system application menu / launcher.
# ==============================================================================

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="${HOME}/.local/share/applications"
TARGET_FILE="${TARGET_DIR}/nokia-n900-flasher.desktop"

mkdir -p "${TARGET_DIR}"

cat > "${TARGET_FILE}" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Nokia N900 Flasher
GenericName=Nokia N900 Flasher
Comment=Standalone Portable Flasher for Nokia N900 (Maemo 5)
Exec="${DIR}/N900-Flasher"
Icon="${DIR}/n900_flasher/assets/n900-flasher.svg"
Path=${DIR}
Terminal=false
Categories=Utility;System;Development;
Keywords=nokia;n900;maemo;flasher;fiasco;emmc;rx-51;
StartupNotify=true
EOF

chmod +x "${TARGET_FILE}"
chmod +x "${DIR}/N900-Flasher"
chmod +x "${DIR}/start.sh"

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "${TARGET_DIR}" 2>/dev/null || true
fi

echo "✔ Desktop shortcut successfully installed!"
echo "  Location: ${TARGET_FILE}"
echo "  'Nokia N900 Flasher' is now available in your Application Menu."
