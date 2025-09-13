import httpx
import pytest

from taskjournal.services.openai import OpenAIService


@pytest.mark.asyncio
async def test_summarize_returns_summary(respx_mock):
    # Mock OpenAI API response
    route = respx_mock.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={"choices": [{"message": {"content": "This is the weekly summary."}}]},
        )
    )

    service = OpenAIService()
    result = await service.summarize(["Did X", "Fixed Y", "Reviewed Z"])

    assert result == "This is the weekly summary."
    assert route.called


@pytest.mark.asyncio
async def test_summarize_handles_empty_input():
    service = OpenAIService()
    result = await service.summarize([])
    assert result == "No summaries provided."


@pytest.mark.asyncio
async def test_summarize_handles_unexpected_format(respx_mock):
    # Missing "message" in choices
    respx_mock.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={"choices": [{}]},
        )
    )

    service = OpenAIService()
    result = await service.summarize(["Did something"])
    assert "unexpected response format" in result


@pytest.mark.asyncio
async def test_summarize_handles_timeout(respx_mock):
    respx_mock.post("https://api.openai.com/v1/chat/completions").mock(
        side_effect=httpx.TimeoutException("Request timed out")
    )

    service = OpenAIService()
    result = await service.summarize(["Work A", "Work B"])
    assert "timed out" in result


@pytest.mark.asyncio
async def test_summarize_handles_http_error(respx_mock):
    respx_mock.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(500, text="Internal Server Error")
    )

    service = OpenAIService()
    result = await service.summarize(["Work A", "Work B"])
    assert "service error" in result


@pytest.mark.asyncio
async def test_summarize_handles_generic_exception(monkeypatch):
    async def broken_post(*args, **kwargs):
        raise RuntimeError("Unexpected failure")

    service = OpenAIService()

    monkeypatch.setattr("httpx.AsyncClient.post", broken_post)

    result = await service.summarize(["Work A", "Work B"])
    assert "unexpected error" in result
