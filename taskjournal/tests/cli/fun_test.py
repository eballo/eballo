from collections.abc import Callable
from unittest.mock import MagicMock, patch

from pytest_mock import MockerFixture
from typer.testing import Result

from taskjournal.cli.commands.fun import _fetch_joke


class TestFetchJoke:

    def test_fetch_joke_returns_twopart(self, mocker: MockerFixture) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "type": "twopart",
            "setup": "Why do programmers?",
            "delivery": "Because they can!",
        }
        mocker.patch("taskjournal.cli.commands.fun.http_get", return_value=mock_response)

        result = _fetch_joke()

        assert result == ("Why do programmers?", "Because they can!")

    def test_fetch_joke_returns_single(self, mocker: MockerFixture) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "type": "single",
            "joke": "A single joke.",
        }
        mocker.patch("taskjournal.cli.commands.fun.http_get", return_value=mock_response)

        result = _fetch_joke()

        assert result == ("A single joke.", "")

    def test_fetch_joke_returns_none_on_timeout(self, mocker: MockerFixture) -> None:
        from httpx import TimeoutException
        mocker.patch(
            "taskjournal.cli.commands.fun.http_get",
            side_effect=TimeoutException("timed out"),
        )

        result = _fetch_joke()

        assert result is None

    def test_fetch_joke_returns_none_on_request_error(self, mocker: MockerFixture) -> None:
        from httpx import RequestError
        mocker.patch(
            "taskjournal.cli.commands.fun.http_get",
            side_effect=RequestError("connection failed"),
        )

        result = _fetch_joke()

        assert result is None

    def test_fetch_joke_returns_none_when_single_joke_empty(self, mocker: MockerFixture) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {"type": "single", "joke": ""}
        mocker.patch("taskjournal.cli.commands.fun.http_get", return_value=mock_response)

        result = _fetch_joke()

        assert result is None


class TestJokeCLI:

    def test_joke_with_twopart_shows_both_panels(
        self,
        mocker: MockerFixture,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        mocker.patch(
            "taskjournal.cli.commands.fun._fetch_joke",
            return_value=("Why?", "Because!"),
        )
        mocker.patch("taskjournal.cli.commands.fun.sleep")
        mock_live = mocker.MagicMock()
        mock_live.__enter__ = mocker.MagicMock(return_value=mock_live)
        mock_live.__exit__ = mocker.MagicMock(return_value=False)
        mocker.patch("taskjournal.cli.commands.fun.Live", return_value=mock_live)

        result = invoke_cli(["joke"])

        assert result.exit_code == 0
        assert "Why?" in result.output
        assert "Because!" in result.output

    def test_joke_with_single_shows_one_panel(
        self,
        mocker: MockerFixture,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        mocker.patch(
            "taskjournal.cli.commands.fun._fetch_joke",
            return_value=("Only a joke.", ""),
        )

        result = invoke_cli(["joke"])

        assert result.exit_code == 0
        assert "Only a joke." in result.output

    def test_joke_falls_back_to_local_when_fetch_fails(
        self,
        mocker: MockerFixture,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        mocker.patch("taskjournal.cli.commands.fun._fetch_joke", return_value=None)
        mocker.patch(
            "taskjournal.cli.commands.fun.choice",
            return_value=("Fallback setup", "Fallback punchline"),
        )
        mocker.patch("taskjournal.cli.commands.fun.sleep")
        mock_live = mocker.MagicMock()
        mock_live.__enter__ = mocker.MagicMock(return_value=mock_live)
        mock_live.__exit__ = mocker.MagicMock(return_value=False)
        mocker.patch("taskjournal.cli.commands.fun.Live", return_value=mock_live)

        result = invoke_cli(["joke"])

        assert result.exit_code == 0
        assert "Fallback setup" in result.output
