from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from taskjournal.services.integrations.screentime import (
    ScreenTimeService,
    _apple_to_unix,
    _bundle_to_app_name,
    _unix_to_apple,
)


class TestScreenTimeUtils:
    def test_apple_to_unix_epoch(self) -> None:
        result = _apple_to_unix(0.0)
        assert result == datetime(2001, 1, 1)

    def test_unix_to_apple_epoch(self) -> None:
        result = _unix_to_apple(datetime(2001, 1, 1))
        assert result == 0.0

    def test_unix_apple_roundtrip(self) -> None:
        dt = datetime(2026, 7, 1, 12, 0, 0)
        assert abs(_apple_to_unix(_unix_to_apple(dt)).timestamp() - dt.timestamp()) < 1

    def test_bundle_to_app_name_known(self) -> None:
        assert _bundle_to_app_name("com.apple.Terminal") == "Terminal"
        assert _bundle_to_app_name("com.tinyspeck.slackmacgap") == "Slack"
        assert _bundle_to_app_name("com.google.Chrome") == "Chrome"

    def test_bundle_to_app_name_unknown(self) -> None:
        result = _bundle_to_app_name("com.example.MyApp")
        assert result == "Myapp"

    def test_bundle_to_app_name_empty(self) -> None:
        result = _bundle_to_app_name("")
        assert result == ""


class TestScreenTimeService:

    def test_name(self) -> None:
        assert ScreenTimeService(enabled=False).name == "ScreenTimeService"

    def test_health_check_disabled(self) -> None:
        svc = ScreenTimeService(enabled=False)
        result = svc.health_check()
        assert result.status.name == "UNCONFIGURED"
        assert "disabled" in result.message

    @patch("taskjournal.services.integrations.screentime.platform", "linux")
    def test_health_check_non_macos(self) -> None:
        svc = ScreenTimeService(enabled=True)
        result = svc.health_check()
        assert result.status.name == "UNCONFIGURED"
        assert "macOS" in result.message

    @patch("taskjournal.services.integrations.screentime.platform", "darwin")
    def test_health_check_db_not_found(self) -> None:
        svc = ScreenTimeService(enabled=True)
        with patch.object(svc, "_find_db", return_value=None):
            result = svc.health_check()
        assert result.status.name == "ERROR"
        assert "Full Disk Access" in result.message

    @patch("taskjournal.services.integrations.screentime.platform", "darwin")
    def test_health_check_ok(self) -> None:
        svc = ScreenTimeService(enabled=True)
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        with (
            patch.object(svc, "_find_db", return_value="/fake/knowledgeC.db"),
            patch("taskjournal.services.integrations.screentime.connect", return_value=mock_conn),
        ):
            result = svc.health_check()
        assert result.status.name == "OK"

    def test_get_usage_disabled_returns_empty(self) -> None:
        svc = ScreenTimeService(enabled=False)
        result = svc.get_usage(datetime(2026, 7, 1))
        assert result == []

    @patch("taskjournal.services.integrations.screentime.platform", "linux")
    def test_get_usage_non_macos_returns_empty(self) -> None:
        svc = ScreenTimeService(enabled=True)
        result = svc.get_usage(datetime(2026, 7, 1))
        assert result == []

    @patch("taskjournal.services.integrations.screentime.platform", "darwin")
    def test_get_usage_no_db_returns_empty(self) -> None:
        svc = ScreenTimeService(enabled=True)
        with patch.object(svc, "_find_db", return_value=None):
            result = svc.get_usage(datetime(2026, 7, 1))
        assert result == []

    @patch("taskjournal.services.integrations.screentime.platform", "darwin")
    def test_get_usage_returns_apps(self) -> None:
        svc = ScreenTimeService(enabled=True)
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.execute.return_value.fetchall.return_value = [
            ("com.microsoft.VSCode", 7200),
            ("com.apple.Terminal", 3600),
            ("com.apple.loginwindow", 100),
        ]
        with (
            patch.object(svc, "_find_db", return_value="/fake/db"),
            patch("taskjournal.services.integrations.screentime.connect", return_value=mock_conn),
        ):
            result = svc.get_usage(datetime(2026, 7, 1))
        names = [r[0] for r in result]
        assert "VS Code" in names
        assert "Terminal" in names
        assert "Loginwindow" not in names

    @patch("taskjournal.services.integrations.screentime.platform", "darwin")
    def test_get_usage_filters_noise_apps(self) -> None:
        svc = ScreenTimeService(enabled=True)
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.execute.return_value.fetchall.return_value = [
            ("com.apple.loginwindow", 9999),
            ("com.apple.finder", 8888),
        ]
        with (
            patch.object(svc, "_find_db", return_value="/fake/db"),
            patch("taskjournal.services.integrations.screentime.connect", return_value=mock_conn),
        ):
            result = svc.get_usage(datetime(2026, 7, 1))
        assert result == []

    def test_format_usage_disabled_returns_empty(self) -> None:
        svc = ScreenTimeService(enabled=False)
        assert svc.format_usage(datetime(2026, 7, 1)) == ""

    @patch("taskjournal.services.integrations.screentime.platform", "darwin")
    def test_format_usage_with_data(self) -> None:
        svc = ScreenTimeService(enabled=True)
        with patch.object(svc, "get_usage", return_value=[("VS Code", 7200), ("Terminal", 3600)]):
            result = svc.format_usage(datetime(2026, 7, 1))
        assert "VS Code" in result
        assert "Terminal" in result

    @patch("taskjournal.services.integrations.screentime.platform", "darwin")
    def test_get_usage_handles_db_error(self) -> None:
        from sqlite3 import OperationalError
        svc = ScreenTimeService(enabled=True)
        with (
            patch.object(svc, "_find_db", return_value="/fake/db"),
            patch(
                "taskjournal.services.integrations.screentime.connect",
                side_effect=OperationalError("permission denied"),
            ),
        ):
            result = svc.get_usage(datetime(2026, 7, 1))
        assert result == []
