from pathlib import Path
from platform import system
from shutil import which
from subprocess import run as _run_process, PIPE, CalledProcessError

from taskjournal.services.base import BaseService, HealthCheckResult, ServiceStatus
from taskjournal.services.logger import logger

_LABEL = "com.taskjournal.backup"
_PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / f"{_LABEL}.plist"
_CRON_MARKER = "# taskjournal-backup"

_PLIST_TEMPLATE = """\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{label}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{wk_path}</string>
        <string>backup</string>
        <string>run</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>{hour}</integer>
        <key>Minute</key>
        <integer>{minute}</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/tmp/taskjournal-backup.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/taskjournal-backup.log</string>
</dict>
</plist>
"""


class ScheduleService(BaseService):

    @property
    def name(self) -> str:
        return "Schedule"

    def health_check(self) -> HealthCheckResult:
        if self.is_installed():
            return HealthCheckResult(ServiceStatus.OK, "Backup schedule is active")
        return HealthCheckResult(ServiceStatus.WARNING, "No backup schedule configured")

    def is_installed(self) -> bool:
        if system() == "Darwin":
            return _PLIST_PATH.exists()
        return self._cron_entry() is not None

    def install(self, hour: int, minute: int) -> None:
        if system() == "Darwin":
            self._install_launchd(hour, minute)
        else:
            self._install_cron(hour, minute)

    def uninstall(self) -> None:
        if system() == "Darwin":
            self._uninstall_launchd()
        else:
            self._uninstall_cron()

    def _install_launchd(self, hour: int, minute: int) -> None:
        wk_path = which("wk")
        if not wk_path:
            raise RuntimeError("Cannot find 'wk' binary in PATH")
        _PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
        if _PLIST_PATH.exists():
            _execute(["launchctl", "unload", str(_PLIST_PATH)])
        _PLIST_PATH.write_text(
            _PLIST_TEMPLATE.format(label=_LABEL, wk_path=wk_path, hour=hour, minute=minute)
        )
        _execute(["launchctl", "load", str(_PLIST_PATH)])

    def _uninstall_launchd(self) -> None:
        if not _PLIST_PATH.exists():
            logger.warning("No backup schedule found.")
            return
        _execute(["launchctl", "unload", str(_PLIST_PATH)])
        _PLIST_PATH.unlink()

    def _install_cron(self, hour: int, minute: int) -> None:
        wk_path = which("wk")
        if not wk_path:
            raise RuntimeError("Cannot find 'wk' binary in PATH")
        entry = f"{minute} {hour} * * * {wk_path} backup run {_CRON_MARKER}"
        lines = [l for l in self._crontab().splitlines() if _CRON_MARKER not in l]
        lines.append(entry)
        self._write_crontab("\n".join(lines) + "\n")

    def _uninstall_cron(self) -> None:
        lines = [l for l in self._crontab().splitlines() if _CRON_MARKER not in l]
        self._write_crontab("\n".join(lines) + "\n")

    def _cron_entry(self) -> str | None:
        for line in self._crontab().splitlines():
            if _CRON_MARKER in line:
                return line
        return None

    def _crontab(self) -> str:
        result = _run_process(["crontab", "-l"], stdout=PIPE, stderr=PIPE)
        return result.stdout.decode() if result.returncode == 0 else ""

    def _write_crontab(self, content: str) -> None:
        _run_process(["crontab", "-"], input=content.encode(), check=True)


def _execute(cmd: list[str]) -> None:
    try:
        _run_process(cmd, check=True, capture_output=True)
    except CalledProcessError as e:
        raise RuntimeError(f"Command failed ({' '.join(cmd)}): {e.stderr.decode()}") from e
