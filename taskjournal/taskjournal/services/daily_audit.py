from collections.abc import Callable, Iterator
from datetime import datetime, timedelta, date as date_t
from os import listdir, walk
from os.path import exists, isdir, join
from re import compile as re_compile

from taskjournal.config import BASE_DIR, TEMPLATE_FORMAT
from taskjournal.services.file import FileService
from taskjournal.services.logger import logger
from taskjournal.services.parser import DailyParserService
from taskjournal.services.time import TimeService


class DailyAuditService:
    def __init__(
        self,
        file_service: FileService,
        time_service: TimeService,
        parser: DailyParserService,
        base_dir: str = str(BASE_DIR),
        template_format: str = TEMPLATE_FORMAT,
    ) -> None:
        self.file_service = file_service
        self.time_service = time_service
        self.parser = parser
        self.base_dir = base_dir
        self.template_format = template_format

    def note_issues(self, file_path: str) -> list[str]:
        issues: list[str] = []
        try:
            lines = self.file_service.get_lines(file_path)
            self.time_service.get_start_time(lines)
        except (ValueError, FileNotFoundError):
            issues.append("missing start time")
        if not self.file_service.check_finalized_in_file(file_path):
            issues.append("missing end time")
        note = self.parser.parse(file_path)
        if note and not note.time_spent.strip():
            issues.append("missing time spent")
        if note and not any(line.strip() for line in note.summary):
            issues.append("missing summary")
        return issues

    def audit_daily_notes(self, year: int) -> list[tuple[str, str, list[str]]]:
        year_dir = join(self.base_dir, str(year))
        if not exists(year_dir):
            return []

        results: list[tuple[str, str, list[str]]] = []
        for entry in sorted(listdir(year_dir)):
            week_path = join(year_dir, entry)
            if not isdir(week_path):
                continue
            for file_name in sorted(listdir(week_path)):
                if not file_name.endswith(f"-DailyNotes.{self.template_format}"):
                    continue
                file_path = join(week_path, file_name)
                date_str = file_name.replace(f"-DailyNotes.{self.template_format}", "")
                results.append((date_str, file_path, self.note_issues(file_path)))
        return results

    def count_week_folders(self, year: int) -> int:
        year_dir = join(self.base_dir, str(year))
        if not exists(year_dir):
            return 0
        return sum(1 for e in listdir(year_dir) if e.startswith("week") and isdir(join(year_dir, e)))

    def audit_weekly_coverage(self, year: int) -> list[tuple[str, list[str]]]:
        year_dir = join(self.base_dir, str(year))
        if not exists(year_dir):
            return []
        today = date_t.today()
        missing: list[tuple[str, list[str]]] = []
        for entry in sorted(listdir(year_dir)):
            if not entry.startswith("week"):
                continue
            week_path = join(year_dir, entry)
            if not isdir(week_path):
                continue
            try:
                week_num = int(entry[4:])
            except ValueError:
                continue
            week_missing: list[str] = []
            for day_num in range(1, 6):
                try:
                    day = date_t.fromisocalendar(year, week_num, day_num)
                except ValueError:
                    continue
                if day > today:
                    continue
                daily_path = join(week_path, f"{day}-DailyNotes.{self.template_format}")
                holiday_path = join(week_path, f"{day}-DailyNotes-Holidays.{self.template_format}")
                if not exists(daily_path) and not exists(holiday_path):
                    week_missing.append(str(day))
            if week_missing:
                missing.append((entry, week_missing))
        return missing

    def get_previous_day_issues(
        self, today: datetime, get_path: Callable[[datetime], str]
    ) -> tuple[str, str, list[str]] | None:
        candidate = today - timedelta(days=1)
        for _ in range(14):
            prev_file = get_path(candidate)
            if exists(prev_file):
                issues = self.note_issues(prev_file)
                return (candidate.strftime("%Y-%m-%d"), prev_file, issues) if issues else None
            candidate -= timedelta(days=1)
        return None

    def warn_incomplete_week_notes(self, week_date: datetime, week_folder: str) -> None:
        start_of_week = week_date - timedelta(days=week_date.weekday())
        incomplete: list[str] = []
        for i in range(5):
            day = start_of_week + timedelta(days=i)
            daily_file = join(week_folder, self.time_service.get_daily_notes_name(day))
            if not exists(daily_file):
                continue
            issues = self.note_issues(daily_file)
            if issues:
                incomplete.append(f"{day.strftime('%Y-%m-%d')}: {', '.join(issues)}")
        if incomplete:
            logger.warning("Week report generated with incomplete notes:")
            for line in incomplete:
                logger.warning(f"  ⚠  {line}")

    def iter_daily_notes(self, year: int) -> Iterator[tuple[datetime, str]]:
        year_dir = join(self.base_dir, str(year))
        if not exists(year_dir):
            return
        for entry in sorted(listdir(year_dir)):
            week_path = join(year_dir, entry)
            if not isdir(week_path):
                continue
            for file_name in sorted(listdir(week_path)):
                if not file_name.endswith(f"-DailyNotes.{self.template_format}"):
                    continue
                date_str = file_name.replace(f"-DailyNotes.{self.template_format}", "")
                try:
                    day = datetime.strptime(date_str, "%Y-%m-%d")
                except ValueError:
                    continue
                yield day, join(week_path, file_name)

    def iter_streak_dates(self) -> Iterator[date_t]:
        date_rx = re_compile(r"^(\d{4}-\d{2}-\d{2})")
        for _, _, files in walk(self.base_dir):
            for fname in files:
                if "DailyNotes" not in fname:
                    continue
                dm = date_rx.match(fname)
                if dm:
                    try:
                        yield datetime.strptime(dm.group(1), "%Y-%m-%d").date()
                    except ValueError:
                        pass