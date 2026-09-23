from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from taskjournal.commands.commands import CommandManager


@pytest.fixture
def macos(mocker):
    mocker.patch("taskjournal.commands.daily.platform", "darwin")
    return mocker.patch("taskjournal.commands.daily.subprocess_run")


def test_schedule_alarm_writes_tracking_file_on_success(
    cmd: CommandManager, macos, tmp_path
) -> None:
    macos.return_value.returncode = 0
    path = tmp_path / "alarm"

    cmd._daily._schedule_macos_alarm(datetime(2025, 3, 9, 17, 25), str(path), "Finish")

    assert path.read_text() == "reminder|2025-03-09|17:25|Finish"
    assert 'body:"wk:2025-03-09:17:25"' in macos.call_args.args[0][2]


def test_schedule_alarm_failure_or_exception_does_not_write_file(
    cmd: CommandManager, macos, tmp_path
) -> None:
    path = tmp_path / "alarm"
    macos.return_value = SimpleNamespace(returncode=1, stderr=b"permission denied")
    cmd._daily._schedule_macos_alarm(datetime(2025, 1, 15, 17), str(path))
    assert not path.exists()

    macos.side_effect = OSError("osascript missing")
    cmd._daily._schedule_macos_alarm(datetime(2025, 1, 15, 17), str(path))
    assert not path.exists()


@pytest.mark.parametrize(
    ("content", "program", "script_fragment"),
    [
        (
            "reminder|2025-01-15|17:30|Finish",
            "osascript",
            'body is "wk:2025-01-15:17:30"',
        ),
        ("reminder|Old alarm", "osascript", 'name is "Old alarm"'),
        ("wk.alarm|17:30", "launchctl", "bootout"),
        ("1234:17:30", "kill", "1234"),
    ],
)
def test_cancel_alarm_uses_matching_legacy_backend(
    cmd: CommandManager, macos, tmp_path, mocker, content, program, script_fragment
) -> None:
    path = tmp_path / "alarm"
    path.write_text(content)
    mocker.patch("taskjournal.commands.daily._LAUNCH_AGENTS_DIR", str(tmp_path))

    cmd._daily._cancel_macos_alarm(str(path))

    assert not path.exists()
    assert macos.call_args.args[0][0] == program
    assert script_fragment in " ".join(macos.call_args.args[0])


def test_cancel_missing_file_or_failed_system_call_keeps_tracking_file(
    cmd: CommandManager, macos, tmp_path
) -> None:
    path = tmp_path / "alarm"
    cmd._daily._cancel_macos_alarm(str(path))
    macos.assert_not_called()

    path.write_text("reminder|2025-01-15|17:30|Finish")
    macos.side_effect = OSError("osascript missing")
    cmd._daily._cancel_macos_alarm(str(path))
    assert path.exists()


def test_pending_tags_handles_success_failure_empty_and_exception(
    cmd: CommandManager, macos
) -> None:
    macos.return_value = SimpleNamespace(
        returncode=0, stdout="wk:2025-01-15:17:30, wk:2025-01-16:18:00\n"
    )
    assert cmd._daily._pending_wk_tags() == {
        "wk:2025-01-15:17:30",
        "wk:2025-01-16:18:00",
    }

    macos.return_value = SimpleNamespace(returncode=1, stdout="wk:error")
    assert cmd._daily._pending_wk_tags() == set()
    macos.return_value = SimpleNamespace(returncode=0, stdout=" ")
    assert cmd._daily._pending_wk_tags() == set()
    macos.side_effect = OSError("osascript missing")
    assert cmd._daily._pending_wk_tags() == set()


def test_list_alarms_reads_current_legacy_and_expired_entries(
    cmd: CommandManager, macos, tmp_path, mocker
) -> None:
    mocker.patch.object(cmd.file_service, "get_week_folder", return_value=str(tmp_path))
    mocker.patch.object(
        cmd._daily,
        "_pending_wk_tags",
        return_value={"wk:2025-01-15:17:30", "wk:Old alarm"},
    )
    mocker.patch(
        "taskjournal.commands.daily.datetime", wraps=datetime
    ).now.return_value = datetime(2025, 1, 16)
    (tmp_path / ".alarm_job_2025-01-15_1730").write_text(
        "reminder|2025-01-15|17:30|Finish"
    )
    (tmp_path / ".alarm_job_2025-01-16_1800").write_text("reminder|Old alarm|18:00")
    (tmp_path / ".alarm_job_2025-01-17_1800").write_text("label|18:00")
    (tmp_path / ".alarm_job_2025-01-18_1800").write_text("1234:18:00")
    (tmp_path / "ignore.md").write_text("untracked")
    macos.side_effect = [SimpleNamespace(returncode=0), SimpleNamespace(returncode=1)]

    alarms = cmd._daily.list_alarms(weeks_back=1)

    assert len(alarms) == 4
    assert alarms[0] == {
        "date": "2025-01-15",
        "job_id": "2025-01-15",
        "scheduled": "17:30",
        "message": "Finish",
        "is_past": True,
        "is_alive": True,
    }
    assert alarms[1]["is_alive"] is True
    assert alarms[2]["is_alive"] is True
    assert alarms[3]["is_alive"] is False
    assert macos.call_count == 2


def test_list_alarms_ignores_unreadable_files_and_invalid_dates(
    cmd: CommandManager, macos, tmp_path, mocker
) -> None:
    mocker.patch.object(cmd.file_service, "get_week_folder", return_value=str(tmp_path))
    mocker.patch.object(cmd._daily, "_pending_wk_tags", return_value=set())
    mocker.patch(
        "taskjournal.commands.daily.datetime", wraps=datetime
    ).now.return_value = datetime(2025, 1, 16)
    invalid = tmp_path / ".alarm_job_invalid-date"
    invalid.write_text("reminder|2025-01-15")
    unreadable = tmp_path / ".alarm_job_2025-01-15_1234"
    unreadable.write_text("1234")
    original_read = Path.read_text

    def read_file(path, *args, **kwargs):
        if path == unreadable:
            raise OSError("unreadable")
        return original_read(path, *args, **kwargs)

    mocker.patch("taskjournal.commands.daily.Path.read_text", read_file)

    assert cmd._daily.list_alarms(0) == [
        {
            "date": "invalid-da",
            "job_id": "2025-01-15",
            "scheduled": None,
            "message": None,
            "is_past": False,
            "is_alive": False,
        }
    ]
    macos.assert_not_called()
