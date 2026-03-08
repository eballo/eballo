from typing import List

import httpx

from taskjournal.config import OPENAI_API_KEY
from taskjournal.services.logger import logger


class OpenAIService:
    def __init__(self) -> None:
        self.base_url = "https://api.openai.com/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }

    async def summarize(self, daily_summaries: List[str]) -> str:
        """
        Summarize daily notes into a single summary.

        Args:
            daily_summaries: List of daily summaries
            period: "week" or "half-year"
        """
        if not daily_summaries:
            return "No summaries provided."

        messages = [
            {
                "role": "system",
                "content": (
                    "You are an assistant that generates clear, concise summaries "
                    "for a senior software engineer. Start with a summary of the work done and then "
                    "Focus on achievements, progress, blockers, and key learnings."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Here are the daily summaries for the week:\n\n"
                    + "\n".join(f"- {s}" for s in daily_summaries)
                    + "\n\nPlease create a summary."
                ),
            },
        ]

        payload = {
            "model": "gpt-4o-mini",  # fast & cost-effective model
            "messages": messages,
            "temperature": 0.7,
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.base_url, headers=self.headers, json=payload
                )
                response.raise_for_status()
                data = response.json()

            # Validate structure
            choices = data.get("choices")
            if (
                not isinstance(choices, list)
                or not choices
                or "message" not in choices[0]
            ):
                msg = "⚠️ OpenAI service returned an unexpected response format."
                logger.error(msg)
                return msg

            content = choices[0]["message"]["content"]
            if not isinstance(content, str):
                msg = "⚠️ OpenAI service returned an unexpected content format."
                logger.error(msg)
                return msg

            return content.strip()

        except httpx.TimeoutException:
            msg = "⚠️ The request to OpenAI timed out. Please try again."
            logger.error(msg)
            return msg
        except httpx.HTTPStatusError as e:
            msg = f"⚠️ OpenAI service error: {e.response.status_code} {e.response.reason_phrase}"
            logger.error(msg)
            return msg
        except Exception as e:
            msg = f"⚠️ Failed to summarize due to an unexpected error: {e}"
            logger.error(msg)
            return msg
