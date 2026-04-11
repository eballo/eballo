import httpx
import respx
from pytest import MonkeyPatch, mark

from taskjournal.services.openai import OpenAIService


class TestOpenai:
    @mark.asyncio
    async def test_summarize_returns_summary(
        self,
        respx_mock: respx.MockRouter,
        openai_chat_completions_url: str,
        openai_service: OpenAIService,
    ) -> None:
        # given
        route = respx_mock.post(openai_chat_completions_url).mock(
            return_value=httpx.Response(
                200,
                json={
                    "choices": [{"message": {"content": "This is the weekly summary."}}]
                },
            )
        )

        # when
        result = await openai_service.summarize(
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
        assert route.called

        # Check that the request contains the context instruction
        request_body = route.calls.last.request.content.decode()
        assert "CONTEXT ONLY" in request_body
        assert "DO NOT REPEAT" in request_body
        assert "Do NOT include titles like 'Weekly Work Summary'" in request_body
        assert "Key Achievements" in request_body
        assert "Problems Fixed" in request_body
        assert "Technical Debt" in request_body
        assert "Collaboration & Mentoring" in request_body
        assert "Strategic Decisions" in request_body
        assert "Upcoming Focus" in request_body
        assert "bullet points" in request_body
        assert "brief cohesive summary first" in request_body
        assert (
            "highlight achievements and challenges related to being on-call"
            in request_body
        )

    @mark.asyncio
    async def test_summarize_handles_empty_input(
        self, openai_service: OpenAIService
    ) -> None:
        # when
        result = await openai_service.summarize([])
        # then
        assert result == "No summaries provided."

    @mark.asyncio
    async def test_summarize_handles_unexpected_format(
        self,
        respx_mock: respx.MockRouter,
        openai_chat_completions_url: str,
        openai_service: OpenAIService,
    ) -> None:
        # given
        respx_mock.post(openai_chat_completions_url).mock(
            return_value=httpx.Response(
                200,
                json={"choices": [{}]},
            )
        )

        # when
        result = await openai_service.summarize(["Did something"])
        # then
        assert "unexpected response format" in result

    @mark.asyncio
    async def test_summarize_handles_timeout(
        self,
        respx_mock: respx.MockRouter,
        openai_chat_completions_url: str,
        openai_service: OpenAIService,
    ) -> None:
        # given
        respx_mock.post(openai_chat_completions_url).mock(
            side_effect=httpx.TimeoutException("Request timed out")
        )

        # when
        result = await openai_service.summarize(["Work A", "Work B"])
        # then
        assert "timed out" in result

    @mark.asyncio
    async def test_summarize_handles_http_error(
        self,
        respx_mock: respx.MockRouter,
        openai_chat_completions_url: str,
        openai_service: OpenAIService,
    ) -> None:
        # given
        respx_mock.post(openai_chat_completions_url).mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )

        # when
        result = await openai_service.summarize(["Work A", "Work B"])
        # then
        assert "service error" in result

    @mark.asyncio
    async def test_summarize_handles_generic_exception(
        self,
        monkeypatch: MonkeyPatch,
        openai_service: OpenAIService,
    ) -> None:
        # given
        async def broken_post(*_args: object, **_kwargs: object) -> None:
            raise RuntimeError("Unexpected failure")

        monkeypatch.setattr("httpx.AsyncClient.post", broken_post)

        # when
        result = await openai_service.summarize(["Work A", "Work B"])
        # then
        assert "unexpected error" in result
