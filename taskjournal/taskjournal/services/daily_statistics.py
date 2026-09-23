from collections import defaultdict
from datetime import date as date_t, datetime, timedelta
from os.path import join
from re import compile as re_compile
from typing import Iterator, Protocol

from taskjournal.config import BASE_DIR, HOLIDAYS_FILE
from taskjournal.models.task import Status
from taskjournal.services.calendar.holidays import HolidayService
from taskjournal.services.parser import DailyParserService


class DailyNotesAudit(Protocol):
    def iter_daily_notes(self, year: int) -> Iterator[tuple[datetime, str]]: ...
    def iter_streak_dates(self) -> Iterator[date_t]: ...


class DailyStatisticsService:
    def __init__(self, parser: DailyParserService, audit: DailyNotesAudit) -> None:
        self.parser = parser
        self.audit = audit

    def get_streak_stats(self, today: datetime) -> dict[str, object]:
        all_dates = set(self.audit.iter_streak_dates())

        if not all_dates:
            return {"current": 0, "longest": 0, "longest_start": None, "longest_end": None, "total": 0}

        holiday_cache: dict[int, HolidayService] = {}

        def _is_non_working(d: date_t) -> bool:
            if d.weekday() >= 5:
                return True
            if d.year not in holiday_cache:
                path = join(str(BASE_DIR), f"{d.year}/{HOLIDAYS_FILE}")
                holiday_cache[d.year] = HolidayService(filepath=path)
            return holiday_cache[d.year].is_holiday(datetime(d.year, d.month, d.day)) is not None

        def _next_working(d: date_t) -> date_t:
            d += timedelta(days=1)
            while _is_non_working(d):
                d += timedelta(days=1)
            return d

        today_date = today.date()
        current = 0
        check = today_date
        while True:
            if _is_non_working(check):
                check -= timedelta(days=1)
                continue
            if check not in all_dates:
                break
            current += 1
            check -= timedelta(days=1)

        sorted_dates = sorted(all_dates)
        longest = cur_len = 1
        longest_start = longest_end = cur_start = sorted_dates[0]

        for i in range(1, len(sorted_dates)):
            prev, curr = sorted_dates[i - 1], sorted_dates[i]
            if curr == _next_working(prev):
                cur_len += 1
            else:
                cur_len = 1
                cur_start = curr

            if cur_len > longest:
                longest = cur_len
                longest_start = cur_start
                longest_end = curr

        return {
            "current": current,
            "longest": longest,
            "longest_start": longest_start,
            "longest_end": longest_end,
            "total": len(all_dates),
        }

    def get_completion_stats(self, year: int) -> list[tuple[str, int, int]]:
        results: list[tuple[str, int, int]] = []
        for day, file_path in self.audit.iter_daily_notes(year):
            note = self.parser.parse(file_path)
            if not note:
                continue
            tasks = note.planned_tasks
            if not tasks:
                continue
            done = sum(1 for t in tasks if t.status == Status.DONE)
            results.append((day.strftime("%Y-%m-%d"), done, len(tasks)))
        return results

    def get_workload_stats(self, year: int) -> list[tuple[str, int]]:
        time_rx = re_compile(r"(\d+):(\d+)")
        weekly: dict[str, int] = {}
        for day, file_path in self.audit.iter_daily_notes(year):
            note = self.parser.parse(file_path)
            if not note or not note.time_spent:
                continue
            m = time_rx.search(note.time_spent)
            if not m:
                continue
            seconds = int(m.group(1)) * 3600 + int(m.group(2)) * 60
            week_key = f"W{day.isocalendar()[1]:02d}"
            weekly[week_key] = weekly.get(week_key, 0) + seconds
        return sorted(weekly.items())

    def get_pattern_stats(self, year: int) -> dict[str, object]:
        day_done: dict[int, list[int]] = defaultdict(list)
        day_total: dict[int, list[int]] = defaultdict(list)
        hour_done: dict[int, int] = defaultdict(int)
        carry: list[tuple[str, set[str]]] = []

        prev_pending: set[str] = set()
        for day, file_path in self.audit.iter_daily_notes(year):
            note = self.parser.parse(file_path)
            if not note:
                continue
            tasks = note.planned_tasks
            done = [t.description for t in tasks if t.status == Status.DONE]
            pending = {t.description for t in tasks if t.status in (Status.TODO, Status.IN_PROGRESS, Status.BLOCKED)}
            dow = day.weekday()
            day_done[dow].append(len(done))
            day_total[dow].append(len(tasks))
            if note.start_time:
                try:
                    start_hour = datetime.strptime(note.start_time[:5], "%H:%M").hour
                    hour_done[start_hour] += len(done)
                except (ValueError, TypeError):
                    pass
            carry.append((day.strftime("%Y-%m-%d"), prev_pending & {t.description for t in tasks}))
            prev_pending = pending

        dow_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        avg_by_day = {
            dow_names[d]: round(sum(v) / len(v), 1)
            for d, v in day_done.items() if v and d < 5
        }
        best_day = max(avg_by_day, key=lambda k: avg_by_day[k]) if avg_by_day else None
        best_hour = max(hour_done, key=lambda k: hour_done[k]) if hour_done else None

        total_days = len(carry)
        carry_days = sum(1 for _, c in carry if c)
        carry_rate = round(carry_days / total_days * 100) if total_days else 0

        all_done = [n for vals in day_done.values() for n in vals]
        avg_done = round(sum(all_done) / len(all_done), 1) if all_done else 0

        return {
            "best_day": best_day,
            "best_hour": best_hour,
            "avg_done_per_day": avg_done,
            "carry_over_rate": carry_rate,
            "avg_by_day": avg_by_day,
        }

    def get_tags_stats(self, year: int) -> list[tuple[str, int]]:
        tags_rx = re_compile(r"^Tags:\s*(.+)$", flags=8)
        counts: dict[str, int] = {}
        for _, file_path in self.audit.iter_daily_notes(year):
            with open(file_path) as f:
                for line in f:
                    m = tags_rx.match(line.strip())
                    if m:
                        for tag in m.group(1).split(","):
                            tag = tag.strip()
                            if tag:
                                counts[tag] = counts.get(tag, 0) + 1
                        break
        return sorted(counts.items(), key=lambda x: x[1], reverse=True)