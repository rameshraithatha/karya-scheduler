from unittest.mock import MagicMock

from core.job_utils import (exceeded_max_retries, get_current_step,
                            get_retry_count, increment_retry_count)


def test_get_current_step():
    mock_job = MagicMock()
    mock_job.context = {"meta": {"current_step": "jira_check"}}
    mock_job.steps = [{"id": "jira_check", "type": "task", "action": "CheckJiraStatus"}]
    assert get_current_step(mock_job) == {
        "id": "jira_check",
        "type": "task",
        "action": "CheckJiraStatus",
    }


def test_get_current_step_empty_steps():
    mock_job = MagicMock()
    mock_job.steps = []
    assert get_current_step(mock_job) == {}


def test_get_retry_count():
    mock_job = MagicMock()
    mock_job.context = {
        "meta": {"current_step": "jira_check", "step_retries": {"jira_check": 1}}
    }
    result = get_retry_count(mock_job)
    assert result == 1


def test_increment_retry_count():
    mock_job = MagicMock()
    mock_job.context = {
        "meta": {"current_step": "jira_check", "step_retries": {"jira_check": 1}}
    }
    increment_retry_count(mock_job)
    assert mock_job.step_retry_counts["jira_check"] == 2
    assert mock_job.context["meta"]["step_retries"]["jira_check"] == 2


def test_increment_retry_count_empty_step():
    mock_job = MagicMock()
    mock_job.context = {"meta": {}}
    res = increment_retry_count(mock_job)
    assert res is None


def test_exceeded_max_retries():
    mock_job = MagicMock()
    mock_job.context = {
        "meta": {"current_step": "wait_step", "step_retries": {"wait_step": 4}}
    }
    mock_job.steps = [
        {"id": "wait_step", "type": "wait", "duration": "5", "max_retries": 3}
    ]
    assert exceeded_max_retries(mock_job) is True


def test_exceeded_max_retries_non_wait_type():
    mock_job = MagicMock()
    mock_job.context = {"meta": {"current_step": "jira_check"}}
    mock_job.steps = [{"id": "jira_check", "type": "task", "action": "CheckJiraStatus"}]
    assert exceeded_max_retries(mock_job) is False
