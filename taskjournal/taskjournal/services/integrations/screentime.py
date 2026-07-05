from datetime import datetime, timedelta
from os.path import expanduser, exists
from pathlib import Path
from sqlite3 import connect, OperationalError, DatabaseError
from sys import platform

from taskjournal.services.base import BaseService, HealthCheckResult, ServiceStatus
from taskjournal.services.logger import logger

_DB_PATHS = [
    "~/Library/Application Support/Knowledge/knowledgeC.db",
    "~/Library/Application Support/com.apple.knowledge-agent/knowledgeC.db",
]

_APPLE_EPOCH = datetime(2001, 1, 1)

_NOISE_BUNDLE_IDS = {
    "com.apple.loginwindow",
    "com.apple.finder",
    "com.apple.dock",
    "com.apple.systemuiserver",
    "com.apple.WindowManager",
    "com.apple.spotlight",
    "com.apple.Notification Center",
}


def _apple_to_unix(apple_seconds: float) -> datetime:
    return _APPLE_EPOCH + timedelta(seconds=apple_seconds)


def _unix_to_apple(dt: datetime) -> float:
    return (dt - _APPLE_EPOCH).total_seconds()


def _bundle_to_app_name(bundle_id: str) -> str:
    known = {
        "com.apple.dt.Xcode": "Xcode",
        "com.microsoft.VSCode": "VS Code",
        "com.todesktop.230313mzl4w4u92": "Cursor",
        "com.apple.Terminal": "Terminal",
        "com.googlecode.iterm2": "iTerm2",
        "com.apple.Safari": "Safari",
        "com.google.Chrome": "Chrome",
        "com.mozilla.firefox": "Firefox",
        "com.tinyspeck.slackmacgap": "Slack",
        "us.zoom.xos": "Zoom",
        "com.microsoft.teams2": "Teams",
        "com.figma.Desktop": "Figma",
        "com.obsidian.md": "Obsidian",
        "com.apple.Notes": "Notes",
        "com.apple.mail": "Mail",
    }
    if bundle_id in known:
        return known[bundle_id]
    parts = bundle_id.split(".")
    return parts[-1].replace("-", " ").title() if parts else bundle_id


class ScreenTimeService(BaseService):
    """Reads macOS Screen Time data from the knowledgeC.db SQLite database."""

    def __init__(self, enabled: bool = False) -> None:
        self._enabled = enabled
        self._db_path: str | None = None

    @property
    def name(self) -> str:
        return "ScreenTimeService"

    def _find_db(self) -> str | None:
        for path in _DB_PATHS:
            expanded = expanduser(path)
            if exists(expanded):
                return expanded
        return None

    def health_check(self) -> HealthCheckResult:
        if not self._enabled:
            return HealthCheckResult(status=ServiceStatus.UNCONFIGURED, message="Screen Time disabled (set SCREEN_TIME_ENABLED=true)")
        if platform != "darwin":
            return HealthCheckResult(status=ServiceStatus.UNCONFIGURED, message="Screen Time is only available on macOS")
        db = self._find_db()
        if not db:
            return HealthCheckResult(status=ServiceStatus.ERROR, message="knowledgeC.db not found — grant Full Disk Access to Terminal")
        try:
            with connect(db) as conn:
                conn.execute("SELECT 1 FROM ZOBJECT LIMIT 1")
            return HealthCheckResult(status=ServiceStatus.OK, message=f"Screen Time database accessible: {db}")
        except (OperationalError, DatabaseError) as e:
            return HealthCheckResult(status=ServiceStatus.ERROR, message=f"Cannot read Screen Time database: {e}")

    def get_usage(self, date: datetime) -> list[tuple[str, int]]:
        """Return list of (app_name, seconds) for the given date, sorted by usage desc."""
        if not self._enabled:
            return []
        if platform != "darwin":
            return []
        db = self._db_path or self._find_db()
        if not db:
            logger.warning("Screen Time: knowledgeC.db not found")
            return []

        day_start = datetime(date.year, date.month, date.day)
        day_end = day_start + timedelta(days=1)
        apple_start = _unix_to_apple(day_start)
        apple_end = _unix_to_apple(day_end)

        query = """
            SELECT ZVALUESTRING, SUM(ZENDDATE - ZSTARTDATE) as duration
            FROM ZOBJECT
            WHERE ZSTREAMNAME = '/app/inFocus'
              AND ZSTARTDATE >= ?
              AND ZENDDATE <= ?
              AND ZVALUESTRING IS NOT NULL
            GROUP BY ZVALUESTRING
            ORDER BY duration DESC
        """
        try:
            with connect(db) as conn:
                rows = conn.execute(query, (apple_start, apple_end)).fetchall()
        except (OperationalError, DatabaseError) as e:
            logger.warning(f"Screen Time query failed: {e}")
            return []

        result: list[tuple[str, int]] = []
        for bundle_id, seconds in rows:
            if bundle_id in _NOISE_BUNDLE_IDS:
                continue
            app_name = _bundle_to_app_name(bundle_id)
            result.append((app_name, int(seconds)))

        return result

    def format_usage(self, date: datetime) -> str:
        """Return a formatted string of app usage for the given date."""
        usage = self.get_usage(date)
        if not usage:
            return ""
        total = sum(s for _, s in usage)
        if total == 0:
            return ""
        lines: list[str] = []
        for app, seconds in usage[:10]:
            h, m = divmod(seconds // 60, 60)
            bar_len = max(1, int(seconds / total * 15))
            bar = "█" * bar_len + "░" * (15 - bar_len)
            lines.append(f"{app:<20} {h}h {m:02d}m  {bar}")
        return "\n".join(lines)
