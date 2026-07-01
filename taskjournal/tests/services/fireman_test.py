from pytest_mock import MockerFixture
from pathlib import Path
from collections.abc import Callable

from datetime import datetime, date

from taskjournal.config import TEMPLATE_FORMAT
from taskjournal.services.fireman import FiremanService


class TestFireman:

    def test_load_and_parse_normalizes_dates_to_monday(
        self,
        tmp_path: Path,
        mocker: MockerFixture,
        fireman_service_factory: Callable[[datetime], FiremanService],
    ) -> None:
        # given
        base_dir = tmp_path
        target_year = "2025"
        fireman_rel_file = f"fireman/fireman_weeks.{TEMPLATE_FORMAT}"
        fireman_file = base_dir / target_year / "fireman" / f"fireman_weeks.{TEMPLATE_FORMAT}"
        fireman_file.parent.mkdir(parents=True, exist_ok=True)
        fireman_file.write_text(
            "\n".join(
                [
                    "# comments are ignored",
                    "2025-01-08 - week 2",
                    "2025-01-10",
                    "2025-99-99 invalid",
                    "2025-01-13",
                    "this line does not match date pattern",
                ]
            ),
            encoding="utf-8",
        )

        mocker.patch("taskjournal.services.fireman.BASE_DIR", str(base_dir))
        mocker.patch(
            "taskjournal.services.fireman.FIREMAN_WEEKS_FILE", fireman_rel_file
        )
        logger = mocker.patch("taskjournal.services.fireman.logger")

        # when
        service = fireman_service_factory(datetime(2025, 1, 9, 9, 0, 0))

        # then
        assert service._get_monday(datetime(2025, 1, 8).date()) in service.fireman_weeks
        assert (
            service._get_monday(datetime(2025, 1, 13).date()) in service.fireman_weeks
        )
        assert len(service.fireman_weeks) == 2
        logger.error.assert_called_once_with("Invalid date: 2025-99-99 invalid")

    def test_load_and_parse_handles_missing_file(
        self,
        mocker: MockerFixture,
        fireman_service_factory: Callable[[datetime], FiremanService],
    ) -> None:
        # given
        mocker.patch("taskjournal.services.fireman.BASE_DIR", "/tmp/does-not-exist")
        logger = mocker.patch("taskjournal.services.fireman.logger")

        # when
        service = fireman_service_factory(datetime(2025, 1, 9, 9, 0, 0))

        # then
        assert service.fireman_weeks == set()
        logger.warning.assert_called_once()

    def test_is_fireman_week_true_and_false(
        self,
        tmp_path: Path,
        mocker: MockerFixture,
        fireman_service_factory: Callable[[datetime], FiremanService],
    ) -> None:
        # given
        fireman_file = tmp_path / "2025" / "fireman" / f"fireman_weeks.{TEMPLATE_FORMAT}"
        fireman_file.parent.mkdir(parents=True, exist_ok=True)
        fireman_file.write_text("2025-01-06\n", encoding="utf-8")

        mocker.patch("taskjournal.services.fireman.BASE_DIR", str(tmp_path))
        logger = mocker.patch("taskjournal.services.fireman.logger")

        # when
        true_service = fireman_service_factory(datetime(2025, 1, 8, 10, 0, 0))
        false_service = fireman_service_factory(datetime(2025, 1, 20, 10, 0, 0))

        # then
        assert true_service.is_fireman_week() is True
        assert false_service.is_fireman_week() is False
        assert logger.info.call_count >= 2

    def _make_service_with_weeks(
        self,
        tmp_path: Path,
        mocker: MockerFixture,
        fireman_service_factory: Callable[[datetime], FiremanService],
        weeks: list[str],
    ) -> FiremanService:
        fireman_file = tmp_path / "2025" / "fireman" / f"fireman_weeks.{TEMPLATE_FORMAT}"
        fireman_file.parent.mkdir(parents=True, exist_ok=True)
        fireman_file.write_text("\n".join(weeks) + "\n", encoding="utf-8")
        mocker.patch("taskjournal.services.fireman.BASE_DIR", str(tmp_path))
        mocker.patch("taskjournal.services.fireman.logger")
        return fireman_service_factory(datetime(2025, 1, 1))

    def test_get_all_weeks_returns_sorted_mondays(
        self,
        tmp_path: Path,
        mocker: MockerFixture,
        fireman_service_factory: Callable[[datetime], FiremanService],
    ) -> None:
        svc = self._make_service_with_weeks(
            tmp_path, mocker, fireman_service_factory,
            ["2025-01-15", "2025-01-06", "2025-01-22"],
        )
        weeks = svc.get_all_weeks()
        assert weeks == sorted(weeks)
        assert all(d.weekday() == 0 for d in weeks)

    def test_get_upcoming_and_past_weeks(
        self,
        tmp_path: Path,
        mocker: MockerFixture,
        fireman_service_factory: Callable[[datetime], FiremanService],
    ) -> None:
        svc = self._make_service_with_weeks(
            tmp_path, mocker, fireman_service_factory,
            ["2025-01-06", "2025-01-13", "2025-01-20"],
        )
        today = date(2025, 1, 14)  # Tuesday of week starting 2025-01-13
        past = svc.get_past_weeks(today)
        upcoming = svc.get_upcoming_weeks(today)
        assert date(2025, 1, 6) in past
        assert date(2025, 1, 13) in upcoming  # current week included
        assert date(2025, 1, 20) in upcoming

    def test_get_next_week_returns_closest_monday(
        self,
        tmp_path: Path,
        mocker: MockerFixture,
        fireman_service_factory: Callable[[datetime], FiremanService],
    ) -> None:
        svc = self._make_service_with_weeks(
            tmp_path, mocker, fireman_service_factory,
            ["2025-01-20", "2025-01-27"],
        )
        today = date(2025, 1, 14)
        days, next_monday = svc.get_next_week(today)
        assert next_monday == date(2025, 1, 20)
        assert days == 6

    def test_get_next_week_returns_none_when_empty(
        self,
        tmp_path: Path,
        mocker: MockerFixture,
        fireman_service_factory: Callable[[datetime], FiremanService],
    ) -> None:
        svc = self._make_service_with_weeks(
            tmp_path, mocker, fireman_service_factory, []
        )
        days, next_monday = svc.get_next_week(date(2025, 1, 14))
        assert next_monday is None
        assert days == 0

    def test_add_week_appends_to_file(
        self,
        tmp_path: Path,
        mocker: MockerFixture,
        fireman_service_factory: Callable[[datetime], FiremanService],
    ) -> None:
        fireman_file = tmp_path / "2025" / "fireman" / f"fireman_weeks.{TEMPLATE_FORMAT}"
        fireman_file.parent.mkdir(parents=True, exist_ok=True)
        fireman_file.write_text("2025-01-06\n", encoding="utf-8")
        mocker.patch("taskjournal.services.fireman.BASE_DIR", str(tmp_path))
        mocker.patch("taskjournal.services.fireman.logger")

        svc = fireman_service_factory(datetime(2025, 1, 1))
        svc.add_week("2025-01-20")

        assert fireman_file.read_text().count("2025-01-20") == 1
        assert date(2025, 1, 20) in svc.fireman_weeks

    def test_add_week_skips_duplicate(
        self,
        tmp_path: Path,
        mocker: MockerFixture,
        fireman_service_factory: Callable[[datetime], FiremanService],
    ) -> None:
        fireman_file = tmp_path / "2025" / "fireman" / f"fireman_weeks.{TEMPLATE_FORMAT}"
        fireman_file.parent.mkdir(parents=True, exist_ok=True)
        fireman_file.write_text("2025-01-06\n", encoding="utf-8")
        mocker.patch("taskjournal.services.fireman.BASE_DIR", str(tmp_path))
        logger_mock = mocker.patch("taskjournal.services.fireman.logger")

        svc = fireman_service_factory(datetime(2025, 1, 1))
        svc.add_week("2025-01-08")  # same week as 2025-01-06

        logger_mock.warning.assert_called_once()
        assert fireman_file.read_text().strip() == "2025-01-06"

    def test_add_week_invalid_date_logs_error(
        self,
        tmp_path: Path,
        mocker: MockerFixture,
        fireman_service_factory: Callable[[datetime], FiremanService],
    ) -> None:
        fireman_file = tmp_path / "2025" / "fireman" / f"fireman_weeks.{TEMPLATE_FORMAT}"
        fireman_file.parent.mkdir(parents=True, exist_ok=True)
        fireman_file.write_text("", encoding="utf-8")
        mocker.patch("taskjournal.services.fireman.BASE_DIR", str(tmp_path))
        logger_mock = mocker.patch("taskjournal.services.fireman.logger")

        svc = fireman_service_factory(datetime(2025, 1, 1))
        svc.add_week("not-a-date")

        logger_mock.error.assert_called_once()

    def test_add_week_missing_file_logs_error(
        self,
        tmp_path: Path,
        mocker: MockerFixture,
        fireman_service_factory: Callable[[datetime], FiremanService],
    ) -> None:
        mocker.patch("taskjournal.services.fireman.BASE_DIR", str(tmp_path))
        logger_mock = mocker.patch("taskjournal.services.fireman.logger")

        svc = fireman_service_factory(datetime(2025, 1, 1))
        svc.add_week("2025-03-10")

        logger_mock.error.assert_called()

    def test_summary_empty(
        self,
        tmp_path: Path,
        mocker: MockerFixture,
        fireman_service_factory: Callable[[datetime], FiremanService],
    ) -> None:
        mocker.patch("taskjournal.services.fireman.BASE_DIR", str(tmp_path))
        logger_mock = mocker.patch("taskjournal.services.fireman.logger")

        svc = fireman_service_factory(datetime(2025, 1, 1))
        svc.summary(date(2025, 6, 1))

        logger_mock.info.assert_called_once_with("No fireman weeks registered.")

    def test_summary_with_past_and_upcoming(
        self,
        tmp_path: Path,
        mocker: MockerFixture,
        fireman_service_factory: Callable[[datetime], FiremanService],
    ) -> None:
        fireman_file = tmp_path / "2025" / "fireman" / f"fireman_weeks.{TEMPLATE_FORMAT}"
        fireman_file.parent.mkdir(parents=True, exist_ok=True)
        fireman_file.write_text("2025-01-06\n2025-01-20\n2025-02-03\n", encoding="utf-8")
        mocker.patch("taskjournal.services.fireman.BASE_DIR", str(tmp_path))
        logger_mock = mocker.patch("taskjournal.services.fireman.logger")

        svc = fireman_service_factory(datetime(2025, 1, 1))
        svc.summary(date(2025, 1, 14))  # after week of Jan 6, before Jan 20

        calls = [str(c) for c in logger_mock.info.call_args_list]
        assert any("Total fireman weeks: 3" in c for c in calls)
        assert any("Done:" in c for c in calls)
        assert any("Next:" in c for c in calls)

    def test_summary_no_upcoming(
        self,
        tmp_path: Path,
        mocker: MockerFixture,
        fireman_service_factory: Callable[[datetime], FiremanService],
    ) -> None:
        fireman_file = tmp_path / "2025" / "fireman" / f"fireman_weeks.{TEMPLATE_FORMAT}"
        fireman_file.parent.mkdir(parents=True, exist_ok=True)
        fireman_file.write_text("2025-01-06\n", encoding="utf-8")
        mocker.patch("taskjournal.services.fireman.BASE_DIR", str(tmp_path))
        logger_mock = mocker.patch("taskjournal.services.fireman.logger")

        svc = fireman_service_factory(datetime(2025, 1, 1))
        svc.summary(date(2025, 12, 31))

        calls = [str(c) for c in logger_mock.info.call_args_list]
        assert any("No upcoming fireman weeks" in c for c in calls)
