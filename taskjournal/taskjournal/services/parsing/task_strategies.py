from abc import ABC, abstractmethod
from re import compile, Pattern
from uuid import uuid4

from taskjournal.models.task import Status, Task

_STATUS_CHAR_MAP: dict[str, Status] = {
    " ": Status.TODO,
    "x": Status.DONE,
    "-": Status.BLOCKED,
    ">": Status.IN_PROGRESS,
    "~": Status.CODE_REVIEW,
}

# Matches the leading "[KEY](link)" and "[🐙](github_link)" markdown that
# TaskFormatter.format_task bakes into a rendered line, so re-parsed tasks
# carry the same key as a freshly-fetched Jira task and dedupe correctly.
_TASK_KEY_LINK_RE = compile(r"^\[([A-Z][A-Z0-9]*-\d+)\]\(([^)]*)\)")
_TASK_GITHUB_RE = compile(r"^\[🐙\]\(([^)]*)\)")

# Plain-text equivalent (see TaskFormatter.format_task): "[KEY] description
# … 🔗 <link> 🐙 <github>" — the key stays a bare tag and the URLs trail the
# line behind sentinels the parser strips back out.
_TXT_TASK_KEY_RE = compile(r"^\[([A-Z][A-Z0-9]*-\d+)\]\s*")
_TXT_TASK_LINK_RE = compile(r"\s*🔗\s*(\S+)")
_TXT_TASK_GITHUB_RE = compile(r"\s*🐙\s*(\S+)")

_TASK_REGEX_MD = compile(r"^\s*-\s*\[([ xX>~-])\]\s*(.*)")
_TASK_REGEX_TXT = compile(r"^\[([ xX>~-])\]\s*(.*)")


class TaskParseStrategy(ABC):

    @property
    @abstractmethod
    def task_regex(self) -> Pattern[str]:
        """Regex pattern to match and extract status char and remainder."""
        ...

    @abstractmethod
    def extract_metadata(
        self, remainder: str
    ) -> tuple[str | None, str | None, str | None, str]:
        """Extract (key, link, github, description) from the task line remainder."""
        ...

    def parse_task(self, line: str) -> Task | None:
        """Parse a line into a Task object if it matches the format, else None."""
        task_match = self.task_regex.match(line)
        if not task_match:
            return None

        status_char = task_match.group(1).lower()
        remainder = task_match.group(2)
        status = _STATUS_CHAR_MAP.get(status_char, Status.TODO)
        key, link, github, description = self.extract_metadata(remainder)

        return Task(
            id=str(uuid4()),
            key=key,
            link=link,
            github=github,
            description=description,
            status=status,
        )


class MarkdownParseStrategy(TaskParseStrategy):

    @property
    def task_regex(self) -> Pattern[str]:
        return _TASK_REGEX_MD

    def extract_metadata(
        self, remainder: str
    ) -> tuple[str | None, str | None, str | None, str]:
        key: str | None = None
        link: str | None = None
        github: str | None = None

        key_match = _TASK_KEY_LINK_RE.match(remainder)
        if key_match:
            key = key_match.group(1)
            link = key_match.group(2)
            remainder = remainder[key_match.end():]

        github_match = _TASK_GITHUB_RE.match(remainder)
        if github_match:
            github = github_match.group(1)
            remainder = remainder[github_match.end():]

        return key, link, github, remainder


class PlainTextParseStrategy(TaskParseStrategy):

    @property
    def task_regex(self) -> Pattern[str]:
        return _TASK_REGEX_TXT

    def extract_metadata(
        self, remainder: str
    ) -> tuple[str | None, str | None, str | None, str]:
        # Legacy .txt notes were rendered with markdown link syntax; keep
        # reading those so keys still dedupe after the format change.
        if _TASK_KEY_LINK_RE.match(remainder):
            return MarkdownParseStrategy().extract_metadata(remainder)

        key: str | None = None
        link: str | None = None
        github: str | None = None

        key_match = _TXT_TASK_KEY_RE.match(remainder)
        if key_match:
            key = key_match.group(1)
            remainder = remainder[key_match.end():]

        link_match = _TXT_TASK_LINK_RE.search(remainder)
        if link_match:
            link = link_match.group(1)
            remainder = remainder[:link_match.start()] + remainder[link_match.end():]

        github_match = _TXT_TASK_GITHUB_RE.search(remainder)
        if github_match:
            github = github_match.group(1)
            remainder = remainder[:github_match.start()] + remainder[github_match.end():]

        return key, link, github, remainder.strip()