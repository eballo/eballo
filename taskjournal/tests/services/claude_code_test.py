from asyncio import subprocess as aio_subprocess
from unittest.mock import AsyncMock, MagicMock, patch

from pytest import fixture, mark
from pytest_mock import MockerFixture

from taskjournal.services.ai.claude_code import ClaudeCodeService


@fixture
def claude_code_service() -> ClaudeCodeService:
    return ClaudeCodeService()


def _mock_proc(
    mocker: MockerFixture,
    stdout: str = "",
    returncode: int = 0,
    side_effect: Exception | None = None,
) -> MagicMock:
    mock_proc = MagicMock()
    mock_proc.returncode = returncode
    mock_proc.communicate = AsyncMock(
        return_value=(stdout.encode(), b"")
    )
    if side_effect is not None:
        mock_create = AsyncMock(side_effect=side_effect)
    else:
        mock_create = AsyncMock(return_value=mock_proc)
    mocker.patch("taskjournal.services.ai.claude_code.create_subprocess_exec", mock_create)
    return mock_proc


class TestClaudeCode:
    @mark.asyncio
    async def test_summarize_returns_summary(
        self,
        claude_code_service: ClaudeCodeService,
        mocker: MockerFixture,
    ) -> None:
        # given
        _mock_proc(mocker, stdout="This is the weekly summary.")

        # when
        result = await claude_code_service.summarize(
            ["Did X", "Fixed Y", "Reviewed Z"],
            stats={
                "total_time_seconds": 3600 * 8,
                "days_at_office": 2,
                "days_at_home": 3,
                "vacation_days": 0,
            },
            is_fireman_week=True,
        )

        # then
        assert result == "This is the weekly summary."

    @mark.asyncio
    async def test_summarize_monthly_period(
        self,
        claude_code_service: ClaudeCodeService,
        mocker: MockerFixture,
    ) -> None:
        # given
        _mock_proc(mocker, stdout="This is the monthly summary.")

        # when
        result = await claude_code_service.summarize(
            ["Work done throughout the month"],
            stats={
                "total_time_seconds": 3600 * 160,
                "days_at_office": 10,
                "days_at_home": 10,
                "vacation_days": 2,
            },
            period="monthly",
        )

        # then
        assert result == "This is the monthly summary."

    @mark.asyncio
    async def test_summarize_handles_empty_input(
        self, claude_code_service: ClaudeCodeService
    ) -> None:
        result = await claude_code_service.summarize([])
        assert result == "No summaries provided."

    @mark.asyncio
    async def test_summarize_handles_nonzero_exit_code(
        self,
        claude_code_service: ClaudeCodeService,
        mocker: MockerFixture,
    ) -> None:
        # given
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.communicate = AsyncMock(return_value=(b"", b"some error"))
        mocker.patch(
            "taskjournal.services.ai.claude_code.create_subprocess_exec",
            AsyncMock(return_value=mock_proc),
        )

        # when
        result = await claude_code_service.summarize(["Work A"])
        # then
        assert "exit code 1" in result

    @mark.asyncio
    async def test_summarize_handles_timeout(
        self,
        claude_code_service: ClaudeCodeService,
        mocker: MockerFixture,
    ) -> None:
        # given
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(side_effect=TimeoutError())
        mocker.patch(
            "taskjournal.services.ai.claude_code.create_subprocess_exec",
            AsyncMock(return_value=mock_proc),
        )

        # when
        result = await claude_code_service.summarize(["Work A", "Work B"])
        # then
        assert "timed out" in result

    @mark.asyncio
    async def test_summarize_handles_generic_exception(
        self,
        claude_code_service: ClaudeCodeService,
        mocker: MockerFixture,
    ) -> None:
        # given
        _mock_proc(mocker, side_effect=RuntimeError("Unexpected failure"))

        # when
        result = await claude_code_service.summarize(["Work A", "Work B"])
        # then
        assert "unexpected error" in result

    def test_health_check_ok_when_claude_available(
        self,
        claude_code_service: ClaudeCodeService,
        mocker: MockerFixture,
    ) -> None:
        mocker.patch("taskjournal.services.ai.claude_code.which", return_value="/usr/local/bin/claude")
        result = claude_code_service.health_check()
        assert result.status.value == "ok"

    def test_health_check_unconfigured_when_claude_missing(
        self,
        claude_code_service: ClaudeCodeService,
        mocker: MockerFixture,
    ) -> None:
        mocker.patch("taskjournal.services.ai.claude_code.which", return_value=None)
        result = claude_code_service.health_check()
        assert result.status.value == "unconfigured"
