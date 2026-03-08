from collections.abc import Callable
from unittest.mock import MagicMock

from taskjournal.services.wifi import WifiService


class TestWifiService:
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
