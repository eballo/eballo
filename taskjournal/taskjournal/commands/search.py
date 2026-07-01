from datetime import datetime
from os import walk
from os.path import join
from re import compile as re_compile, escape as re_escape, IGNORECASE, Pattern

from taskjournal.config import TEMPLATE_FORMAT, BASE_DIR
from taskjournal.services.logger import logger


class SearchCommands:

    def search_notes(
        self,
        query: str,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        note_type: str | None = None,
    ) -> list[tuple[str, int, str]]:
        results: list[tuple[str, int, str]] = []
        pattern: Pattern[str] = re_compile(re_escape(query), IGNORECASE)
        date_rx: Pattern[str] = re_compile(r"^(\d{4}-\d{2}-\d{2})")

        for root, dirs, files in walk(str(BASE_DIR)):
            dirs.sort()
            for fname in sorted(files):
                if not fname.endswith(f".{TEMPLATE_FORMAT}"):
                    continue
                if note_type == "daily" and "DailyNotes" not in fname:
                    continue
                if note_type == "week" and "week-summary" not in fname:
                    continue

                if from_date or to_date:
                    dm = date_rx.match(fname)
                    if dm:
                        try:
                            fdate = datetime.strptime(dm.group(1), "%Y-%m-%d")
                            if from_date and fdate < from_date:
                                continue
                            if to_date and fdate > to_date:
                                continue
                        except ValueError:
                            pass

                file_path = join(root, fname)
                try:
                    with open(file_path, encoding="utf-8") as f:
                        for lineno, line in enumerate(f, 1):
                            if pattern.search(line):
                                results.append((file_path, lineno, line.rstrip()))
                except OSError:
                    pass

        return results
