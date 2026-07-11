from asyncio import subprocess as aio_subprocess
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from pytest import fixture, mark
from pytest_mock import MockerFixture

from taskjournal.models.parsed_note import ParsedNote
from taskjournal.models.task import Status, Task
from taskjournal.services.ai.base import NullAIService, build_daily_prompt, build_prompt
from taskjournal.services.ai.claude_code import ClaudeCodeService
from taskjournal.services.ai.openai import OpenAIService
from taskjournal.services.base import ServiceStatus


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

    @mark.asyncio
    async def test_summarize_day_returns_result(
        self,
        claude_code_service: ClaudeCodeService,
        mocker: MockerFixture,
    ) -> None:
        _mock_proc(mocker, stdout="Today I worked on X.")
        note = ParsedNote(
            date="2025-01-15",
            sprint_name="Sprint 1",
            planned_tasks=[Task(id="1", description="Task A", status=Status.DONE)],
        )
        result = await claude_code_service.summarize_day(note)
        assert result == "Today I worked on X."


class TestNullAIService:

    def test_name_is_none(self) -> None:
        svc = NullAIService()
        assert svc.name == "None"

    def test_health_check_returns_unconfigured(self) -> None:
        svc = NullAIService()
        result = svc.health_check()
        assert result.status == ServiceStatus.UNCONFIGURED
        assert "AI_PROVIDER" in result.message

    @mark.asyncio
    async def test_summarize_returns_disabled_message(self) -> None:
        svc = NullAIService()
        result = await svc.summarize(["Summary A", "Summary B"])
        assert "disabled" in result.lower()

    @mark.asyncio
    async def test_summarize_day_returns_empty_string(self) -> None:
        svc = NullAIService()
        note = ParsedNote(date="2025-01-15")
        result = await svc.summarize_day(note)
        assert result == ""


class TestBuildDailyPrompt:

    def test_includes_done_tasks(self) -> None:
        note = ParsedNote(
            date="2025-01-15",
            planned_tasks=[Task(id="1", description="Fix bug", status=Status.DONE)],
        )
        prompt = build_daily_prompt(note)
        assert "Fix bug" in prompt
        assert "Completed" in prompt

    def test_includes_wip_tasks(self) -> None:
        note = ParsedNote(
            date="2025-01-15",
            planned_tasks=[Task(id="1", description="Review PR", status=Status.IN_PROGRESS)],
        )
        prompt = build_daily_prompt(note)
        assert "Review PR" in prompt
        assert "Work in progress" in prompt

    def test_includes_blocked_tasks(self) -> None:
        note = ParsedNote(
            date="2025-01-15",
            planned_tasks=[Task(id="1", description="Deploy", status=Status.BLOCKED)],
        )
        prompt = build_daily_prompt(note)
        assert "Deploy" in prompt
        assert "Blocked" in prompt

    def test_includes_code_review_tasks(self) -> None:
        note = ParsedNote(
            date="2025-01-15",
            code_review_tasks=[Task(id="1", description="PR-123", status=Status.TODO)],
        )
        prompt = build_daily_prompt(note)
        assert "PR-123" in prompt
        assert "Code reviews" in prompt

    def test_includes_notes_and_firefighter(self) -> None:
        note = ParsedNote(
            date="2025-01-15",
            notes=["- Attended meeting", "- Discussed roadmap"],
            firefighter=["- Incident P1"],
        )
        prompt = build_daily_prompt(note)
        assert "Attended meeting" in prompt
        assert "Incident P1" in prompt

    def test_includes_sprint_and_time_metadata(self) -> None:
        note = ParsedNote(
            date="2025-01-15",
            sprint_name="Sprint 42",
            time_spent="07:30",
            work_from="Office",
        )
        prompt = build_daily_prompt(note)
        assert "Sprint 42" in prompt
        assert "07:30" in prompt
        assert "Office" in prompt

    def test_includes_existing_summary(self) -> None:
        note = ParsedNote(
            date="2025-01-15",
            summary=["Great day overall"],
        )
        prompt = build_daily_prompt(note)
        assert "Great day overall" in prompt
        assert "Existing summary" in prompt

    def test_skips_empty_note_lines(self) -> None:
        note = ParsedNote(
            date="2025-01-15",
            notes=["-", "---", "  "],
            firefighter=["-", "---"],
        )
        prompt = build_daily_prompt(note)
        assert "Notes:" not in prompt
        assert "Firefighter" not in prompt

    def test_code_review_status_included_in_wip(self) -> None:
        note = ParsedNote(
            date="2025-01-15",
            planned_tasks=[Task(id="1", description="Review merge", status=Status.CODE_REVIEW)],
        )
        prompt = build_daily_prompt(note)
        assert "Work in progress" in prompt


class TestBuildPrompt:

    def test_weekly_prompt_contains_daily_summaries(self) -> None:
        summaries = ["Did X", "Fixed Y"]
        prompt = build_prompt(summaries, stats=None, is_fireman_week=False, period="weekly")
        assert "Did X" in prompt
        assert "Fixed Y" in prompt

    def test_prompt_includes_stats_when_provided(self) -> None:
        stats: dict[str, Any] = {
            "total_time_seconds": 3600 * 8,
            "days_at_office": 3,
            "days_at_home": 2,
            "vacation_days": 0,
        }
        prompt = build_prompt(["summary"], stats=stats, is_fireman_week=False, period="weekly")
        assert "Days at Office: 3" in prompt
        assert "Days at Home: 2" in prompt

    def test_prompt_mentions_fireman_week(self) -> None:
        stats: dict[str, Any] = {
            "total_time_seconds": 0,
            "days_at_office": 0,
            "days_at_home": 5,
            "vacation_days": 0,
        }
        prompt = build_prompt(["on-call"], stats=stats, is_fireman_week=True, period="weekly")
        assert "FIREMAN" in prompt

    def test_prompt_without_stats(self) -> None:
        prompt = build_prompt(["did work"], stats=None, is_fireman_week=False, period="monthly")
        assert "did work" in prompt
        assert "monthly" in prompt.lower()

    def test_period_label_in_prompt(self) -> None:
        prompt = build_prompt(["summary"], stats=None, is_fireman_week=False, period="quarterly")
        assert "quarterly" in prompt.lower()


class TestOpenAIService:

    @fixture
    def openai_service(self) -> OpenAIService:
        return OpenAIService(api_key="test-api-key")

    def test_name_is_openai(self, openai_service: OpenAIService) -> None:
        assert openai_service.name == "OpenAI"

    def test_health_check_ok_when_key_configured(self, openai_service: OpenAIService) -> None:
        result = openai_service.health_check()
        assert result.status == ServiceStatus.OK
        assert "configured" in result.message

    def test_health_check_unconfigured_when_default_key(self) -> None:
        svc = OpenAIService(api_key="your-openai-api-key")
        result = svc.health_check()
        assert result.status == ServiceStatus.UNCONFIGURED

    def test_health_check_unconfigured_when_empty_key(self) -> None:
        svc = OpenAIService(api_key="")
        result = svc.health_check()
        assert result.status == ServiceStatus.UNCONFIGURED

    def test_init_sets_headers(self) -> None:
        svc = OpenAIService(api_key="my-key")
        assert svc.headers["Authorization"] == "Bearer my-key"
        assert svc.headers["Content-Type"] == "application/json"
        assert "openai.com" in svc.base_url

    @mark.asyncio
    async def test_summarize_returns_no_summaries_message(self, openai_service: OpenAIService) -> None:
        result = await openai_service.summarize([])
        assert result == "No summaries provided."

    @mark.asyncio
    async def test_summarize_calls_openai(
        self, openai_service: OpenAIService, mocker: MockerFixture
    ) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Weekly summary text"}}]
        }
        mock_response.raise_for_status = MagicMock()
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mocker.patch("taskjournal.services.ai.openai.AsyncClient", return_value=mock_client)

        result = await openai_service.summarize(["Did A", "Did B"])
        assert result == "Weekly summary text"

    @mark.asyncio
    async def test_summarize_day_calls_openai(
        self, openai_service: OpenAIService, mocker: MockerFixture
    ) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Daily journal entry"}}]
        }
        mock_response.raise_for_status = MagicMock()
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mocker.patch("taskjournal.services.ai.openai.AsyncClient", return_value=mock_client)

        note = ParsedNote(date="2025-01-15", planned_tasks=[])
        result = await openai_service.summarize_day(note)
        assert result == "Daily journal entry"

    @mark.asyncio
    async def test_call_openai_handles_timeout(
        self, openai_service: OpenAIService, mocker: MockerFixture
    ) -> None:
        from httpx import TimeoutException
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=TimeoutException("timed out"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mocker.patch("taskjournal.services.ai.openai.AsyncClient", return_value=mock_client)

        result = await openai_service.summarize(["summary"])
        assert "timed out" in result.lower()

    @mark.asyncio
    async def test_call_openai_handles_http_status_error(
        self, openai_service: OpenAIService, mocker: MockerFixture
    ) -> None:
        from httpx import HTTPStatusError, Request, Response
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 401
        mock_response.reason_phrase = "Unauthorized"
        mock_response.raise_for_status = MagicMock(
            side_effect=HTTPStatusError("401", request=MagicMock(), response=mock_response)
        )
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mocker.patch("taskjournal.services.ai.openai.AsyncClient", return_value=mock_client)

        result = await openai_service.summarize(["summary"])
        assert "OpenAI service error" in result or "error" in result.lower()

    @mark.asyncio
    async def test_call_openai_handles_generic_exception(
        self, openai_service: OpenAIService, mocker: MockerFixture
    ) -> None:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=RuntimeError("Network failure"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mocker.patch("taskjournal.services.ai.openai.AsyncClient", return_value=mock_client)

        result = await openai_service.summarize(["summary"])
        assert "unexpected error" in result.lower()

    @mark.asyncio
    async def test_call_openai_handles_empty_choices(
        self, openai_service: OpenAIService, mocker: MockerFixture
    ) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {"choices": []}
        mock_response.raise_for_status = MagicMock()
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mocker.patch("taskjournal.services.ai.openai.AsyncClient", return_value=mock_client)

        result = await openai_service.summarize(["summary"])
        assert "unexpected response format" in result.lower() or "⚠️" in result

    @mark.asyncio
    async def test_call_openai_handles_non_string_content(
        self, openai_service: OpenAIService, mocker: MockerFixture
    ) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": 12345}}]
        }
        mock_response.raise_for_status = MagicMock()
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mocker.patch("taskjournal.services.ai.openai.AsyncClient", return_value=mock_client)

        result = await openai_service.summarize(["summary"])
        assert "unexpected content format" in result.lower() or "⚠️" in result
