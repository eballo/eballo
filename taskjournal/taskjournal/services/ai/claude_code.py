from asyncio import create_subprocess_exec, wait_for
from asyncio import subprocess as aio_subprocess
from shutil import which
from typing import Any  # dict[str, Any] forwarded to build_prompt

from taskjournal.services.ai.base import AIService, build_prompt
from taskjournal.services.base import HealthCheckResult, ServiceStatus
from taskjournal.services.logger import logger


class ClaudeCodeService(AIService):
    @property
    def name(self) -> str:
        return "Claude Code"

    def health_check(self) -> HealthCheckResult:
        if which("claude") is None:
            return HealthCheckResult(
                ServiceStatus.UNCONFIGURED,
                "claude CLI not found — install Claude Code to enable AI summaries",
            )
        return HealthCheckResult(ServiceStatus.OK, "claude CLI available")

    async def summarize(
        self,
        daily_summaries: list[str],
        stats: dict[str, Any] | None = None,
        is_fireman_week: bool = False,
        period: str = "weekly",
    ) -> str:
        if not daily_summaries:
            return "No summaries provided."

        prompt = build_prompt(daily_summaries, stats, is_fireman_week, period)

        try:
            proc = await create_subprocess_exec(
                "claude",
                "-p",
                prompt,
                stdout=aio_subprocess.PIPE,
                stderr=aio_subprocess.PIPE,
            )
            stdout, stderr = await wait_for(proc.communicate(), timeout=120.0)
            if proc.returncode != 0:
                err = stderr.decode().strip()
                msg = f"⚠️ Claude Code returned exit code {proc.returncode}: {err}"
                logger.error(msg)
                return msg
            return stdout.decode().strip()
        except TimeoutError:
            msg = "⚠️ The request to Claude Code timed out. Please try again."
            logger.error(msg)
            return msg
        except Exception as e:
            msg = f"⚠️ Failed to summarize due to an unexpected error: {e}"
            logger.error(msg)
            return msg
