"""Backend runner for executing Maemo flasher-3.5 commands.

Handles process execution, privilege elevation (pkexec), stdout/stderr streaming,
and sequential flashing workflows (eMMC followed by Firmware).
"""

import os
import shutil
import subprocess
import threading
from typing import Callable, Dict, List, Optional, Tuple


def find_flasher_binary() -> Optional[str]:
    """Find the path to the flasher-3.5 executable, prioritizing bundled portable runner."""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    candidates = [
        os.path.join(project_root, "bin", "flasher-portable"),
        os.path.join(project_root, "bin", "flasher-3.5"),
        "/opt/n900-flasher/bin/flasher-portable",
        "/opt/n900-flasher/bin/flasher-3.5",
        "/usr/local/bin/flasher-3.5",
        "/usr/bin/flasher-3.5",
        shutil.which("flasher-3.5"),
    ]
    for c in candidates:
        if c and os.path.isfile(c) and os.access(c, os.X_OK):
            return os.path.abspath(c)
    return None


def check_flasher_environment() -> Dict:
    """Diagnose the system environment for Nokia N900 flashing support."""
    flasher_path = find_flasher_binary()
    flasher_installed = flasher_path is not None
    flasher_runnable = False
    flasher_error = None
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    is_portable = bool(flasher_path and project_root in flasher_path)

    if flasher_installed:
        try:
            res = subprocess.run([flasher_path, "-h"], capture_output=True, text=True, timeout=3)
            # flasher-3.5 returns code 2 on -h with help usage text
            if "flasher v2.5.2" in res.stdout or "flasher v2.5.2" in res.stderr:
                flasher_runnable = True
            elif "Usage: flasher" in res.stdout or "Usage: flasher" in res.stderr:
                flasher_runnable = True
            else:
                flasher_runnable = True
        except Exception as e:
            flasher_error = str(e)

    # Check i386 architecture
    has_i386 = False
    try:
        res = subprocess.run(["dpkg", "--print-foreign-architectures"], capture_output=True, text=True, timeout=2)
        if "i386" in res.stdout:
            has_i386 = True
    except Exception:
        pass

    # Check udev rule
    has_udev_rule = (
        os.path.exists("/etc/udev/rules.d/70-nokia-n900.rules")
        or os.path.exists("/etc/udev/rules.d/99-nokia-n900.rules")
        or os.path.exists("/etc/udev/rules.d/70-n900-flasher.rules")
    )

    # Check pkexec
    has_pkexec = shutil.which("pkexec") is not None

    return {
        "flasher_path": flasher_path,
        "flasher_installed": flasher_installed,
        "flasher_runnable": flasher_runnable,
        "flasher_error": flasher_error,
        "is_portable": is_portable,
        "has_i386": has_i386,
        "has_udev_rule": has_udev_rule,
        "has_pkexec": has_pkexec,
    }


def install_udev_rule_via_pkexec() -> Tuple[bool, str]:
    """Install udev rule to /etc/udev/rules.d/ using pkexec (requires 1-time root password)."""
    rule_source = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "udev", "70-nokia-n900.rules")
    )
    if not os.path.isfile(rule_source):
        return False, f"Rule template not found: {rule_source}"

    target = "/etc/udev/rules.d/70-nokia-n900.rules"
    cmd = [
        "pkexec",
        "sh",
        "-c",
        f"cp '{rule_source}' '{target}' && chmod 644 '{target}' && udevadm control --reload-rules && udevadm trigger",
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if res.returncode == 0:
            return True, "Udev rules successfully installed and reloaded!"
        return False, f"Failed: {res.stderr.strip() or res.stdout.strip() or 'Cancelled by user'}"
    except Exception as e:
        return False, str(e)


class FlasherCommandBuilder:
    """Constructs command line arguments for flasher-3.5."""

    def __init__(self, binary_path: Optional[str] = None):
        self.binary_path = binary_path or find_flasher_binary() or "flasher-3.5"

    def wrap_privilege(self, cmd: List[str], use_pkexec: bool) -> List[str]:
        if use_pkexec:
            return ["pkexec"] + cmd
        return cmd

    def build_emmc(self, emmc_file: str, reboot: bool = False, use_pkexec: bool = False) -> List[str]:
        """eMMC flashing command: flasher-3.5 -F <emmc_file> -f [-R]"""
        cmd = [self.binary_path, "-F", os.path.abspath(emmc_file), "-f"]
        if reboot:
            cmd.append("-R")
        return self.wrap_privilege(cmd, use_pkexec)

    def build_firmware(self, fw_file: str, reboot: bool = True, use_pkexec: bool = False) -> List[str]:
        """Firmware flashing command: flasher-3.5 -F <fw_file> -f [-R]"""
        cmd = [self.binary_path, "-F", os.path.abspath(fw_file), "-f"]
        if reboot:
            cmd.append("-R")
        return self.wrap_privilege(cmd, use_pkexec)

    def build_cold_flash(
        self,
        fw_file: str,
        reboot: bool = True,
        use_pkexec: bool = False,
        hw_revision: str = "RX-51:2202",
    ) -> List[str]:
        """Dead Mode / Cold Flash recovery command: flasher-3.5 -c -S usb -h <hw> -F <fw_file> -f [-R]"""
        cmd = [self.binary_path, "-c", "-S", "usb", "-h", hw_revision, "-F", os.path.abspath(fw_file), "-f"]
        if reboot:
            cmd.append("-R")
        return self.wrap_privilege(cmd, use_pkexec)

    def build_read_id(self, use_pkexec: bool = False) -> List[str]:
        """Query device type: flasher-3.5 -i"""
        cmd = [self.binary_path, "-i"]
        return self.wrap_privilege(cmd, use_pkexec)

    def build_reboot(self, use_pkexec: bool = False) -> List[str]:
        """Reboot device: flasher-3.5 -R"""
        cmd = [self.binary_path, "-R"]
        return self.wrap_privilege(cmd, use_pkexec)

    def build_rd_mode(self, enable: bool = True, use_pkexec: bool = False) -> List[str]:
        """Toggle R&D mode: flasher-3.5 --enable-rd-mode / --disable-rd-mode"""
        flag = "--enable-rd-mode" if enable else "--disable-rd-mode"
        cmd = [self.binary_path, flag]
        return self.wrap_privilege(cmd, use_pkexec)

    def build_unpack(self, fiasco_file: str, out_dir: Optional[str] = None, use_pkexec: bool = False) -> List[str]:
        """Unpack FIASCO: flasher-3.5 -F <file> -u[=dir]"""
        unpack_arg = f"-u={out_dir}" if out_dir else "-u"
        cmd = [self.binary_path, "-F", os.path.abspath(fiasco_file), unpack_arg]
        return self.wrap_privilege(cmd, use_pkexec)


class FlasherTask:
    """Manages asynchronous execution of flasher commands with live output."""

    def __init__(
        self,
        commands: List[Tuple[str, List[str]]],
        on_line: Callable[[str], None],
        on_step_change: Callable[[int, int, str], None],
        on_complete: Callable[[bool, str], None],
        on_step_finished: Optional[Callable[[int, int, str], bool]] = None,
    ):
        """
        Args:
            commands: List of tuples (step_title, command_args)
            on_line: Callback for each line of stdout/stderr
            on_step_change: Callback (current_step, total_steps, title)
            on_complete: Callback (success_bool, message)
            on_step_finished: Optional callback after a step finishes successfully.
                              Passed (step_index, total_steps, completed_title).
                              Return True to proceed to next step, False to abort.
        """
        self.commands = commands
        self.on_line = on_line
        self.on_step_change = on_step_change
        self.on_complete = on_complete
        self.on_step_finished = on_step_finished
        self._process: Optional[subprocess.Popen] = None
        self._cancelled = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True, name="FlasherTaskThread")
        self._thread.start()

    def cancel(self):
        self._cancelled = True
        if self._process:
            try:
                self._process.terminate()
            except Exception:
                pass

    def _run(self):
        total = len(self.commands)
        env = os.environ.copy()
        env["LC_ALL"] = "C"

        for idx, (title, cmd) in enumerate(self.commands):
            if self._cancelled:
                self.on_line("\n[!] Flashing operation cancelled by user.\n")
                self.on_complete(False, "Cancelled by user.")
                return

            self.on_step_change(idx + 1, total, title)
            self.on_line(f"\n========================================================")
            self.on_line(f"▶ STEP {idx + 1}/{total}: {title}")
            self.on_line(f"COMMAND: {' '.join(cmd)}")
            self.on_line(f"========================================================\n")

            try:
                self._process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    env=env,
                )

                for raw_line in iter(self._process.stdout.readline, ""):
                    if self._cancelled:
                        break
                    line = raw_line.rstrip()
                    if line:
                        self.on_line(line)

                if self._process.stdout:
                    self._process.stdout.close()

                self._process.wait()
                ret = self._process.returncode

                if self._cancelled:
                    self.on_line("\n[!] Process was cancelled.\n")
                    self.on_complete(False, "Operation cancelled.")
                    return

                if ret != 0:
                    self.on_line(f"\n❌ Error: Step failed with return code {ret}\n")
                    self.on_complete(False, f"Step '{title}' failed with error code {ret}")
                    return

                self.on_line(f"\n✔ Step '{title}' completed successfully!\n")

                # If there are more steps, allow intermission hook to pause for device reboot
                if idx + 1 < total and self.on_step_finished:
                    should_continue = self.on_step_finished(idx + 1, total, title)
                    if not should_continue or self._cancelled:
                        self.on_line("\n[!] Flashing sequence stopped before next step by user.\n")
                        self.on_complete(False, "Sequence stopped between steps.")
                        return

            except FileNotFoundError:
                msg = f"Executable not found: {cmd[0]}"
                self.on_line(f"\n❌ {msg}\n")
                self.on_complete(False, msg)
                return
            except Exception as e:
                msg = f"Unexpected execution error: {str(e)}"
                self.on_line(f"\n❌ {msg}\n")
                self.on_complete(False, msg)
                return

        self.on_line("\n🎉 ALL FLASHING STEPS COMPLETED SUCCESSFULLY!\n")
        self.on_complete(True, "All operations completed successfully!")
