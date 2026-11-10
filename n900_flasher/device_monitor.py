"""Device monitor for detecting Nokia N900 (RX-51) connected over USB.

Monitors /sys/bus/usb/devices for Nokia Vendor ID (0421).
Specifically distinguishes:
- 0105: N900 in NOLO Flash / Update Mode (holding 'U' during boot)
- 01c8: N900 in PC-Suite / Cold flash Mode
- Other Nokia IDs
"""

import glob
import os
import shutil
import subprocess
import threading
import time
from typing import Callable, Dict, Optional

NOKIA_VENDOR_ID = "0421"

NOKIA_MODES = {
    "0105": ("Nokia N900 (Flash / NOLO Mode)", True),
    "01c8": ("Nokia N900 (PC-Suite / Cold Flash Mode)", True),
    "01c5": ("Nokia N900 (Mass Storage Mode)", False),
    "01c6": ("Nokia N900 (PC-Suite Mode)", False),
    "01c7": ("Nokia N900 (MTP Mode)", False),
}


def read_sys_file(path: str) -> Optional[str]:
    """Safely read a single trimmed line from a sysfs file."""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read().strip().lower()
    except Exception:
        return None


def detect_n900_via_sysfs() -> Optional[Dict]:
    """Scan /sys/bus/usb/devices for connected Nokia USB devices."""
    sys_usb_path = "/sys/bus/usb/devices"
    if not os.path.exists(sys_usb_path):
        return None

    try:
        for dev_dir in glob.glob(os.path.join(sys_usb_path, "*")):
            vendor_path = os.path.join(dev_dir, "idVendor")
            product_path = os.path.join(dev_dir, "idProduct")

            if os.path.exists(vendor_path) and os.path.exists(product_path):
                vendor = read_sys_file(vendor_path)
                product = read_sys_file(product_path)

                if vendor == NOKIA_VENDOR_ID:
                    product_clean = (product or "").lower()
                    info = NOKIA_MODES.get(product_clean)
                    if info:
                        desc, is_flash = info
                    else:
                        desc = f"Nokia Device (0421:{product_clean})"
                        is_flash = (product_clean == "0105" or product_clean == "01c8")

                    devnum = read_sys_file(os.path.join(dev_dir, "devnum"))
                    busnum = read_sys_file(os.path.join(dev_dir, "busnum"))
                    return {
                        "connected": True,
                        "vendor_id": vendor,
                        "product_id": product_clean,
                        "description": desc,
                        "is_flash_mode": is_flash,
                        "sysfs_path": dev_dir,
                        "devnum": devnum,
                        "busnum": busnum,
                    }
    except Exception:
        pass

    return None


def detect_n900_via_lsusb() -> Optional[Dict]:
    """Fallback scanner using lsusb utility."""
    lsusb_bin = shutil.which("lsusb")
    if not lsusb_bin:
        return None

    try:
        res = subprocess.run([lsusb_bin, "-d", "0421:"], capture_output=True, text=True, timeout=2)
        output = res.stdout.strip()
        if output:
            for line in output.splitlines():
                parts = line.split()
                if "ID" in parts:
                    idx = parts.index("ID")
                    if idx + 1 < len(parts):
                        ids = parts[idx + 1].split(":")
                        if len(ids) == 2:
                            prod = ids[1].lower()
                            info = NOKIA_MODES.get(prod)
                            desc = info[0] if info else f"Nokia Device (0421:{prod})"
                            is_flash = info[1] if info else (prod in ("0105", "01c8"))
                            busnum = parts[1] if len(parts) > 1 else None
                            devnum = parts[3].rstrip(":") if len(parts) > 3 else None
                            return {
                                "connected": True,
                                "vendor_id": "0421",
                                "product_id": prod,
                                "description": desc,
                                "is_flash_mode": is_flash,
                                "sysfs_path": "",
                                "devnum": devnum,
                                "busnum": busnum,
                            }
    except Exception:
        pass

    return None


def get_connected_n900() -> Dict:
    """Return device connection dictionary."""
    dev = detect_n900_via_sysfs()
    if dev is None:
        dev = detect_n900_via_lsusb()

    if dev is None:
        return {
            "connected": False,
            "vendor_id": None,
            "product_id": None,
            "description": "No Nokia N900 detected",
            "is_flash_mode": False,
            "sysfs_path": "",
            "devnum": None,
            "busnum": None,
        }
    return dev


class DeviceMonitorThread:
    """Background thread polling for Nokia device state changes."""

    def __init__(self, callback: Callable[[Dict], None], poll_interval: float = 1.5):
        self.callback = callback
        self.poll_interval = poll_interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_state: Optional[Dict] = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True, name="N900DeviceMonitor")
        self._thread.start()

    def stop(self):
        self._running = False

    def _run(self):
        while self._running:
            state = get_connected_n900()
            if self._last_state is None or state != self._last_state:
                self._last_state = state
                try:
                    self.callback(state)
                except Exception:
                    pass
            time.sleep(self.poll_interval)
