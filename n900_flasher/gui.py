"""GTK3 Graphical User Interface for Nokia N900 Flasher."""

import os
import sys
import threading
from typing import Dict, List, Optional, Tuple

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GLib, Gtk, Pango

from .device_monitor import DeviceMonitorThread, get_connected_n900
from .flasher_backend import (
    FlasherCommandBuilder,
    FlasherTask,
    check_flasher_environment,
    find_flasher_binary,
    install_udev_rule_via_pkexec,
)


class N900FlasherWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="N900 Flasher")
        self.set_default_size(940, 740)
        self.set_position(Gtk.WindowPosition.CENTER)

        # Set application icon if available
        self._setup_icon()

        # State
        self.emmc_path: Optional[str] = None
        self.firmware_path: Optional[str] = None
        self.current_task: Optional[FlasherTask] = None
        self.builder = FlasherCommandBuilder()

        # UI Setup
        self._init_styles()
        self._build_ui()

        # Start Device Monitor
        self.device_monitor = DeviceMonitorThread(self._on_device_state_changed, poll_interval=1.5)
        self.device_monitor.start()

        # Initial checks
        env_info = check_flasher_environment()
        # In portable zero-install mode without udev rule, default to pkexec
        if not env_info.get("has_udev_rule", False):
            self.chk_pkexec.set_active(True)

        self._refresh_health_status()
        self._update_action_buttons()

        self.connect("destroy", self._on_window_close)

    def _setup_icon(self):
        icon_path = os.path.join(os.path.dirname(__file__), "assets", "n900-flasher.svg")
        if os.path.exists(icon_path):
            try:
                self.set_icon_from_file(icon_path)
            except Exception:
                pass

    def _init_styles(self):
        # Prefer dark theme in GTK system settings
        settings = Gtk.Settings.get_default()
        if settings:
            settings.set_property("gtk-application-prefer-dark-theme", True)

        css = b"""
        window {
            background-color: #10141d;
            color: #d1d5db;
            font-size: 13px;
        }
        notebook, notebook > stack {
            background-color: #10141d;
        }
        notebook > header {
            background-color: #161c28;
            border-bottom: 1px solid #2a3447;
        }
        notebook > header > tabs > tab {
            background-color: transparent;
            color: #94a3b8;
            padding: 8px 18px;
            font-weight: bold;
            font-size: 13px;
            border-radius: 2px 2px 0 0;
            border: none;
        }
        notebook > header > tabs > tab:checked {
            background-color: #10141d;
            color: #38bdf8;
            border-top: 2px solid #38bdf8;
            border-bottom: none;
        }
        entry {
            background-color: #090d14;
            color: #f8fafc;
            border: 1px solid #2c384d;
            border-radius: 2px;
            padding: 6px 10px;
            font-size: 13px;
        }
        entry:focus {
            border-color: #0284c7;
        }
        button {
            background-color: #1c2331;
            color: #e2e8f0;
            border: 1px solid #36445a;
            border-radius: 2px;
            padding: 6px 14px;
            font-weight: bold;
            font-size: 13px;
        }
        button:hover {
            background-color: #263145;
            border-color: #4a5d7c;
        }
        button:active {
            background-color: #131923;
        }
        button:disabled {
            opacity: 0.40;
        }
        .title-label {
            font-size: 21px;
            font-weight: bold;
            color: #f8fafc;
            letter-spacing: 0.5px;
        }
        .subtitle-label {
            font-size: 13px;
            color: #94a3b8;
        }
        .status-badge-ready {
            background-color: #064e3b;
            color: #34d399;
            font-weight: bold;
            padding: 5px 12px;
            border-radius: 2px;
            border: 1px solid #059669;
            font-size: 13px;
            font-family: monospace;
        }
        .status-badge-wait {
            background-color: #1f242e;
            color: #cbd5e1;
            font-weight: bold;
            padding: 5px 12px;
            border-radius: 2px;
            border: 1px solid #364153;
            font-size: 13px;
            font-family: monospace;
        }
        .status-badge-warn {
            background-color: #451a03;
            color: #fb923c;
            font-weight: bold;
            padding: 5px 12px;
            border-radius: 2px;
            border: 1px solid #b45309;
            font-size: 13px;
            font-family: monospace;
        }
        .card-box {
            background-color: #151a24;
            border: 1px solid #283347;
            border-radius: 2px;
            padding: 8px 12px;
            margin-bottom: 5px;
        }
        .panel-box {
            background-color: #131822;
            border: 1px solid #283449;
            border-radius: 2px;
            padding: 8px 12px;
            margin-bottom: 5px;
        }
        .card-title {
            font-weight: bold;
            font-size: 13px;
            color: #e2e8f0;
            letter-spacing: 0.3px;
        }
        .card-desc {
            font-size: 12px;
            color: #8b9bb4;
        }
        .btn-emmc {
            background-color: #b45309;
            color: #ffffff;
            font-weight: bold;
            border: 1px solid #d97706;
            border-radius: 2px;
            padding: 6px 14px;
            font-size: 13px;
        }
        .btn-emmc:hover {
            background-color: #d97706;
        }
        .btn-firmware {
            background-color: #0369a1;
            color: #ffffff;
            font-weight: bold;
            border: 1px solid #0284c7;
            border-radius: 2px;
            padding: 6px 14px;
            font-size: 13px;
        }
        .btn-firmware:hover {
            background-color: #0284c7;
        }
        .btn-full {
            background-color: #047857;
            color: #ffffff;
            font-weight: bold;
            font-size: 14px;
            padding: 8px 18px;
            border: 1px solid #10b981;
            border-radius: 2px;
        }
        .btn-full:hover {
            background-color: #059669;
        }
        .btn-dead {
            background-color: #991b1b;
            color: #ffffff;
            font-weight: bold;
            font-size: 14px;
            padding: 8px 18px;
            border: 1px solid #ef4444;
            border-radius: 2px;
        }
        .btn-dead:hover {
            background-color: #b91c1c;
        }
        .btn-stop {
            background-color: #7f1d1d;
            color: #ffffff;
            font-weight: bold;
            border: 1px solid #dc2626;
            border-radius: 2px;
            font-size: 13px;
        }
        .btn-stop:hover {
            background-color: #991b1b;
        }
        .console-view,
        textview.console-view,
        textview.console-view text {
            background-color: #05070c;
            color: #22c55e;
            font-family: 'JetBrains Mono', 'Fira Code', 'DejaVu Sans Mono', 'Ubuntu Mono', monospace;
            font-size: 13px;
            font-weight: 500;
        }
        textview.console-view selection {
            background-color: #14532d;
            color: #86efac;
        }
        progressbar trough {
            background-color: #0a0e16;
            border: 1px solid #283347;
            border-radius: 2px;
            min-height: 22px;
        }
        progressbar progress {
            background-color: #22c55e;
            border-radius: 1px;
        }
        progressbar text {
            color: #ffffff;
            font-weight: bold;
            font-size: 12px;
        }
        checkbutton check {
            background-color: #090d14;
            border: 1px solid #3b4961;
            border-radius: 1px;
            min-width: 16px;
            min-height: 16px;
        }
        checkbutton label {
            font-size: 13px;
        }
        check:checked, checkbutton:checked check {
            background-color: #0284c7;
            border-color: #38bdf8;
        }
        """
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _build_ui(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        vbox.set_margin_start(14)
        vbox.set_margin_end(14)
        vbox.set_margin_top(10)
        vbox.set_margin_bottom(10)
        self.add(vbox)

        # Header Bar with Title and Device Status
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        vbox.pack_start(header_box, False, False, 0)

        title_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        lbl_title = Gtk.Label(label="N900 Flasher", xalign=0)
        lbl_title.get_style_context().add_class("title-label")
        lbl_sub = Gtk.Label(label="Maemo 5 / Fremantle Flashing Utility for Linux", xalign=0)
        lbl_sub.get_style_context().add_class("subtitle-label")
        title_vbox.pack_start(lbl_title, False, False, 0)
        title_vbox.pack_start(lbl_sub, False, False, 0)
        header_box.pack_start(title_vbox, True, True, 0)

        # Device Status Badge
        self.status_badge = Gtk.Label(label="⚪ Scanning for Nokia N900...")
        self.status_badge.get_style_context().add_class("status-badge-wait")
        header_box.pack_end(self.status_badge, False, False, 0)

        # Notebook (Tabs)
        self.notebook = Gtk.Notebook()
        vbox.pack_start(self.notebook, True, True, 0)

        # Tab 1: Flasher Main Page
        tab_flash = self._build_flasher_tab()
        self.notebook.append_page(tab_flash, Gtk.Label(label="⚡ Flasher"))

        # Tab 2: Diagnostic Tools
        tab_tools = self._build_tools_tab()
        self.notebook.append_page(tab_tools, Gtk.Label(label="🛠 Tools"))

        # Tab 3: Guide / Instructions
        tab_guide = self._build_guide_tab()
        self.notebook.append_page(tab_guide, Gtk.Label(label="📖 Guide"))

        # Tab 4: Flasher Compatibility & Library Check
        tab_env = self._build_env_tab()
        self.notebook.append_page(tab_env, Gtk.Label(label="🔍 Flasher Compatibility"))

    def _build_flasher_tab(self) -> Gtk.Widget:
        main_tab_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)

        paned = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)
        paned.set_position(330)

        # Top Controls: File Selection & Flash Actions
        # Narrower margins make the boxes centered and clean
        top_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        top_box.set_margin_start(20)
        top_box.set_margin_end(20)
        top_box.set_margin_top(4)
        top_box.set_margin_bottom(2)

        # Size groups for perfect column alignment of buttons
        browse_group = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)
        flash_btn_group = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)

        # --- Section 1: eMMC File Selection ---
        emmc_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        emmc_card.get_style_context().add_class("card-box")

        emmc_hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        emmc_title = Gtk.Label(label="1. eMMC Image (Internal Storage / MyDocs)", xalign=0)
        emmc_title.get_style_context().add_class("card-title")
        emmc_hdr.pack_start(emmc_title, True, True, 0)
        emmc_card.pack_start(emmc_hdr, False, False, 0)

        emmc_file_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.txt_emmc = Gtk.Entry()
        self.txt_emmc.set_placeholder_text("Select eMMC image (e.g. RX-51_...VANILLA_PR_EMMC_MR0_ARM.bin)...")
        self.txt_emmc.set_hexpand(True)
        self.txt_emmc.connect("changed", self._on_emmc_text_changed)

        btn_browse_emmc = Gtk.Button(label="Browse...")
        btn_browse_emmc.connect("clicked", self._on_browse_emmc)
        browse_group.add_widget(btn_browse_emmc)

        self.btn_flash_emmc = Gtk.Button(label="Flash eMMC Only")
        self.btn_flash_emmc.get_style_context().add_class("btn-emmc")
        self.btn_flash_emmc.connect("clicked", self._on_flash_emmc_clicked)
        flash_btn_group.add_widget(self.btn_flash_emmc)

        emmc_file_row.pack_start(self.txt_emmc, True, True, 0)
        emmc_file_row.pack_start(btn_browse_emmc, False, False, 0)
        emmc_file_row.pack_start(self.btn_flash_emmc, False, False, 0)
        emmc_card.pack_start(emmc_file_row, False, False, 0)

        emmc_desc = Gtk.Label(
            label="Command: flasher-3.5 -F <file> -f  |  Formats internal storage. Does NOT reboot.",
            xalign=0,
        )
        emmc_desc.get_style_context().add_class("card-desc")
        emmc_card.pack_start(emmc_desc, False, False, 0)
        top_box.pack_start(emmc_card, False, False, 0)

        # --- Section 2: Firmware File Selection ---
        fw_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        fw_card.get_style_context().add_class("card-box")

        fw_hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        fw_title = Gtk.Label(label="2. FIASCO Firmware Image (RootFS / Kernel / OS)", xalign=0)
        fw_title.get_style_context().add_class("card-title")
        fw_hdr.pack_start(fw_title, True, True, 0)
        fw_card.pack_start(fw_hdr, False, False, 0)

        fw_file_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.txt_fw = Gtk.Entry()
        self.txt_fw.set_placeholder_text("Select Firmware image (e.g. RX-51_...COMBINED_MR0_ARM.bin)...")
        self.txt_fw.set_hexpand(True)
        self.txt_fw.connect("changed", self._on_fw_text_changed)

        btn_browse_fw = Gtk.Button(label="Browse...")
        btn_browse_fw.connect("clicked", self._on_browse_firmware)
        browse_group.add_widget(btn_browse_fw)

        self.btn_flash_fw = Gtk.Button(label="Flash Firmware Only")
        self.btn_flash_fw.get_style_context().add_class("btn-firmware")
        self.btn_flash_fw.connect("clicked", self._on_flash_fw_clicked)
        flash_btn_group.add_widget(self.btn_flash_fw)

        fw_file_row.pack_start(self.txt_fw, True, True, 0)
        fw_file_row.pack_start(btn_browse_fw, False, False, 0)
        fw_file_row.pack_start(self.btn_flash_fw, False, False, 0)
        fw_card.pack_start(fw_file_row, False, False, 0)

        fw_desc = Gtk.Label(
            label="Command: flasher-3.5 -F <file> -f -R  |  Flashes OS firmware. Automatically reboots device.",
            xalign=0,
        )
        fw_desc.get_style_context().add_class("card-desc")
        fw_card.pack_start(fw_desc, False, False, 0)
        top_box.pack_start(fw_card, False, False, 0)

        # --- Section 3: Combined 1-Click Flash & Options Bar ---
        action_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        action_bar.set_margin_top(2)

        self.btn_flash_both = Gtk.Button(label="⚡ Flash Both Together (eMMC + Firmware)")
        self.btn_flash_both.get_style_context().add_class("btn-full")
        self.btn_flash_both.connect("clicked", self._on_flash_both_clicked)
        action_bar.pack_start(self.btn_flash_both, True, True, 0)

        self.btn_cancel = Gtk.Button(label="⛔ Stop")
        self.btn_cancel.set_sensitive(False)
        self.btn_cancel.set_size_request(95, -1)
        self.btn_cancel.get_style_context().add_class("btn-stop")
        self.btn_cancel.connect("clicked", self._on_cancel_clicked)
        action_bar.pack_start(self.btn_cancel, False, False, 0)
        top_box.pack_start(action_bar, False, False, 0)

        # --- Flashing Modes & USB Settings Panel (Infinity BEST Style) ---
        settings_frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        settings_frame.get_style_context().add_class("panel-box")

        settings_hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lbl_settings = Gtk.Label(label="⚙ FLASHING MODES & USB PERMISSIONS", xalign=0)
        lbl_settings.get_style_context().add_class("card-title")
        settings_hdr.pack_start(lbl_settings, True, True, 0)
        settings_frame.pack_start(settings_hdr, False, False, 0)

        # Row 1: Dead Mode & HW Rev & Password-Free USB & Root Privileges
        row1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        self.chk_dead_mode = Gtk.CheckButton(label="☠ Dead Mode (Cold Flash)")
        self.chk_dead_mode.set_tooltip_text(
            "Check this if your N900 is bricked, does not boot, and does not respond to holding 'U'.\n"
            "Uses OMAP3430 silicon BootROM peripheral boot (-c -S usb) to revive dead hardware."
        )
        self.chk_dead_mode.connect("toggled", self._on_dead_mode_toggled)
        row1.pack_start(self.chk_dead_mode, False, False, 0)

        self.lbl_hw_rev = Gtk.Label(label="HW Rev:", xalign=0)
        self.lbl_hw_rev.get_style_context().add_class("card-desc")
        self.lbl_hw_rev.set_sensitive(False)
        row1.pack_start(self.lbl_hw_rev, False, False, 0)

        self.cmb_hw_rev = Gtk.ComboBoxText()
        self.cmb_hw_rev.append("RX-51:2202", "RX-51:2202 (Retail 2201-2216 - Default)")
        self.cmb_hw_rev.append("RX-51:2120", "RX-51:2120 (Retail 2120, 2217-2220)")
        self.cmb_hw_rev.append("RX-51:2301", "RX-51:2301 (Retail 2301-2306)")
        self.cmb_hw_rev.append("RX-51:2307", "RX-51:2307 (Retail 2307-2310)")
        self.cmb_hw_rev.append("RX-51:2401", "RX-51:2401 (Retail 2401-2406)")
        self.cmb_hw_rev.append("RX-51:2407", "RX-51:2407 (Retail 2407-2410)")
        self.cmb_hw_rev.append("RX-51:2501", "RX-51:2501 (Retail 2501-2506)")
        self.cmb_hw_rev.append("RX-51:2507", "RX-51:2507 (Retail 2507-2510)")
        self.cmb_hw_rev.append("RX-51:2601", "RX-51:2601 (Retail 2601-2606)")
        self.cmb_hw_rev.append("RX-51:2607", "RX-51:2607 (Retail 2607-2610)")
        self.cmb_hw_rev.append("RX-51:2101", "RX-51:2101 (Proto 2101-2103)")
        self.cmb_hw_rev.append("RX-51:2104", "RX-51:2104 (Proto 2104-2119)")
        self.cmb_hw_rev.set_active_id("RX-51:2202")
        self.cmb_hw_rev.set_sensitive(False)
        self.cmb_hw_rev.set_tooltip_text(
            "Hardware revision printed under battery (e.g. 2202).\n"
            "Cold Flash requires knowing the HW revision to load the matching secondary bootloader."
        )
        row1.pack_start(self.cmb_hw_rev, False, False, 0)

        self.btn_install_rule = Gtk.Button(label="🔑 Enable Password-Free USB")
        self.btn_install_rule.set_tooltip_text("Install udev rule (one-time pkexec prompt) so flashing never requires root password")
        self.btn_install_rule.connect("clicked", self._on_install_rule_clicked)
        row1.pack_start(self.btn_install_rule, False, False, 0)

        self.lbl_rule_result = Gtk.Label(label="", xalign=0)
        self.lbl_rule_result.get_style_context().add_class("card-desc")
        row1.pack_start(self.lbl_rule_result, True, True, 0)

        self.chk_pkexec = Gtk.CheckButton(label="Root privileges (pkexec)")
        self.chk_pkexec.set_active(False)
        self.chk_pkexec.set_tooltip_text(
            "Force pkexec elevation if udev rules are not active"
        )
        row1.pack_end(self.chk_pkexec, False, False, 0)
        settings_frame.pack_start(row1, False, False, 0)

        # Row 2: Sequence Order & Battery Reset Auto-continue
        row2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        lbl_order = Gtk.Label(label="Sequence Order:", xalign=0)
        lbl_order.get_style_context().add_class("card-desc")
        row2.pack_start(lbl_order, False, False, 0)

        self.cmb_order = Gtk.ComboBoxText()
        self.cmb_order.append("emmc_first", "1. eMMC First  ➔  2. Firmware (Recommended)")
        self.cmb_order.append("fw_first", "1. Firmware First  ➔  2. eMMC")
        self.cmb_order.set_active(0)
        row2.pack_start(self.cmb_order, False, False, 0)

        self.chk_reconnect_pause = Gtk.CheckButton(label="Auto-continue after battery reset (Hold 'U')")
        self.chk_reconnect_pause.set_active(True)
        self.chk_reconnect_pause.set_tooltip_text(
            "Recommended for full flash: Pauses after eMMC and automatically starts Firmware flashing the moment you reconnect holding 'U'."
        )
        row2.pack_start(self.chk_reconnect_pause, False, False, 0)
        settings_frame.pack_start(row2, False, False, 0)

        top_box.pack_start(settings_frame, False, False, 0)

        paned.pack1(top_box, resize=False, shrink=False)

        # Bottom Area: Live Console Terminal
        bottom_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        bottom_box.set_margin_start(20)
        bottom_box.set_margin_end(20)
        bottom_box.set_margin_top(4)

        console_hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lbl_console = Gtk.Label(label="Live Flasher Terminal Output", xalign=0)
        lbl_console.get_style_context().add_class("card-title")
        console_hdr.pack_start(lbl_console, True, True, 0)

        btn_copy_log = Gtk.Button(label="Copy Log")
        btn_copy_log.connect("clicked", self._on_copy_log_clicked)
        console_hdr.pack_end(btn_copy_log, False, False, 0)

        btn_clear_log = Gtk.Button(label="Clear")
        btn_clear_log.connect("clicked", self._on_clear_log_clicked)
        console_hdr.pack_end(btn_clear_log, False, False, 0)

        bottom_box.pack_start(console_hdr, False, False, 0)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_hexpand(True)
        scrolled.set_vexpand(True)

        self.text_view = Gtk.TextView()
        self.text_view.set_editable(False)
        self.text_view.set_wrap_mode(Gtk.WrapMode.CHAR)
        self.text_view.get_style_context().add_class("console-view")
        self.text_buffer = self.text_view.get_buffer()

        scrolled.add(self.text_view)
        bottom_box.pack_start(scrolled, True, True, 0)

        paned.pack2(bottom_box, resize=True, shrink=False)
        main_tab_box.pack_start(paned, True, True, 0)

        # Permanent Progress Bar at the bottom of the app
        progress_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        progress_box.set_margin_start(20)
        progress_box.set_margin_end(20)
        progress_box.set_margin_top(4)
        progress_box.set_margin_bottom(6)

        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_fraction(0.0)
        self.progress_bar.set_show_text(True)
        self.progress_bar.set_text("Idle")
        progress_box.pack_start(self.progress_bar, False, False, 0)

        main_tab_box.pack_start(progress_box, False, False, 0)

        return main_tab_box

    def _build_tools_tab(self) -> Gtk.Widget:
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        vbox.set_margin_start(16)
        vbox.set_margin_end(16)
        vbox.set_margin_top(16)
        vbox.set_margin_bottom(16)

        desc = Gtk.Label(
            label="Direct hardware utilities using flasher-3.5 on the connected Nokia N900:",
            xalign=0,
        )
        vbox.pack_start(desc, False, False, 0)

        # Tool 1: Read Device ID
        t1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        b1 = Gtk.Button(label="Read Device ID (-i)")
        b1.connect("clicked", lambda w: self._run_single_command("Read Device ID", self.builder.build_read_id(self.chk_pkexec.get_active())))
        t1.pack_start(b1, False, False, 0)
        t1.pack_start(Gtk.Label(label="Queries and prints device hardware type, revision, and bootrom state.", xalign=0), True, True, 0)
        vbox.pack_start(t1, False, False, 0)

        # Tool 2: Reboot Device
        t2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        b2 = Gtk.Button(label="Reboot Device (-R)")
        b2.connect("clicked", lambda w: self._run_single_command("Reboot Device", self.builder.build_reboot(self.chk_pkexec.get_active())))
        t2.pack_start(b2, False, False, 0)
        t2.pack_start(Gtk.Label(label="Safely reboots the Nokia N900 out of flash mode into normal operation.", xalign=0), True, True, 0)
        vbox.pack_start(t2, False, False, 0)

        # Tool 3: R&D Mode toggles
        t3 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        b3_on = Gtk.Button(label="Enable R&D Mode")
        b3_on.connect("clicked", lambda w: self._run_single_command("Enable R&D Mode", self.builder.build_rd_mode(True, self.chk_pkexec.get_active())))
        b3_off = Gtk.Button(label="Disable R&D Mode")
        b3_off.connect("clicked", lambda w: self._run_single_command("Disable R&D Mode", self.builder.build_rd_mode(False, self.chk_pkexec.get_active())))
        t3.pack_start(b3_on, False, False, 0)
        t3.pack_start(b3_off, False, False, 0)
        t3.pack_start(Gtk.Label(label="Enable/Disable Research & Development mode on N900.", xalign=0), True, True, 0)
        vbox.pack_start(t3, False, False, 0)

        # Tool 4: Unpack FIASCO
        t4 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        b4 = Gtk.Button(label="Unpack FIASCO Image...")
        b4.connect("clicked", self._on_unpack_clicked)
        t4.pack_start(b4, False, False, 0)
        t4.pack_start(Gtk.Label(label="Extracts kernel, initfs, and rootfs components from a FIASCO image.", xalign=0), True, True, 0)
        vbox.pack_start(t4, False, False, 0)

        return vbox

    def _build_guide_tab(self) -> Gtk.Widget:
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        vbox.set_margin_start(20)
        vbox.set_margin_end(20)
        vbox.set_margin_top(16)
        vbox.set_margin_bottom(16)

        steps = [
            ("Step 1: Turn off the phone", "Power off your Nokia N900 completely. Ensure the battery has at least 50% charge."),
            ("Step 2: Open keyboard & hold 'U'", "Slide open the physical keyboard. Press and hold down the 'U' key on the keyboard."),
            ("Step 3: Connect USB Cable", "While continuing to hold down the 'U' key, plug the USB cable from your PC into the N900."),
            ("Step 4: Confirm Flash Mode", "Keep holding 'U' until a dim Nokia logo with a small USB icon appears in the top-right corner of the phone's screen. Then release 'U'."),
            ("Step 5: Flash", "The status badge in this app will show green 'Nokia N900 (Flash / NOLO Mode)'. Select your image file(s) and press Flash!"),
        ]

        for title, text in steps:
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            card.get_style_context().add_class("card-box")
            lbl_title = Gtk.Label(label=title, xalign=0)
            lbl_title.get_style_context().add_class("card-title")
            lbl_text = Gtk.Label(label=text, xalign=0)
            lbl_text.set_line_wrap(True)
            card.pack_start(lbl_title, False, False, 0)
            card.pack_start(lbl_text, False, False, 0)
            vbox.pack_start(card, False, False, 0)

        # Flashing advice
        advice_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        advice_card.get_style_context().add_class("card-box")
        lbl_adv_title = Gtk.Label(label="💡 Important Advice for Clean Factory Reset:", xalign=0)
        lbl_adv_title.get_style_context().add_class("card-title")
        advice_text = (
            "• If doing a complete clean flash, use 'Flash Both Together'. It flashes eMMC first, "
            "then automatically pauses and prompts you to power-cycle the battery (pull battery, replace, hold 'U' and plug USB) "
            "before flashing Firmware with reboot. This ensures 100% of the FIASCO image writes properly.\n"
            "• On the first boot after eMMC flashing, the N900 will spend a couple of minutes formatting and setting up /home/opt. Be patient!"
        )
        lbl_adv = Gtk.Label(label=advice_text, xalign=0)
        lbl_adv.set_line_wrap(True)
        advice_card.pack_start(lbl_adv_title, False, False, 0)
        advice_card.pack_start(lbl_adv, False, False, 0)
        vbox.pack_start(advice_card, False, False, 0)

        scrolled.add(vbox)
        return scrolled

    def _build_env_tab(self) -> Gtk.Widget:
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        vbox.set_margin_start(16)
        vbox.set_margin_end(16)
        vbox.set_margin_top(16)
        vbox.set_margin_bottom(16)

        self.lbl_env_status = Gtk.Label(label="Checking flasher compatibility and libraries...", xalign=0)
        self.lbl_env_status.set_line_wrap(True)
        vbox.pack_start(self.lbl_env_status, False, False, 0)

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        btn_refresh = Gtk.Button(label="Re-check Compatibility & Libraries")
        btn_refresh.connect("clicked", lambda w: self._refresh_health_status())
        btn_box.pack_start(btn_refresh, False, False, 0)

        btn_install_rule_env = Gtk.Button(label="Enable Password-Free USB (Install Udev Rule)")
        btn_install_rule_env.set_tooltip_text("Copies udev rule using pkexec so flashing never asks for root password")
        btn_install_rule_env.connect("clicked", self._on_install_rule_clicked)
        btn_box.pack_start(btn_install_rule_env, False, False, 0)

        vbox.pack_start(btn_box, False, False, 0)
        return vbox

    def _on_install_rule_clicked(self, widget):
        self.lbl_rule_result.set_text("Installing udev rules via pkexec...")
        ok, msg = install_udev_rule_via_pkexec()
        if ok:
            self.lbl_rule_result.set_markup("<span color='#4ade80'>✔ " + GLib.markup_escape_text(msg) + "</span>")
            self.chk_pkexec.set_active(False)
            self.btn_install_rule.set_label("✔ Password-Free USB (Active)")
        else:
            self.lbl_rule_result.set_markup("<span color='#f87171'>❌ " + GLib.markup_escape_text(msg) + "</span>")
        self._refresh_health_status()

    # --- File Picking Callbacks ---

    def _on_browse_emmc(self, widget):
        path = self._select_file_dialog("Select eMMC Image", "RX-51*EMMC*.bin;RX-51*VANILLA*.bin;*.bin")
        if path:
            self.txt_emmc.set_text(path)

    def _on_browse_firmware(self, widget):
        path = self._select_file_dialog("Select FIASCO Firmware Image", "RX-51*COMBINED*.bin;*.bin;*.fiasco")
        if path:
            self.txt_fw.set_text(path)

    def _select_file_dialog(self, title: str, pattern: str) -> Optional[str]:
        dialog = Gtk.FileChooserDialog(
            title=title,
            parent=self,
            action=Gtk.FileChooserAction.OPEN,
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL,
            Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN,
            Gtk.ResponseType.OK,
        )

        filter_bin = Gtk.FileFilter()
        filter_bin.set_name(f"Firmware Images ({pattern})")
        for p in pattern.split(";"):
            filter_bin.add_pattern(p)
            filter_bin.add_pattern(p.lower())
        dialog.add_filter(filter_bin)

        filter_all = Gtk.FileFilter()
        filter_all.set_name("All Files (*)")
        filter_all.add_pattern("*")
        dialog.add_filter(filter_all)

        response = dialog.run()
        selected_file = None
        if response == Gtk.ResponseType.OK:
            selected_file = dialog.get_filename()
        dialog.destroy()
        return selected_file

    def _on_emmc_text_changed(self, entry):
        text = entry.get_text().strip()
        self.emmc_path = text if (text and os.path.isfile(text)) else None
        self._update_action_buttons()

    def _on_fw_text_changed(self, entry):
        text = entry.get_text().strip()
        self.firmware_path = text if (text and os.path.isfile(text)) else None
        self._update_action_buttons()

    def _on_dead_mode_toggled(self, widget):
        is_dead = self.chk_dead_mode.get_active()
        if hasattr(self, "cmb_hw_rev"):
            self.cmb_hw_rev.set_sensitive(is_dead)
        if hasattr(self, "lbl_hw_rev"):
            self.lbl_hw_rev.set_sensitive(is_dead)
        self._update_action_buttons()
        if is_dead:
            selected_hw = (self.cmb_hw_rev.get_active_id() if hasattr(self, "cmb_hw_rev") else None) or "RX-51:2202"
            self._append_log("\n" + "=" * 60 + "\n")
            self._append_log("☠ DEAD MODE (Cold Flash Recovery) ACTIVATED.\n")
            self._append_log(f"• Target HW Revision: {selected_hw}\n")
            self._append_log("• Select FIASCO Firmware image (e.g. RX-51...COMBINED...bin)\n")
            self._append_log("• Click 'Flash Dead Phone' to initiate emergency cold boot recovery.\n")
            self._append_log("• Follow the on-screen timing: Unplug -> Click Flash -> Plug USB -> Insert battery.\n")
            self._append_log("=" * 60 + "\n\n")

    def _update_action_buttons(self):
        is_flashing = self.current_task is not None
        dead_mode = getattr(self, "chk_dead_mode", None) and self.chk_dead_mode.get_active()

        if is_flashing:
            self.btn_flash_emmc.set_sensitive(False)
            self.btn_flash_fw.set_sensitive(False)
            self.btn_flash_both.set_sensitive(False)
            self.btn_cancel.set_sensitive(True)
        else:
            self.btn_cancel.set_sensitive(False)
            if dead_mode:
                has_fw = bool(self.firmware_path)
                self.btn_flash_emmc.set_sensitive(False)
                self.btn_flash_fw.set_sensitive(has_fw)
                self.btn_flash_both.set_sensitive(has_fw)
                self.btn_flash_both.set_label("☠ Flash Dead Phone (Cold Flash)")
                self.btn_flash_both.get_style_context().remove_class("btn-full")
                self.btn_flash_both.get_style_context().add_class("btn-dead")
            else:
                self.btn_flash_emmc.set_sensitive(bool(self.emmc_path))
                self.btn_flash_fw.set_sensitive(bool(self.firmware_path))
                self.btn_flash_both.set_sensitive(bool(self.emmc_path and self.firmware_path))
                self.btn_flash_both.set_label("⚡ Flash Both Together (eMMC + Firmware)")
                self.btn_flash_both.get_style_context().remove_class("btn-dead")
                self.btn_flash_both.get_style_context().add_class("btn-full")

    # --- Flashing Execution Callbacks ---

    def _start_cold_flash_flow(self):
        if not self.firmware_path:
            return

        hw_rev = (self.cmb_hw_rev.get_active_id() if hasattr(self, "cmb_hw_rev") else None) or "RX-51:2202"

        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.NONE,
            text="☠ Confirm Dead Mode Recovery (Cold Flash)",
        )
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        btn_proceed = dialog.add_button("Proceed with Cold Flash", Gtk.ResponseType.OK)
        btn_proceed.get_style_context().add_class("btn-dead")

        msg = (
            f"You are initiating a <b>Cold Flash hardware recovery</b> for an unresponsive Nokia N900:\n\n"
            f"• <b>FIASCO Firmware:</b> {os.path.basename(self.firmware_path)}\n"
            f"• <b>Target HW Revision:</b> <code>{hw_rev}</code>\n\n"
            f"<b>CRITICAL HARDWARE TIMING PROCEDURE:</b>\n"
            f"  1. <b>UNPLUG</b> the USB cable and <b>REMOVE THE BATTERY</b> now.\n"
            f"  2. Click <b>'Proceed with Cold Flash'</b> below.\n"
            f"  3. Once the flasher terminal displays <i>'Waiting for USB device...'</i>:\n"
            f"     • <b>Plug the USB cable</b> into the PC and N900.\n"
            f"     • <b>Immediately insert the battery</b> into the N900.\n\n"
            f"The flasher will intercept the TI OMAP3430 silicon BootROM and restore the bootloader."
        )
        dialog.format_secondary_markup(msg)
        response = dialog.run()
        dialog.destroy()

        if response != Gtk.ResponseType.OK:
            return

        use_pkexec = self.chk_pkexec.get_active()
        cmd = self.builder.build_cold_flash(self.firmware_path, reboot=True, use_pkexec=use_pkexec, hw_revision=hw_rev)
        self._run_flasher_sequence([("Cold Flash Recovery (Dead Phone)", cmd)])

    def _on_flash_emmc_clicked(self, widget):
        if not self.emmc_path:
            return
        use_pkexec = self.chk_pkexec.get_active()
        cmd = self.builder.build_emmc(self.emmc_path, use_pkexec)
        self._run_flasher_sequence([("Flash eMMC Only", cmd)])

    def _on_flash_fw_clicked(self, widget):
        if self.chk_dead_mode.get_active():
            self._start_cold_flash_flow()
            return
        if not self.firmware_path:
            return
        use_pkexec = self.chk_pkexec.get_active()
        cmd = self.builder.build_firmware(self.firmware_path, use_pkexec)
        self._run_flasher_sequence([("Flash Firmware Only", cmd)])

    def _on_flash_both_clicked(self, widget):
        if self.chk_dead_mode.get_active():
            self._start_cold_flash_flow()
            return
        if not self.emmc_path or not self.firmware_path:
            return
            return

        order = self.cmb_order.get_active_id() or "emmc_first"
        order_text = (
            "1. Flash eMMC (No Reboot)  ➔  2. Flash Firmware (With Reboot)"
            if order == "emmc_first"
            else "1. Flash Firmware (No Reboot)  ➔  2. Flash eMMC (With Reboot)"
        )

        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.NONE,
            text="Confirm Full Device Flash",
        )
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        btn_proceed = dialog.add_button("Proceed with Full Flash", Gtk.ResponseType.OK)
        btn_proceed.get_style_context().add_class("btn-full")

        msg = (
            f"You are about to flash both images to your Nokia N900:\n\n"
            f"• <b>eMMC Image:</b> {os.path.basename(self.emmc_path)}\n"
            f"• <b>Firmware Image:</b> {os.path.basename(self.firmware_path)}\n\n"
            f"<b>Sequence Order:</b> {order_text}\n\n"
            f"⚠️ <b>WARNING:</b> This will completely repartition and erase all internal user data!\n\n"
            f"Ensure your Nokia N900 battery is above 50%.\n"
            f"<i>Note: The app will pause after the first step and guide you to reset the battery and hold 'U' before flashing the second image.</i>"
        )
        dialog.format_secondary_markup(msg)
        response = dialog.run()
        dialog.destroy()

        if response != Gtk.ResponseType.OK:
            return

        use_pkexec = self.chk_pkexec.get_active()

        if order == "emmc_first":
            cmd_1 = self.builder.build_emmc(self.emmc_path, reboot=False, use_pkexec=use_pkexec)
            cmd_2 = self.builder.build_firmware(self.firmware_path, reboot=True, use_pkexec=use_pkexec)
            steps = [
                ("1. Flash eMMC Storage (No Reboot)", cmd_1),
                ("2. Flash OS Firmware (With Reboot)", cmd_2),
            ]
        else:
            cmd_1 = self.builder.build_firmware(self.firmware_path, reboot=False, use_pkexec=use_pkexec)
            cmd_2 = self.builder.build_emmc(self.emmc_path, reboot=True, use_pkexec=use_pkexec)
            steps = [
                ("1. Flash OS Firmware (No Reboot)", cmd_1),
                ("2. Flash eMMC Storage (With Reboot)", cmd_2),
            ]

        self._run_flasher_sequence(steps)

    def _run_single_command(self, title: str, cmd: List[str]):
        self._run_flasher_sequence([(title, cmd)])

    def _on_unpack_clicked(self, widget):
        path = self._select_file_dialog("Select FIASCO file to unpack", "*.bin;*.fiasco")
        if not path:
            return
        cmd = self.builder.build_unpack(path, use_pkexec=self.chk_pkexec.get_active())
        self._run_flasher_sequence([(f"Unpack FIASCO: {os.path.basename(path)}", cmd)])

    def _run_flasher_sequence(self, commands: List[Tuple[str, List[str]]]):
        if self.current_task:
            return

        self._append_log("\n" + "=" * 60 + "\n")
        self._append_log(f"Starting execution: {len(commands)} step(s)\n")

        self.progress_bar.set_fraction(0.0)
        self.progress_bar.set_text("Starting...")

        self.current_task = FlasherTask(
            commands=commands,
            on_line=lambda line: GLib.idle_add(self._append_log, line + "\n"),
            on_step_change=lambda cur, tot, title: GLib.idle_add(self._on_step_progress, cur, tot, title),
            on_complete=lambda success, msg: GLib.idle_add(self._on_task_finished, success, msg),
            on_step_finished=self._handle_step_finished,
        )
        self._update_action_buttons()
        self.current_task.start()

    def _handle_step_finished(self, step_idx: int, total_steps: int, title: str) -> bool:
        if not self.chk_reconnect_pause.get_active():
            return True

        event = threading.Event()
        result = [False]

        # Query initial USB state right as step 1 finishes
        initial_dev = get_connected_n900()
        initial_devnum = initial_dev.get("devnum") if initial_dev.get("connected") else None

        def _show_dialog():
            self.progress_bar.set_fraction(0.5)
            self.progress_bar.set_text("⏸ Waiting for USB connection (Hold 'U')...")

            self._append_log("\n" + "*" * 60 + "\n")
            self._append_log(f"⏸ Step {step_idx}/{total_steps} finished successfully.\n")
            self._append_log("Re-insert the battery, then re-insert the USB cable holding 'U'.\n")
            self._append_log("Waiting for USB connection to start firmware flashing...\n")
            self._append_log("*" * 60 + "\n\n")

            dialog = Gtk.Dialog(
                title="Prepare Nokia N900 for Firmware Flash",
                parent=self,
                flags=Gtk.DialogFlags.MODAL,
            )
            dialog.set_default_size(480, -1)
            dialog.set_border_width(18)

            content_area = dialog.get_content_area()
            content_area.set_spacing(16)

            lbl_title = Gtk.Label(xalign=0)
            lbl_title.set_markup(
                f"<span size='large' weight='bold' color='#38bdf8'>Step {step_idx} Completed Successfully!</span>"
            )
            content_area.pack_start(lbl_title, False, False, 0)

            lbl_instructions = Gtk.Label(xalign=0)
            lbl_instructions.set_line_wrap(True)
            lbl_instructions.set_markup(
                "<b>Please prepare your Nokia N900:</b>\n\n"
                "  1. <b>Re-insert the battery</b> (unplug USB, pull out &amp; re-insert battery).\n"
                "  2. <b>Re-insert the USB cable</b> while holding down the <b>'U' key</b>.\n\n"
                "Flashing will begin automatically once connected."
            )
            content_area.pack_start(lbl_instructions, False, False, 0)

            # Prominent Waiting Loading Sign
            status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            status_box.get_style_context().add_class("card-box")
            status_box.set_margin_top(4)
            status_box.set_margin_bottom(4)

            spinner = Gtk.Spinner()
            spinner.set_size_request(24, 24)
            spinner.start()
            status_box.pack_start(spinner, False, False, 0)

            lbl_status = Gtk.Label(xalign=0)
            lbl_status.set_line_wrap(True)
            lbl_status.set_markup(
                "<span color='#38bdf8' size='medium'><b>Waiting for USB connection...</b></span>"
            )
            status_box.pack_start(lbl_status, True, True, 0)
            content_area.pack_start(status_box, False, False, 0)

            # Only Cancel Sequence button - no manual submit button
            dialog.add_button("Cancel Sequence", Gtk.ResponseType.CANCEL)

            dialog.show_all()

            seen_disconnect = not initial_dev.get("connected", False)
            auto_triggered = [False]
            timer_id = [None]

            def _poll_device():
                if auto_triggered[0]:
                    timer_id[0] = None
                    return False

                current = get_connected_n900()
                is_connected = current.get("connected", False)
                cur_devnum = current.get("devnum")
                is_flash = current.get("is_flash_mode", False)

                nonlocal seen_disconnect
                if not is_connected:
                    seen_disconnect = True
                    lbl_status.set_markup(
                        "<span color='#38bdf8' size='medium'><b>Waiting for USB connection...</b>\n<small>(Hold 'U' and connect USB)</small></span>"
                    )
                    return True

                is_fresh = seen_disconnect or (initial_devnum and cur_devnum != initial_devnum)

                if is_fresh and is_flash:
                    auto_triggered[0] = True
                    timer_id[0] = None
                    spinner.stop()
                    lbl_status.set_markup(
                        "<span color='#4ade80' size='medium'><b>⚡ Nokia N900 (Flash Mode) detected!</b>\nStarting firmware flash automatically...</span>"
                    )
                    self._append_log("⚡ Fresh Nokia N900 Flash Mode detected! Starting firmware flash automatically...\n")
                    GLib.timeout_add(1000, lambda: dialog.response(Gtk.ResponseType.OK))
                    return False

                elif not is_fresh and is_flash:
                    lbl_status.set_markup(
                        "<span color='#fbbf24'><b>⚠️ Please unplug USB &amp; re-insert battery</b>...</span>"
                    )
                elif is_connected and not is_flash:
                    lbl_status.set_markup(
                        f"<span color='#f87171'><b>⚠️ Wrong mode ({current.get('description')}).</b>\nPlease re-insert battery, hold 'U', and plug in USB.</span>"
                    )

                return True

            _poll_device()
            timer_id[0] = GLib.timeout_add(400, _poll_device)

            resp = dialog.run()
            if timer_id[0]:
                GLib.source_remove(timer_id[0])
                timer_id[0] = None
            dialog.destroy()

            result[0] = (resp == Gtk.ResponseType.OK)
            event.set()

        GLib.idle_add(_show_dialog)
        event.wait()
        return result[0]

    def _on_step_progress(self, current: int, total: int, title: str):
        if total == 2:
            fraction = 0.25 if current == 1 else 0.75
            stage_name = "eMMC Storage" if "eMMC" in title else "OS Firmware"
            self.progress_bar.set_fraction(fraction)
            self.progress_bar.set_text(f"Step {current} of 2 [{stage_name}]: {title}...")
        else:
            fraction = float(current - 1) / float(total)
            self.progress_bar.set_fraction(fraction)
            self.progress_bar.set_text(f"Step {current}/{total}: {title}")

    def _on_task_finished(self, success: bool, message: str):
        self.current_task = None
        self._update_action_buttons()
        if success:
            self.progress_bar.set_fraction(1.0)
            self.progress_bar.set_text("✔ 100% Completed! Nokia N900 is rebooting safely.")
        else:
            self.progress_bar.set_text("❌ Failed or Cancelled")
            # If failed with permission error hint, suggest root privilege
            buffer_text = self.text_buffer.get_text(
                self.text_buffer.get_start_iter(),
                self.text_buffer.get_end_iter(),
                False,
            )
            if "Suitable USB device not found" in buffer_text or "permission" in buffer_text.lower():
                self._append_log("\n[TIP] If you get a USB permission error, make sure the Nokia N900 is in Flash Mode (holding 'U') or enable the 'Root privileges (pkexec)' checkbox!\n")

    def _on_cancel_clicked(self, widget):
        if self.current_task:
            self.current_task.cancel()
            self._append_log("\n[!] Cancelling current operation...\n")

    def _on_clear_log_clicked(self, widget):
        self.text_buffer.set_text("")

    def _on_copy_log_clicked(self, widget):
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        text = self.text_buffer.get_text(
            self.text_buffer.get_start_iter(),
            self.text_buffer.get_end_iter(),
            False,
        )
        clipboard.set_text(text, -1)

    def _append_log(self, text: str):
        end_iter = self.text_buffer.get_end_iter()
        self.text_buffer.insert(end_iter, text)
        # Auto-scroll to end
        adj = self.text_view.get_vadjustment()
        adj.set_value(adj.get_upper())

    # --- Device & Health Monitoring ---

    def _on_device_state_changed(self, state: Dict):
        GLib.idle_add(self._update_device_badge, state)

    def _update_device_badge(self, state: Dict):
        ctx = self.status_badge.get_style_context()
        ctx.remove_class("status-badge-ready")
        ctx.remove_class("status-badge-wait")
        ctx.remove_class("status-badge-warn")

        if state.get("connected"):
            desc = state.get("description", "Nokia Device")
            if state.get("is_flash_mode"):
                self.status_badge.set_text(f"🟢 {desc} - READY")
                ctx.add_class("status-badge-ready")
            else:
                self.status_badge.set_text(f"🟡 {desc} (Not in Flash Mode)")
                ctx.add_class("status-badge-warn")
        else:
            self.status_badge.set_text("⚪ Waiting for Nokia N900 (Hold 'U' & connect USB)...")
            ctx.add_class("status-badge-wait")

    def _refresh_health_status(self):
        info = check_flasher_environment()
        lines = []
        lines.append("=== Flasher Compatibility & Library Diagnostics ===")
        if info.get("is_portable"):
            lines.append("✔ Mode: Self-Contained Portable Edition (Bundled flasher & 32-bit libraries active)")
            lines.append("  (Zero installation required on the host system!)")
        else:
            lines.append("ℹ Mode: System-installed flasher")

        if info["flasher_installed"]:
            lines.append(f"✔ Flasher executable: {info['flasher_path']}")
        else:
            lines.append("❌ Flasher-3.5 binary NOT found.")

        if info["flasher_runnable"]:
            lines.append("✔ Flasher-3.5 is runnable (32-bit execution & libusb OK)")
        else:
            lines.append(f"❌ Flasher-3.5 cannot be executed: {info['flasher_error'] or 'Missing 32-bit libraries'}")

        if info.get("is_portable"):
            lines.append("✔ Host i386 multiarch: Not required (Bundled 32-bit runtime active)")
        elif info["has_i386"]:
            lines.append("✔ i386 multiarch enabled in dpkg")
        else:
            lines.append("⚠ i386 architecture not yet added (run: sudo dpkg --add-architecture i386)")

        if info["has_udev_rule"]:
            lines.append("✔ Udev rules installed in /etc/udev/rules.d/")
            if hasattr(self, "btn_install_rule"):
                self.btn_install_rule.set_label("✔ Password-Free USB (Active)")
                self.btn_install_rule.set_tooltip_text("Udev rules installed! Flashing works without entering root password.")
            if hasattr(self, "chk_pkexec"):
                self.chk_pkexec.set_active(False)
        else:
            lines.append("⚠ No udev rules found. Flashing may require root privileges (pkexec).")
            if hasattr(self, "btn_install_rule"):
                self.btn_install_rule.set_label("🔑 Enable Password-Free USB")
                self.btn_install_rule.set_tooltip_text("Install udev rule (one-time pkexec prompt) so flashing never requires root password")

        if info["has_pkexec"]:
            lines.append("✔ pkexec available for elevation")
        else:
            lines.append("⚠ pkexec not found")

        self.lbl_env_status.set_text("\n".join(lines))

    def _on_window_close(self, widget):
        if self.device_monitor:
            self.device_monitor.stop()
        if self.current_task:
            self.current_task.cancel()
        Gtk.main_quit()
