# Nokia N900 Flasher (Portable Linux Edition)

A standalone graphical flasher application for the **Nokia N900 (RX-51 / Maemo 5 Fremantle)** on 64-bit Linux (Debian, Ubuntu, Linux Mint, and derivatives).

---

## ⚡ Quick Start

This application is **100% self-contained and portable**. It includes the official Nokia flasher binary and all necessary 32-bit execution libraries (`libusb-0.1`, `libc`, `ld-linux`) bundled directly in the folder. No system package installation is required.

### How to Launch:
* **Option 1 (Direct Execution)**: Double-click **`N900-Flasher`** directly in your file manager. It is a native executable that launches the app immediately.
* **Option 2 (Terminal)**: Run `./N900-Flasher` or `./start.sh` from this directory.

---

## 📥 Download & Install from Terminal (Git Method)

If you prefer cloning directly from GitHub without downloading the release `.tar.gz`:

### 1. Install prerequisites (Python 3 & GTK 3)
```bash
sudo apt update && sudo apt install -y git python3 python3-gi python3-gi-cairo gir1.2-gtk-3.0
```

### 2. Clone the repository
```bash
git clone https://github.com/lensmanreboot/Nokia-N900-Flasher.git
cd Nokia-N900-Flasher
```

### 3. Launch directly from terminal
```bash
./N900-Flasher
```

### 4. (Optional) Add to System Application Menu
To create a desktop shortcut so the app appears in your system Application Menu (with icon):
```bash
./install-desktop-shortcut.sh
```
> *Once run, you can press your Super/Windows key and search for **"Nokia N900 Flasher"** to launch it anytime.*

---

## 🚀 Key Features

* **Zero-Install Portable 32-bit Runtime**:
  * Bundled 32-bit dynamic linker (`lib32/ld-linux.so.2`).
  * Bundled 32-bit USB communication library (`lib32/libusb-0.1.so.4`).
  * Bundled 32-bit standard library (`lib32/libc.so.6`).
  * Runs seamlessly on modern 64-bit Linux systems without requiring `dpkg --add-architecture i386` or system-wide 32-bit packages.

* **Flashing Modes**:
  1. **Flash eMMC Only**: Writes eMMC storage (`*EMMC*.bin` or `*VANILLA*.bin`) without rebooting.
  2. **Flash Firmware Only**: Writes the FIASCO OS image (`*COMBINED*.bin` or `*FIASCO*.bin`) and reboots the device.
  3. **Flash Both Together (Full Clean Reset)**: Flashes eMMC first, automatically pauses with guided prompts to reset the battery (re-entering NOLO mode with `U`), and then flashes Firmware with auto-reboot.
  4. **☠ Dead Mode (Cold Flash Recovery)**: Revives hard-bricked N900 units that cannot boot or do not respond to holding the `U` key. Uses OMAP3430 silicon BootROM peripheral boot (`-c -S usb -h <HW_REV>`) with selectable hardware revisions (`RX-51:2202`, `2120`, `2301`, `2401`, `2501`, `2601`, etc.).

* **Nokia Infinity BEST Industrial UI**:
  * Sharp, high-contrast dark theme.
  * Real-time phosphor green console with an integrated bottom progress bar.
  * Live hardware detection badge (`⚪ Waiting` / `🟡 Connected` / `🟢 Ready (NOLO Flash Mode)`).

* **USB Permissions Management**:
  * Works out of the box with `pkexec` privilege elevation when needed.
  * One-click **"Enable Password-Free USB"** installs a local udev rule so flashing never prompts for a root password.

* **Diagnostic & Maintenance Tools**:
  * Query device hardware ID and versions (`flasher-3.5 -i`).
  * Reboot device into normal mode (`flasher-3.5 -R`).
  * Unpack FIASCO firmware container files (`flasher-3.5 -F <file> -u`).
  * Enable or disable R&D mode (`--enable-rd-mode` / `--disable-rd-mode`).
  * **Flasher Compatibility** tab verifying 32-bit runtime readiness, libusb presence, and USB rules.

---

## 📖 Flashing Instructions

### Normal Mode (Phone boots or responds to holding 'U'):

1. Launch **`N900-Flasher`**.
2. Power the phone completely **OFF**.
3. Slide open the physical keyboard.
4. Press and **hold the `U` key**.
5. While holding `U`, connect the USB cable between the computer and phone.
6. When the Nokia logo appears with a small USB icon in the top-right corner, release the `U` key.
7. The status badge will display **`🟢 Nokia N900 (Flash / NOLO Mode) - READY`**.
8. Select your firmware files:
   * **Full factory reset**: Select both eMMC and FIASCO firmware, then click **`⚡ Flash Both Together`**.
   * **OS update / repair only**: Select FIASCO firmware and click **`Flash Firmware Only`**.
   * **Storage reset only**: Select eMMC image and click **`Flash eMMC Only`**.

---

### Dead Mode / Cold Flash (Phone does not boot or respond to 'U'):

1. Launch **`N900-Flasher`**.
2. Under **Firmware Selection**, browse and select your FIASCO firmware image (`RX-51_..._COMBINED_...bin`).
3. Check the **`[✔] ☠ Dead Mode (Cold Flash)`** box.
4. Verify your phone's hardware revision in the **`HW Rev:`** dropdown (default is `RX-51:2202`, matching over 90% of retail units; check the sticker under your battery if uncertain).
5. Click **`☠ Flash Dead Phone (Cold Flash)`**.
6. Follow the timing wizard:
   * **Unplug USB** and **remove the battery**.
   * Click **Proceed with Cold Flash** in the confirmation prompt.
   * When the terminal shows `Suitable USB device not found, waiting.`:
     1. **Plug the USB cable** into the phone.
     2. **Immediately reinsert the battery**.
7. The flasher will intercept the TI OMAP BootROM, upload the secondary bootloader, and restore the firmware.

---

## 📁 Directory Structure

```text
Nokia-N900-Flasher/
├── N900-Flasher                  # Direct 64-bit ELF binary launcher
├── start.sh                      # Alternative shell script launcher
├── install-desktop-shortcut.sh   # Installs launcher shortcut into Linux Application Menu
├── Launch-N900-Flasher.desktop   # Desktop shortcut entry
├── bin/
│   ├── flasher-3.5               # Official Nokia flasher-3.5 binary (32-bit)
│   └── flasher-portable          # Portable runtime wrapper script
├── lib32/                        # Bundled 32-bit libraries (ld-linux, libc, libusb)
└── n900_flasher/                 # Application Python source code and assets
```
