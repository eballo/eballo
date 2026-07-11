from unittest.mock import MagicMock

from pytest_mock import MockerFixture


class TestRunMarquee:

    def test_run_marquee_calls_console_print_with_text(
        self, mocker: MockerFixture
    ) -> None:
        mocker.stopall()

        mock_live_instance = MagicMock()
        mock_live_instance.__enter__ = MagicMock(return_value=mock_live_instance)
        mock_live_instance.__exit__ = MagicMock(return_value=False)
        mocker.patch("taskjournal.cli.animations.Live", return_value=mock_live_instance)
        mocker.patch("taskjournal.cli.animations.sleep")
        mocker.patch(
            "taskjournal.cli.animations.monotonic",
            side_effect=[0.0, 10.0],
        )
        mocker.patch(
            "taskjournal.cli.animations.get_terminal_size",
            return_value=MagicMock(columns=80),
        )
        mock_print = mocker.patch("taskjournal.cli.animations.console.print")

        from taskjournal.cli.animations import run_marquee
        run_marquee("Hello world", style="bold red", duration=1.0)

        mock_print.assert_called_once()
        call_text = mock_print.call_args[0][0]
        assert "Hello world" in str(call_text)
