from collections.abc import Callable
from unittest.mock import MagicMock

from taskjournal.constants import PLACEHOLDER_HOME_WIFI, PLACEHOLDER_OFFICE_WIFI
from taskjournal.services.base import ServiceStatus
from taskjournal.services.wifi import WifiService


class TestWifiService:
    def test_name_property(self, wifi_service: WifiService) -> None:
        assert wifi_service.name == "WiFi"

    def test_health_check_ok_when_both_custom(self) -> None:
        svc = WifiService(home_wifi="MyHome", office_wifi="MyOffice")
        result = svc.health_check()
        assert result.status == ServiceStatus.OK

    def test_health_check_unconfigured_when_home_is_default(self) -> None:
        svc = WifiService(home_wifi=PLACEHOLDER_HOME_WIFI, office_wifi="MyOffice")
        result = svc.health_check()
        assert result.status == ServiceStatus.UNCONFIGURED
        assert any("HOME_WIFI" in d for d in result.details)

    def test_health_check_unconfigured_when_office_is_default(self) -> None:
        svc = WifiService(home_wifi="MyHome", office_wifi=PLACEHOLDER_OFFICE_WIFI)
        result = svc.health_check()
        assert result.status == ServiceStatus.UNCONFIGURED
        assert any("OFFICE_WIFI" in d for d in result.details)

    def test_health_check_unconfigured_with_two_details_when_both_default(self) -> None:
        svc = WifiService(home_wifi=PLACEHOLDER_HOME_WIFI, office_wifi=PLACEHOLDER_OFFICE_WIFI)
        result = svc.health_check()
        assert result.status == ServiceStatus.UNCONFIGURED
        assert len(result.details) == 2

    def test_sentinel_strings_come_from_constants(self) -> None:
        from taskjournal.services.setup import _DEFAULTS
        assert _DEFAULTS["HOME_WIFI"] == PLACEHOLDER_HOME_WIFI
        assert _DEFAULTS["OFFICE_WIFI"] == PLACEHOLDER_OFFICE_WIFI

    def test_get_name_success(
        self,
        wifi_service: WifiService,
        wifi_subprocess_run: MagicMock,
        wifi_result_factory: Callable[[str], MagicMock],
    ) -> None:
        # given
        wifi_subprocess_run.return_value = wifi_result_factory(
            "Preferred networks on en0:\n\tCodePI\n\tTSH\n"
        )

        # when
        result = wifi_service.get_name()

        # then
        assert result == "CodePI"
        wifi_subprocess_run.assert_called_once_with(
            ["networksetup", "-listpreferredwirelessnetworks", "en0"],
            capture_output=True,
            text=True,
            check=True,
        )

    def test_get_name_no_networks(
        self,
        wifi_service: WifiService,
        wifi_subprocess_run: MagicMock,
        wifi_result_factory: Callable[[str], MagicMock],
    ) -> None:
        # given
        wifi_subprocess_run.return_value = wifi_result_factory(
            "Preferred networks on en0:\n"
        )

        # when
        result = wifi_service.get_name()

        # then
        assert result is None

    def test_get_name_exception(
        self, wifi_service: WifiService, wifi_subprocess_run: MagicMock
    ) -> None:
        # given
        wifi_subprocess_run.side_effect = Exception("Network error")

        # when
        result = wifi_service.get_name()

        # then
        assert result is None

    def test_get_name_empty_ssid_returns_none(
        self,
        wifi_service: WifiService,
        wifi_subprocess_run: MagicMock,
        wifi_result_factory: Callable[[str], MagicMock],
    ) -> None:
        # given
        wifi_subprocess_run.return_value = wifi_result_factory(
            "Preferred networks on en0:\n \nAnotherNetwork\n"
        )

        # when
        result = wifi_service.get_name()

        # then
        assert result is None
