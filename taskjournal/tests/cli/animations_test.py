from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from taskjournal.cli.animations import run_marquee


class TestRunMarquee:

    def test_run_marquee_calls_console_print_with_text(
        self, mocker: MockerFixture
    ) -> None:
        mock_live_instance = MagicMock()
        mock_live_instance.__enter__ = MagicMock(return_value=mock_live_instance)
        mock_live_instance.__exit__ = MagicMock(return_value=False)
        mock_live = mocker.patch(
            "taskjournal.cli.animations.Live", return_value=mock_live_instance
        )
        mock_sleep = mocker.patch("taskjournal.cli.animations.sleep")
        mocker.patch(
            "taskjournal.cli.animations.monotonic",
            side_effect=[0.0, 10.0],
        )
        mock_terminal_size = mocker.patch(
            "taskjournal.cli.animations.get_terminal_size"
        )
        mock_print = mocker.patch("taskjournal.cli.animations.console.print")

        run_marquee("Hello world", style="bold red", duration=1.0)

        mock_live.assert_called_once_with(transient=True, refresh_per_second=20)
        mock_live_instance.update.assert_not_called()
        mock_terminal_size.assert_not_called()
        mock_sleep.assert_not_called()
        mock_print.assert_called_once()
        call_text = mock_print.call_args[0][0]
        assert call_text.plain == "Hello world"
        assert call_text.style == "bold red"

    def test_run_marquee_advances_frames_and_wraps(self, mocker: MockerFixture) -> None:
        mock_live_instance = MagicMock()
        mock_live_instance.__enter__.return_value = mock_live_instance
        mocker.patch("taskjournal.cli.animations.Live", return_value=mock_live_instance)
        mock_sleep = mocker.patch("taskjournal.cli.animations.sleep")
        mocker.patch(
            "taskjournal.cli.animations.monotonic",
            side_effect=[100.0] + [100.0] * 9 + [101.0],
        )
        mock_terminal_size = mocker.patch(
            "taskjournal.cli.animations.get_terminal_size",
            return_value=MagicMock(columns=4),
        )
        mock_print = mocker.patch("taskjournal.cli.animations.console.print")

        run_marquee("Go", duration=1.0)

        frames = [call.args[0] for call in mock_live_instance.update.call_args_list]
        assert [frame.plain for frame in frames] == [
            "   G",
            "  Go",
            " Go ",
            "Go  ",
            "o   ",
            "    ",
            "    ",
            "    ",
            "   G",
        ]
        assert all(frame.style == "bold green" for frame in frames)
        assert mock_terminal_size.call_count == 9
        assert [call.args for call in mock_sleep.call_args_list] == [(0.05,)] * 9
        mock_print.assert_called_once()
        assert mock_print.call_args.args[0].plain == "Go"
        assert mock_print.call_args.args[0].style == "bold green"

    def test_run_marquee_uses_current_terminal_width(
        self, mocker: MockerFixture
    ) -> None:
        mock_live_instance = MagicMock()
        mock_live_instance.__enter__.return_value = mock_live_instance
        mocker.patch("taskjournal.cli.animations.Live", return_value=mock_live_instance)
        mock_sleep = mocker.patch("taskjournal.cli.animations.sleep")
        mocker.patch(
            "taskjournal.cli.animations.monotonic",
            side_effect=[0.0, 0.0, 0.3, 0.6, 0.7],
        )
        mock_terminal_size = mocker.patch(
            "taskjournal.cli.animations.get_terminal_size",
            side_effect=[
                MagicMock(columns=4),
                MagicMock(columns=6),
                MagicMock(columns=2),
            ],
        )
        mock_print = mocker.patch("taskjournal.cli.animations.console.print")

        run_marquee("Go", style="bold red", duration=0.7)

        frames = [call.args[0] for call in mock_live_instance.update.call_args_list]
        assert [frame.plain for frame in frames] == ["   G", "  Go  ", " G"]
        assert all(frame.style == "bold red" for frame in frames)
        assert mock_terminal_size.call_count == 3
        assert mock_sleep.call_count == 3
        mock_print.assert_called_once()
        assert mock_print.call_args.args[0].plain == "Go"
        assert mock_print.call_args.args[0].style == "bold red"

    @pytest.mark.parametrize("duration", [0.0, -1.0])
    def test_run_marquee_skips_frames_for_nonpositive_duration(
        self, mocker: MockerFixture, duration: float
    ) -> None:
        mock_live_instance = MagicMock()
        mock_live_instance.__enter__.return_value = mock_live_instance
        mocker.patch("taskjournal.cli.animations.Live", return_value=mock_live_instance)
        mocker.patch("taskjournal.cli.animations.monotonic", return_value=5.0)
        mock_sleep = mocker.patch("taskjournal.cli.animations.sleep")
        mock_terminal_size = mocker.patch(
            "taskjournal.cli.animations.get_terminal_size"
        )
        mock_print = mocker.patch("taskjournal.cli.animations.console.print")

        run_marquee("Done", duration=duration)

        mock_live_instance.update.assert_not_called()
        mock_terminal_size.assert_not_called()
        mock_sleep.assert_not_called()
        mock_print.assert_called_once()
        assert mock_print.call_args.args[0].plain == "Done"
