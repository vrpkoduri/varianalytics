"""Tests for report scheduler."""
import pytest

from services.reports.scheduler.report_scheduler import ReportScheduler


class TestReportScheduler:
    def test_add_schedule(self):
        scheduler = ReportScheduler()
        scheduler.add_schedule("s1", {"name": "Weekly Pulse", "frequency": "WEEKLY", "enabled": True})
        assert len(scheduler.schedules) == 1
        assert "s1" in scheduler.schedules

    def test_remove_schedule(self):
        scheduler = ReportScheduler()
        scheduler.add_schedule("s1", {"name": "Test", "frequency": "DAILY"})
        assert scheduler.remove_schedule("s1") is True
        assert len(scheduler.schedules) == 0

    def test_remove_nonexistent(self):
        scheduler = ReportScheduler()
        assert scheduler.remove_schedule("nope") is False

    def test_update_schedule(self):
        scheduler = ReportScheduler()
        scheduler.add_schedule("s1", {"name": "Old", "frequency": "DAILY"})
        result = scheduler.update_schedule("s1", {"name": "New"})
        assert result is not None
        assert result["name"] == "New"

    def test_update_nonexistent(self):
        scheduler = ReportScheduler()
        assert scheduler.update_schedule("nope", {"name": "X"}) is None

    def test_list_schedules(self):
        scheduler = ReportScheduler()
        scheduler.add_schedule("s1", {"name": "A", "frequency": "DAILY"})
        scheduler.add_schedule("s2", {"name": "B", "frequency": "WEEKLY"})
        assert len(scheduler.list_schedules()) == 2

    def test_get_schedule(self):
        scheduler = ReportScheduler()
        scheduler.add_schedule("s1", {"name": "Test", "frequency": "DAILY"})
        sched = scheduler.get_schedule("s1")
        assert sched is not None
        assert sched["name"] == "Test"

    def test_get_nonexistent(self):
        scheduler = ReportScheduler()
        assert scheduler.get_schedule("nope") is None

    def test_next_run_computed(self):
        scheduler = ReportScheduler()
        scheduler.add_schedule("s1", {"name": "Test", "frequency": "DAILY"})
        sched = scheduler.get_schedule("s1")
        assert sched is not None
        assert sched["next_run_at"] is not None

    def test_add_schedule_returns_record(self):
        scheduler = ReportScheduler()
        result = scheduler.add_schedule("s1", {"name": "X", "frequency": "MONTHLY"})
        assert result["schedule_id"] == "s1"
        assert result["name"] == "X"
        assert result["created_at"] is not None

    @pytest.mark.asyncio
    async def test_start_stop(self):
        scheduler = ReportScheduler()
        await scheduler.start()
        assert scheduler._running is True
        await scheduler.stop()
        assert scheduler._running is False

    @pytest.mark.asyncio
    async def test_double_start_is_noop(self):
        scheduler = ReportScheduler()
        await scheduler.start()
        task1 = scheduler._task
        await scheduler.start()  # Should not create second task
        assert scheduler._task is task1
        await scheduler.stop()
