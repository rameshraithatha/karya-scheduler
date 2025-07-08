from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.executor import FlowExecutor

pytestmark = pytest.mark.asyncio


@pytest.fixture
def sample_steps():
    return [
        {"id": "step1", "type": "task", "action": "MockAction"},
        {"id": "step2", "type": "wait", "duration": "1", "max_retries": 2},
        {
            "id": "step3",
            "type": "choice",
            "conditions": [
                {"if": "context.value == 1", "next": "end"},
                {"default": "step2"},
            ],
        },
        {"id": "end", "type": "task", "action": "MockAction"},
    ]


@pytest.fixture
def parameters():
    return {"value": 1}


@pytest.mark.asyncio
async def test_execute_task_step(sample_steps, parameters):
    executor = FlowExecutor(sample_steps, parameters, "job-1")

    with patch.object(
        executor,
        "load_action",
        new=AsyncMock(
            return_value={"type": "http", "method": "POST", "url": "http://mock.url"}
        ),
    ), patch.object(
        executor, "execute_http", new=AsyncMock(return_value="http_completed")
    ), patch.object(
        executor, "persist_context"
    ) as mock_persist:

        result = await executor.run_step(sample_steps[0])
        assert result == "http_completed"
        mock_persist.assert_called_once()


@pytest.mark.asyncio
async def test_execute_wait_step_within_retries(sample_steps, parameters):
    executor = FlowExecutor(sample_steps, parameters, "job-2")

    with patch.object(executor, "session") as mock_session, patch.object(
        executor, "update_job_status"
    ) as mock_update:

        mock_job = MagicMock()
        mock_session.query().get.return_value = mock_job

        result = await executor.run_step(sample_steps[1])

        assert result is "job_paused"
        assert mock_job.status == "WAITING"
        mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_execute_wait_step_exceed_retries(sample_steps, parameters):
    executor = FlowExecutor(sample_steps, parameters, "job-3")
    step_id = sample_steps[1]["id"]
    executor.retry_counts[step_id] = 2
    executor.context["meta"]["step_retries"][step_id] = 2

    with patch.object(executor, "update_job_status") as mock_update:
        result = await executor.run_step(sample_steps[1])
        assert result is None
        mock_update.assert_called_with(
            "FAILED", f"Max retries exceeded for step '{step_id}'"
        )


@pytest.mark.asyncio
async def test_execute_choice_step(sample_steps, parameters):
    executor = FlowExecutor(sample_steps, parameters, "job-4")

    with patch.object(executor, "persist_context") as mock_persist:
        result = await executor.run_step(sample_steps[2])
        assert result == "end"
        mock_persist.assert_called_once()


@pytest.mark.asyncio
async def test_execute_steps_flow_success(sample_steps, parameters):
    executor = FlowExecutor(sample_steps[:1], parameters, "job-5")

    with patch.object(
        executor, "run_step", new=AsyncMock(return_value="http_completed")
    ), patch.object(executor, "update_job_status") as mock_update:

        result = await executor.execute_steps()
        assert result == "completed"
        mock_update.assert_called_with("COMPLETED")


@pytest.mark.asyncio
async def test_run_failure_logs_and_updates(sample_steps, parameters):
    executor = FlowExecutor(sample_steps, parameters, "job-6")

    with patch.object(executor, "update_job_status") as mock_update, patch.object(
        executor, "execute_steps", side_effect=Exception("fail")
    ):

        await executor.run()
        mock_update.assert_called_with("FAILED", "fail")
