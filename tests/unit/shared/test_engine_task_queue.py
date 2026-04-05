"""Tests for Phase 3D: Engine Task Queue.

Validates EngineTask, EngineTaskQueue, and engine control API endpoints.
"""

import asyncio

import pytest

from shared.engine.task_queue import EngineTask, EngineTaskQueue


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def data_dir():
    return "data/output"


@pytest.fixture
def queue(data_dir):
    return EngineTaskQueue(data_dir=data_dir, max_concurrent=1)


# ---------------------------------------------------------------------------
# Tests: EngineTask
# ---------------------------------------------------------------------------


class TestEngineTask:
    """Test EngineTask dataclass."""

    def test_defaults(self):
        """EngineTask initializes with default values."""
        task = EngineTask()
        assert task.status == "queued"
        assert task.process == "full"
        assert task.mode == "template"
        assert task.progress == 0.0

    def test_to_dict(self):
        """to_dict returns all expected keys."""
        task = EngineTask(task_id="abc", status="running", period_id="2026-06")
        d = task.to_dict()
        assert d["task_id"] == "abc"
        assert d["status"] == "running"
        assert d["period_id"] == "2026-06"
        expected_keys = {
            "task_id", "status", "process", "mode", "period_id", "periods",
            "multi_period", "created_at", "started_at", "completed_at",
            "progress", "current_pass", "cost_estimate", "actual_result", "error",
        }
        assert set(d.keys()) == expected_keys


# ---------------------------------------------------------------------------
# Tests: EngineTaskQueue — Submit and Execute
# ---------------------------------------------------------------------------


class TestEngineTaskQueueSubmit:
    """Test task submission and execution."""

    @pytest.mark.asyncio
    async def test_submit_returns_task(self, queue):
        """submit() returns an EngineTask with task_id."""
        task = await queue.submit({
            "period_id": "2026-06",
            "process": "a",
            "mode": "template",
        })
        assert isinstance(task, EngineTask)
        assert task.task_id != ""
        assert task.status in ("queued", "running")

    @pytest.mark.asyncio
    async def test_submit_process_a_completes(self, queue):
        """Process A task completes within reasonable time."""
        task = await queue.submit({
            "period_id": "2026-06",
            "process": "a",
            "mode": "template",
        })

        # Wait for completion (Process A ~15-20s)
        for _ in range(60):
            await asyncio.sleep(1)
            t = queue.get_task(task.task_id)
            if t and t.status in ("completed", "failed"):
                break

        final = queue.get_task(task.task_id)
        assert final is not None
        assert final.status == "completed", f"Task status: {final.status}, error: {final.error}"
        assert final.actual_result is not None
        assert final.progress == 1.0

    @pytest.mark.asyncio
    async def test_task_has_timings(self, queue):
        """Completed task has pass timings in actual_result."""
        task = await queue.submit({
            "period_id": "2026-06",
            "process": "a",
        })

        for _ in range(60):
            await asyncio.sleep(1)
            t = queue.get_task(task.task_id)
            if t and t.status in ("completed", "failed"):
                break

        final = queue.get_task(task.task_id)
        assert final.actual_result is not None
        assert "pass_timings" in final.actual_result
        assert "total_time_seconds" in final.actual_result


class TestEngineTaskQueueCancel:
    """Test task cancellation."""

    @pytest.mark.asyncio
    async def test_cancel_running_task(self, queue):
        """Running task can be cancelled."""
        # Submit a full pipeline (takes longer, easier to cancel)
        task = await queue.submit({
            "period_id": "2026-06",
            "process": "full",
        })

        # Give it a moment to start
        await asyncio.sleep(0.5)

        success = await queue.cancel(task.task_id)
        assert success is True

        final = queue.get_task(task.task_id)
        assert final.status == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_task(self, queue):
        """Cancel returns False for nonexistent task."""
        result = await queue.cancel("nonexistent")
        assert result is False


class TestEngineTaskQueueConcurrency:
    """Test max concurrent enforcement."""

    @pytest.mark.asyncio
    async def test_max_one_concurrent(self, queue):
        """Second task is queued when first is running."""
        task1 = await queue.submit({"period_id": "2026-06", "process": "full"})
        task2 = await queue.submit({"period_id": "2026-05", "process": "a"})

        # Task 2 should be queued since task 1 is running
        t2 = queue.get_task(task2.task_id)
        assert t2.status == "queued"

        # Cleanup
        await queue.cancel(task1.task_id)
        await queue.cancel(task2.task_id)


# ---------------------------------------------------------------------------
# Tests: EngineTaskQueue — List and Get
# ---------------------------------------------------------------------------


class TestEngineTaskQueueList:
    """Test task listing and retrieval."""

    @pytest.mark.asyncio
    async def test_list_tasks(self, queue):
        """list_tasks returns submitted tasks."""
        await queue.submit({"period_id": "2026-06", "process": "a"})
        await queue.submit({"period_id": "2026-05", "process": "a"})

        tasks = queue.list_tasks()
        assert len(tasks) >= 2

        # Cleanup
        for t in tasks:
            await queue.cancel(t.task_id)

    @pytest.mark.asyncio
    async def test_list_tasks_newest_first(self, queue):
        """list_tasks returns newest first."""
        t1 = await queue.submit({"period_id": "2026-06", "process": "a"})
        t2 = await queue.submit({"period_id": "2026-05", "process": "a"})

        tasks = queue.list_tasks()
        assert tasks[0].task_id == t2.task_id  # Newest first

        for t in tasks:
            await queue.cancel(t.task_id)

    @pytest.mark.asyncio
    async def test_get_task_by_id(self, queue):
        """get_task returns correct task."""
        task = await queue.submit({"period_id": "2026-06", "process": "a"})
        found = queue.get_task(task.task_id)
        assert found is not None
        assert found.task_id == task.task_id
        await queue.cancel(task.task_id)

    def test_get_nonexistent_task(self, queue):
        """get_task returns None for missing ID."""
        assert queue.get_task("nonexistent") is None


# ---------------------------------------------------------------------------
# Tests: Period Generation
# ---------------------------------------------------------------------------


class TestPeriodGeneration:
    """Test multi-period generation helper."""

    def test_generates_12_periods(self, queue):
        """_generate_periods creates 12 trailing months."""
        periods = queue._generate_periods("2026-06", 12)
        assert len(periods) == 12
        assert periods[0] == "2025-07"
        assert periods[-1] == "2026-06"

    def test_single_period(self, queue):
        """_generate_periods with count=1 returns just the period."""
        periods = queue._generate_periods("2026-06", 1)
        assert periods == ["2026-06"]

    def test_year_boundary(self, queue):
        """_generate_periods handles year boundary correctly."""
        periods = queue._generate_periods("2026-03", 6)
        assert periods[0] == "2025-10"
        assert periods[-1] == "2026-03"


# ---------------------------------------------------------------------------
# Tests: Cost Estimate
# ---------------------------------------------------------------------------


class TestEngineEstimate:
    """Test cost estimation in task queue."""

    @pytest.mark.asyncio
    async def test_process_a_zero_cost(self, queue):
        """Process A task has zero cost estimate."""
        task = await queue.submit({
            "period_id": "2026-06",
            "process": "a",
        })
        assert task.cost_estimate.get("estimated_cost_usd", 0) == 0.0
        await queue.cancel(task.task_id)

    @pytest.mark.asyncio
    async def test_process_b_has_estimate(self, queue):
        """Process B task has cost estimate."""
        task = await queue.submit({
            "period_id": "2026-06",
            "process": "b",
            "mode": "llm",
        })
        assert task.cost_estimate.get("estimated_calls", 0) > 0
        await queue.cancel(task.task_id)
