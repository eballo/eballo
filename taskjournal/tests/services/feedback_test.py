from datetime import datetime
from pathlib import Path

import pytest

from taskjournal.services.feedback import FeedbackService


class TestFeedbackService:

    @pytest.fixture
    def svc(self, tmp_path: Path) -> FeedbackService:
        return FeedbackService(base_dir=str(tmp_path))

    def test_health_check_ok(self, svc: FeedbackService) -> None:
        result = svc.health_check()
        assert result.status.name == "OK"

    def test_name(self, svc: FeedbackService) -> None:
        assert svc.name == "FeedbackService"

    def test_add_and_list_received(self, svc: FeedbackService) -> None:
        date = datetime(2026, 7, 1)
        svc.add_received("Great review", "Maria", "PR #42", date)
        entries = svc.list_feedback(2026)
        assert len(entries) == 1
        assert entries[0]["type"] == "received"
        assert entries[0]["from_person"] == "Maria"
        assert entries[0]["text"] == "Great review"
        assert entries[0]["context"] == "PR #42"
        assert entries[0]["date"] == "2026-07-01"

    def test_add_and_list_given(self, svc: FeedbackService) -> None:
        date = datetime(2026, 7, 2)
        svc.add_given("Excellent work", "Alex", "1:1", date)
        entries = svc.list_feedback(2026)
        assert len(entries) == 1
        assert entries[0]["type"] == "given"
        assert entries[0]["to_person"] == "Alex"

    def test_list_empty_year(self, svc: FeedbackService) -> None:
        entries = svc.list_feedback(2025)
        assert entries == []

    def test_filter_by_type_received(self, svc: FeedbackService) -> None:
        date = datetime(2026, 7, 1)
        svc.add_received("Good job", "Maria", "", date)
        svc.add_given("Keep it up", "Bob", "", date)
        entries = svc.list_feedback(2026, feedback_type="received")
        assert all(e["type"] == "received" for e in entries)
        assert len(entries) == 1

    def test_filter_by_type_given(self, svc: FeedbackService) -> None:
        date = datetime(2026, 7, 1)
        svc.add_received("Good job", "Maria", "", date)
        svc.add_given("Keep it up", "Bob", "", date)
        entries = svc.list_feedback(2026, feedback_type="given")
        assert all(e["type"] == "given" for e in entries)
        assert len(entries) == 1

    def test_filter_by_quarter(self, svc: FeedbackService) -> None:
        svc.add_received("Q1 feedback", "Maria", "", datetime(2026, 2, 10))
        svc.add_received("Q3 feedback", "Bob", "", datetime(2026, 8, 10))
        q1 = svc.list_feedback(2026, quarter=1)
        assert len(q1) == 1
        assert q1[0]["from_person"] == "Maria"

    def test_filter_by_person_received(self, svc: FeedbackService) -> None:
        svc.add_received("From Maria", "Maria", "", datetime(2026, 1, 1))
        svc.add_received("From Bob", "Bob", "", datetime(2026, 1, 2))
        entries = svc.list_feedback(2026, person="Maria")
        assert len(entries) == 1
        assert entries[0]["from_person"] == "Maria"

    def test_filter_by_person_given(self, svc: FeedbackService) -> None:
        svc.add_given("To Alex", "Alex", "", datetime(2026, 3, 1))
        svc.add_given("To Bob", "Bob", "", datetime(2026, 3, 2))
        entries = svc.list_feedback(2026, person="alex")
        assert len(entries) == 1
        assert entries[0]["to_person"] == "Alex"

    def test_get_for_period(self, svc: FeedbackService) -> None:
        svc.add_received("Jan", "A", "", datetime(2026, 1, 15))
        svc.add_received("Jul", "B", "", datetime(2026, 7, 15))
        result = svc.get_for_period(datetime(2026, 1, 1), datetime(2026, 3, 31))
        assert len(result) == 1
        assert result[0]["from_person"] == "A"

    def test_get_for_period_multi_year(self, svc: FeedbackService) -> None:
        svc.add_received("2025 entry", "X", "", datetime(2025, 12, 20))
        svc.add_received("2026 entry", "Y", "", datetime(2026, 1, 5))
        result = svc.get_for_period(datetime(2025, 12, 1), datetime(2026, 1, 31))
        assert len(result) == 2

    def test_load_invalid_json_returns_empty(self, tmp_path: Path) -> None:
        svc = FeedbackService(base_dir=str(tmp_path))
        path = tmp_path / "2026" / "feedback" / "feedback.json"
        path.parent.mkdir(parents=True)
        path.write_text("not json", encoding="utf-8")
        entries = svc.list_feedback(2026)
        assert entries == []

    def test_multiple_entries_accumulate(self, svc: FeedbackService) -> None:
        for i in range(5):
            svc.add_received(f"feedback {i}", "Person", "", datetime(2026, 1, 1))
        entries = svc.list_feedback(2026)
        assert len(entries) == 5
