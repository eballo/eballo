from pathlib import Path
from subprocess import CalledProcessError
from unittest.mock import MagicMock

from pytest import raises
from pytest_mock import MockerFixture

from taskjournal.services.schedule import ScheduleService, _PLIST_PATH, _CRON_MARKER


class TestScheduleService:

    def test_name(self) -> None:
        assert ScheduleService().name == "Schedule"

    def test_health_check_ok_when_installed(self, mocker: MockerFixture) -> None:
        from taskjournal.services.base import ServiceStatus
        svc = ScheduleService()
        mocker.patch.object(svc, "is_installed", return_value=True)
        result = svc.health_check()
        assert result.status == ServiceStatus.OK

    def test_health_check_warning_when_not_installed(self, mocker: MockerFixture) -> None:
        from taskjournal.services.base import ServiceStatus
        svc = ScheduleService()
        mocker.patch.object(svc, "is_installed", return_value=False)
        result = svc.health_check()
        assert result.status == ServiceStatus.WARNING

    def test_is_installed_darwin_checks_plist(self, mocker: MockerFixture) -> None:
        mocker.patch("taskjournal.services.schedule.system", return_value="Darwin")
        mocker.patch.object(Path, "exists", return_value=True)
        assert ScheduleService().is_installed() is True

    def test_is_installed_linux_checks_cron(self, mocker: MockerFixture) -> None:
        mocker.patch("taskjournal.services.schedule.system", return_value="Linux")
        svc = ScheduleService()
        mocker.patch.object(svc, "_cron_entry", return_value="some cron entry")
        assert svc.is_installed() is True

    def test_is_installed_linux_false_when_no_cron(self, mocker: MockerFixture) -> None:
        mocker.patch("taskjournal.services.schedule.system", return_value="Linux")
        svc = ScheduleService()
        mocker.patch.object(svc, "_cron_entry", return_value=None)
        assert svc.is_installed() is False

    def test_install_darwin_calls_launchd(self, mocker: MockerFixture) -> None:
        mocker.patch("taskjournal.services.schedule.system", return_value="Darwin")
        svc = ScheduleService()
        launchd = mocker.patch.object(svc, "_install_launchd")
        svc.install(17, 30)
        launchd.assert_called_once_with(17, 30)

    def test_install_linux_calls_cron(self, mocker: MockerFixture) -> None:
        mocker.patch("taskjournal.services.schedule.system", return_value="Linux")
        svc = ScheduleService()
        cron = mocker.patch.object(svc, "_install_cron")
        svc.install(17, 30)
        cron.assert_called_once_with(17, 30)

    def test_uninstall_darwin_calls_launchd(self, mocker: MockerFixture) -> None:
        mocker.patch("taskjournal.services.schedule.system", return_value="Darwin")
        svc = ScheduleService()
        launchd = mocker.patch.object(svc, "_uninstall_launchd")
        svc.uninstall()
        launchd.assert_called_once()

    def test_uninstall_linux_calls_cron(self, mocker: MockerFixture) -> None:
        mocker.patch("taskjournal.services.schedule.system", return_value="Linux")
        svc = ScheduleService()
        cron = mocker.patch.object(svc, "_uninstall_cron")
        svc.uninstall()
        cron.assert_called_once()

    def test_install_launchd_raises_when_no_wk(self, mocker: MockerFixture) -> None:
        mocker.patch("taskjournal.services.schedule.which", return_value=None)
        with raises(RuntimeError, match="Cannot find 'wk' binary"):
            ScheduleService()._install_launchd(17, 30)

    def test_install_launchd_unloads_existing_plist(self, mocker: MockerFixture, tmp_path: Path) -> None:
        plist = tmp_path / "test.plist"
        plist.write_text("existing")
        mocker.patch("taskjournal.services.schedule.which", return_value="/usr/bin/wk")
        mocker.patch("taskjournal.services.schedule._PLIST_PATH", plist)
        execute = mocker.patch("taskjournal.services.schedule._execute")
        ScheduleService()._install_launchd(17, 30)
        assert execute.call_count == 2

    def test_install_launchd_no_existing_plist(self, mocker: MockerFixture, tmp_path: Path) -> None:
        plist = tmp_path / "new.plist"
        mocker.patch("taskjournal.services.schedule.which", return_value="/usr/bin/wk")
        mocker.patch("taskjournal.services.schedule._PLIST_PATH", plist)
        execute = mocker.patch("taskjournal.services.schedule._execute")
        ScheduleService()._install_launchd(17, 30)
        assert execute.call_count == 1

    def test_uninstall_launchd_warns_when_no_plist(self, mocker: MockerFixture, tmp_path: Path) -> None:
        plist = tmp_path / "missing.plist"
        mocker.patch("taskjournal.services.schedule._PLIST_PATH", plist)
        execute = mocker.patch("taskjournal.services.schedule._execute")
        ScheduleService()._uninstall_launchd()
        execute.assert_not_called()

    def test_uninstall_launchd_removes_plist(self, mocker: MockerFixture, tmp_path: Path) -> None:
        plist = tmp_path / "existing.plist"
        plist.write_text("plist content")
        mocker.patch("taskjournal.services.schedule._PLIST_PATH", plist)
        execute = mocker.patch("taskjournal.services.schedule._execute")
        ScheduleService()._uninstall_launchd()
        execute.assert_called_once()
        assert not plist.exists()

    def test_install_cron_raises_when_no_wk(self, mocker: MockerFixture) -> None:
        mocker.patch("taskjournal.services.schedule.which", return_value=None)
        svc = ScheduleService()
        mocker.patch.object(svc, "_crontab", return_value="")
        with raises(RuntimeError, match="Cannot find 'wk' binary"):
            svc._install_cron(17, 30)

    def test_install_cron_adds_entry(self, mocker: MockerFixture) -> None:
        mocker.patch("taskjournal.services.schedule.which", return_value="/usr/bin/wk")
        svc = ScheduleService()
        mocker.patch.object(svc, "_crontab", return_value="0 8 * * * some-other-cmd\n")
        write = mocker.patch.object(svc, "_write_crontab")
        svc._install_cron(17, 30)
        written = write.call_args[0][0]
        assert _CRON_MARKER in written
        assert "30 17" in written

    def test_uninstall_cron_removes_entry(self, mocker: MockerFixture) -> None:
        svc = ScheduleService()
        existing = f"0 8 * * * cmd\n30 17 * * * /usr/bin/wk backup run {_CRON_MARKER}\n"
        mocker.patch.object(svc, "_crontab", return_value=existing)
        write = mocker.patch.object(svc, "_write_crontab")
        svc._uninstall_cron()
        written = write.call_args[0][0]
        assert _CRON_MARKER not in written
        assert "0 8 * * * cmd" in written

    def test_cron_entry_returns_line_when_found(self, mocker: MockerFixture) -> None:
        svc = ScheduleService()
        entry = f"30 17 * * * wk backup {_CRON_MARKER}"
        mocker.patch.object(svc, "_crontab", return_value=f"other\n{entry}\n")
        assert svc._cron_entry() == entry

    def test_cron_entry_returns_none_when_not_found(self, mocker: MockerFixture) -> None:
        svc = ScheduleService()
        mocker.patch.object(svc, "_crontab", return_value="other cmd\n")
        assert svc._cron_entry() is None

    def test_crontab_returns_empty_on_nonzero(self, mocker: MockerFixture) -> None:
        result = MagicMock()
        result.returncode = 1
        mocker.patch("taskjournal.services.schedule._run_process", return_value=result)
        assert ScheduleService()._crontab() == ""

    def test_crontab_returns_output_on_success(self, mocker: MockerFixture) -> None:
        result = MagicMock()
        result.returncode = 0
        result.stdout = b"0 8 * * * cmd\n"
        mocker.patch("taskjournal.services.schedule._run_process", return_value=result)
        assert ScheduleService()._crontab() == "0 8 * * * cmd\n"
