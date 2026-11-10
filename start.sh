#!/bin/bash
# ==============================================================================
# N900 Flasher - Portable Launcher (Zero-Install)
# ==============================================================================
# Runs N900 Flasher directly from this folder using bundled libraries and flasher.
# No system installation required.
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="${SCRIPT_DIR}:${PYTHONPATH}"

# Check Python 3
if ! command -v python3 >/dev/null 2>&1; then
    echo "[-] Error: Python 3 is required to run N900 Flasher."
    echo "    Please install python3 using your package manager (e.g. sudo apt install python3)."
    exit 1
fi

# Check PyGObject / GTK 3
if ! python3 -c "import gi; gi.require_version('Gtk', '3.0'); from gi.repository import Gtk" >/dev/null 2>&1; then
    echo "[-] Note: GTK 3 (PyGObject) library is missing."
    echo "    To install it, run: sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0"
    exit 1
fi

# Launch N900 Flasher GUI
exec python3 "${SCRIPT_DIR}/n900_flasher/main.py" "$@"
