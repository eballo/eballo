from datetime import datetime
from sqlite3 import DatabaseError, OperationalError
from unittest.mock import call, patch

import pytest

from taskjournal.services.base import ServiceStatus
from taskjournal.services.integrations.screentime import ScreenTimeService


@pytest.mark.parametrize(
    ("present", "expected", "checked"),
    [
        ({"/mock/first.db"}, "/mock/first.db", [call("/mock/first.db")]),
        (
            {"/mock/second.db"},
            "/mock/second.db",
            [call("/mock/first.db"), call("/mock/second.db")],
        ),
        (set(), None, [call("/mock/first.db"), call("/mock/second.db")]),
    ],
)
def test_find_db_tries_candidates_in_order(present, expected, checked) -> None:
    paths = ["~/first.db", "~/second.db"]
    with (
        patch("taskjournal.services.integrations.screentime._DB_PATHS", paths),
        patch(
            "taskjournal.services.integrations.screentime.expanduser",
            side_effect=lambda path: path.replace("~", "/mock"),
        ) as expand,
        patch(
            "taskjournal.services.integrations.screentime.exists",
            side_effect=lambda path: path in present,
        ) as exists,
    ):
        assert ScreenTimeService(enabled=True)._find_db() == expected

    assert exists.call_args_list == checked
    assert expand.call_args_list == [call(path) for path in paths[: len(checked)]]


@pytest.mark.parametrize(
    "error", [OperationalError("permission denied"), DatabaseError("corrupt database")]
)
def test_health_check_reports_database_errors(error) -> None:
    service = ScreenTimeService(enabled=True)
    with (
        patch("taskjournal.services.integrations.screentime.platform", "darwin"),
        patch.object(service, "_find_db", return_value="/mock/knowledgeC.db"),
        patch(
            "taskjournal.services.integrations.screentime.connect", side_effect=error
        ) as connect,
    ):
        result = service.health_check()

    connect.assert_called_once_with("/mock/knowledgeC.db")
    assert result.status is ServiceStatus.ERROR
    assert result.message == f"Cannot read Screen Time database: {error}"


def test_format_usage_omits_zero_total() -> None:
    service = ScreenTimeService(enabled=True)
    date = datetime(2026, 7, 1)
    with patch.object(
        service, "get_usage", return_value=[("Terminal", 0)]
    ) as get_usage:
        assert service.format_usage(date) == ""
    get_usage.assert_called_once_with(date)
