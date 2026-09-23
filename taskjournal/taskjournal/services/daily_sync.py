from datetime import datetime
from os.path import exists
from re import compile as re_compile

from taskjournal.models.task import Task, Status
from taskjournal.repositories.task_formatter import TaskFormatter
from taskjournal.services.file import FileService
from taskjournal.services.integrations.github import GithubService
from taskjournal.services.integrations.jira import JiraService
from taskjournal.services.logger import console, logger
from taskjournal.services.parser import DailyParserService, _SECTION_RULES


class DailySyncService:
    def __init__(
        self,
        jira: JiraService,
        github: GithubService,
        task_formatter: TaskFormatter,
        file_service: FileService,
        parser: DailyParserService,
    ) -> None:
        self.jira = jira
        self.github = github
        self.task_formatter = task_formatter
        self.file_service = file_service
        self.parser = parser

    async def sync_daily_notes(self, date: datetime, file_path: str) -> tuple[int, int]:
        """Reconcile today's notes with live Jira/GitHub state.

        Adds any assigned Jira task (any status) or code-review task that's
        missing, and corrects the checkbox of any task whose local status has
        gone stale (e.g. a code-review approval, or a Jira status change).
        """
        if not exists(file_path):
            raise FileNotFoundError(f"No daily notes for {date.strftime('%Y-%m-%d')}")

        logger.debug("Fetching Jira tasks...")
        assigned = await self.jira.get_current_sprint_tasks_all_assigned_to_me()
        code_review = await self.jira.get_current_sprint_tasks_in_code_review()

        lines = self.file_service.get_lines(file_path)

        async with self.github:
            await self.github.update_status_if_task_reviewed(code_review)

            added = self._insert_missing_tasks_in_section(lines, "planned_tasks", assigned)
            added += self._insert_missing_tasks_in_section(lines, "code_review_tasks", code_review)
            updated = self._correct_stale_task_statuses(lines, assigned + code_review)
            # A ticket can leave Jira's "Code Review" status/sprint (e.g. moved
            # forward right after merging) before its PR is re-checked here, so
            # already-tracked code-review lines are re-verified directly against
            # their linked PR rather than relying only on the live Jira query.
            updated += await self._correct_existing_code_review_links(lines)

        if added or updated:
            self.file_service.write_lines_to_file(file_path, lines)
        else:
            console.print("[green]✓[/green] Tasks already in sync.")

        return added, updated

    def _insert_missing_tasks_in_section(
        self, lines: list[str], section_name: str, tasks: list[Task]
    ) -> int:
        to_add = [t for t in tasks if t.key and not any(t.key in raw for raw in lines)]
        if not to_add:
            return 0

        task_rx = re_compile(r"^\s*-?\s*\[[ xX>~-]\]")
        in_section = False
        last_task_idx = section_header_idx = -1

        for i, raw in enumerate(lines):
            stripped = raw.strip()
            for sec_name, pat in _SECTION_RULES:
                if pat.match(stripped):
                    in_section = sec_name == section_name
                    if in_section:
                        section_header_idx = i
                    break
            if in_section and task_rx.match(stripped):
                last_task_idx = i

        if section_header_idx == -1:
            return 0

        insert_at = last_task_idx if last_task_idx != -1 else section_header_idx
        for offset, task in enumerate(to_add):
            formatted = self.task_formatter.format_task(task, with_name=True, with_status=False)
            lines.insert(insert_at + 1 + offset, formatted + "\n")
            console.print(f"  [green]+[/green] {task.description}")

        return len(to_add)

    def _correct_stale_task_statuses(self, lines: list[str], tasks: list[Task]) -> int:
        checkbox_rx = re_compile(r"\[([ xX>~-])\]")
        updated = 0

        for task in tasks:
            if not task.key:
                continue
            desired_char = self.task_formatter.status_checkbox_char(task.status)
            for i, raw in enumerate(lines):
                if task.key not in raw:
                    continue
                m = checkbox_rx.search(raw)
                if not m or m.group(1).lower() == desired_char:
                    break
                lines[i] = raw.replace(f"[{m.group(1)}]", f"[{desired_char}]", 1)
                console.print(f"  [cyan]~[/cyan] {task.description} → {task.status.value}")
                updated += 1
                break

        return updated

    async def _correct_existing_code_review_links(self, lines: list[str]) -> int:
        link_rx = re_compile(r"\[🐙\]\(([^)]+)\)")
        checkbox_rx = re_compile(r"\[([ xX>~-])\]")
        in_section = False
        updated = 0

        for i, raw in enumerate(lines):
            stripped = raw.strip()
            for sec_name, pat in _SECTION_RULES:
                if pat.match(stripped):
                    in_section = sec_name == "code_review_tasks"
                    break
            if not in_section:
                continue

            checkbox_match = checkbox_rx.search(raw)
            link_match = link_rx.search(raw)
            if not checkbox_match or not link_match:
                continue
            if checkbox_match.group(1).lower() == "x":
                continue

            reviewed = await self.github.has_user_approved_pr(link_match.group(1))
            if not reviewed:
                continue

            lines[i] = raw.replace(f"[{checkbox_match.group(1)}]", "[x]", 1)
            console.print(f"  [cyan]~[/cyan] {stripped} → {Status.DONE.value}")
            updated += 1

        return updated