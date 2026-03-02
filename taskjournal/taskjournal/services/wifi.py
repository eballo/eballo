import subprocess

from taskjournal.services.logger import logger


class WifiService:
    """Service for WiFi-related operations."""

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
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

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
