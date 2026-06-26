from subprocess import run

from taskjournal.constants import PLACEHOLDER_HOME_WIFI, PLACEHOLDER_OFFICE_WIFI
from taskjournal.services.base import BaseService, HealthCheckResult, ServiceStatus
from taskjournal.services.logger import logger


class WifiService(BaseService):
    """Service for WiFi-related operations."""

    def __init__(self, home_wifi: str, office_wifi: str) -> None:
        self.home_wifi = home_wifi
        self.office_wifi = office_wifi

    @property
    def name(self) -> str:
        return "WiFi"

    def health_check(self) -> HealthCheckResult:
        details = []
        if self.home_wifi == PLACEHOLDER_HOME_WIFI:
            details.append("HOME_WIFI is using default value — set it to your home network")
        if self.office_wifi == PLACEHOLDER_OFFICE_WIFI:
            details.append("OFFICE_WIFI is using default value — set it to your office network")
        if details:
            return HealthCheckResult(
                ServiceStatus.UNCONFIGURED,
                "WiFi location detection using default values",
                details,
            )
        return HealthCheckResult(
            ServiceStatus.OK,
            f"Configured (home: {self.home_wifi}, office: {self.office_wifi})",
        )

    @staticmethod
    def get_name() -> str | None:
        """
        Gets the name (SSID) of the currently preferred WiFi network on macOS.

        Returns:
            str | None: The WiFi network name (SSID) if available, None otherwise.

        Note:
            Currently only supports macOS.
            Uses networksetup to get the preferred wireless network.
        """
        try:
            cmd = ["networksetup", "-listpreferredwirelessnetworks", "en0"]
            result = run(cmd, capture_output=True, text=True, check=True)

            lines = result.stdout.strip().split("\n")
            if len(lines) >= 2:
                ssid = lines[1].strip()
                if ssid:
                    logger.debug(f"Connected to WiFi: {ssid}")
                    return ssid

            return None

        except Exception as e:
            logger.error(f"Failed to get WiFi name: {e}")
            return None
