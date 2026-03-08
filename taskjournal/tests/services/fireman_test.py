from pytest_mock import MockerFixture
from pathlib import Path
from collections.abc import Callable

from datetime import datetime

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
        fireman_rel_file = "fireman/fireman_weeks.md"
        fireman_file = base_dir / target_year / "fireman" / "fireman_weeks.md"
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
        logger.error.assert_called_once()

    def test_is_fireman_week_true_and_false(
        self,
        tmp_path: Path,
        mocker: MockerFixture,
        fireman_service_factory: Callable[[datetime], FiremanService],
    ) -> None:
        # given
        fireman_file = tmp_path / "2025" / "fireman" / "fireman_weeks.md"
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
