#!/usr/bin/env python3
"""Main entry point for Nokia N900 Flasher GUI."""

import os
import signal
import sys

# Ensure local package import works
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import gi

try:
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk
except (ValueError, ImportError) as e:
    sys.stderr.write(
        f"Error: GTK 3 (PyGObject) is not available ({e}).\n"
        "Please run 'sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0' to install it.\n"
    )
    sys.exit(1)

from n900_flasher.gui import N900FlasherWindow


def main():
    # Handle Ctrl+C gracefully
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Check for X11 / Wayland display
    if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        sys.stderr.write(
            "Error: No graphical display detected ($DISPLAY or $WAYLAND_DISPLAY is not set).\n"
            "This application requires a Linux desktop environment (X11 or Wayland).\n"
        )
        sys.exit(1)

    win = N900FlasherWindow()
    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
