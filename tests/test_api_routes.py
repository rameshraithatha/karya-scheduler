import re
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from api.routes import router
from db.models import Job
from main import app
import uuid

app.include_router(router)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def job_data():
    return {
        "workflow_name": "TestFlow",
        "parameters": {"key": "value"},
        "steps": [{"id": "step1", "type": "task", "action": "DummyAction"}],
    }


def test_start_job_success(client, job_data, mocker):
    mock_db = MagicMock()
    mocker.patch("api.routes.SessionLocal", return_value=mock_db)
    mock_executor = MagicMock()
    mocker.patch("api.routes.FlowExecutor", return_value=mock_executor)
    mocker.patch("api.routes.asyncio.create_task", return_value=MagicMock())

    # Just simulate DB behaviors
    mock_db.add.return_value = None
    mock_db.commit.return_value = None
    mock_db.refresh.side_effect = lambda job: setattr(job, "id", job.id)

    response = client.post("/jobs", json=job_data)

    assert response.status_code == 200
    data = response.json()

    # Validate UUID format
    assert re.fullmatch(r"[a-f0-9\-]{36}", data["job_id"])
    assert data["status"] == "SCHEDULED"


def test_get_job_steps_success(client, mocker):
    job_id = str(uuid.uuid4())
    mock_job = Job(
        id=job_id, workflow_name="flow", status="SCHEDULED", steps=[{"id": "a"}]
    )
    mocker.patch(
        "api.routes.SessionLocal",
        return_value=MagicMock(
            query=MagicMock(
                return_value=MagicMock(
                    filter=MagicMock(
                        return_value=MagicMock(first=MagicMock(return_value=mock_job))
                    )
                )
            )
        ),
    )

    response = client.get(f"/jobs/{job_id}/steps")
    assert response.status_code == 200
    assert response.json() == [{"id": "a"}]


def test_get_job_steps_not_found(client, mocker):
    mocker.patch(
        "api.routes.SessionLocal",
        return_value=MagicMock(
            query=MagicMock(
                return_value=MagicMock(
                    filter=MagicMock(
                        return_value=MagicMock(first=MagicMock(return_value=None))
                    )
                )
            )
        ),
    )

    response = client.get("/jobs/nonexistent/steps")
    assert response.status_code == 404
    assert response.json()["detail"] == "Job not found"


def test_get_job_status_success(client, mocker):
    job_id = str(uuid.uuid4())
    mock_job = Job(
        id=job_id, workflow_name="TestFlow", status="RUNNING", context={"key": "val"}
    )
    mocker.patch(
        "api.routes.SessionLocal",
        return_value=MagicMock(
            query=MagicMock(
                return_value=MagicMock(
                    filter=MagicMock(
                        return_value=MagicMock(first=MagicMock(return_value=mock_job))
                    )
                )
            )
        ),
    )

    response = client.get(f"/jobs/{job_id}")
    assert response.status_code == 200
    assert response.json()["job_id"] == job_id


def test_get_job_status_not_found(client, mocker):
    mocker.patch(
        "api.routes.SessionLocal",
        return_value=MagicMock(
            query=MagicMock(
                return_value=MagicMock(
                    filter=MagicMock(
                        return_value=MagicMock(first=MagicMock(return_value=None))
                    )
                )
            )
        ),
    )

    response = client.get("/jobs/invalid")
    assert response.status_code == 404


def test_delete_job_success(client, mocker):
    job_id = "test-id"
    mock_job = Job(id=job_id, workflow_name="Test", status="SCHEDULED", context={})
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = mock_job
    mocker.patch("api.routes.SessionLocal", return_value=mock_db)

    response = client.delete(f"/jobs/{job_id}")
    assert response.status_code == 200
    assert "deleted" in response.json()["message"]


def test_delete_job_not_found(client, mocker):
    mocker.patch(
        "api.routes.SessionLocal",
        return_value=MagicMock(
            query=MagicMock(
                return_value=MagicMock(
                    filter=MagicMock(
                        return_value=MagicMock(first=MagicMock(return_value=None))
                    )
                )
            )
        ),
    )

    response = client.delete("/jobs/unknown")
    assert response.status_code == 404


def test_list_jobs(client, mocker):
    job = Job(id="1", workflow_name="wf", status="SCHEDULED", context={"x": 1})
    mocker.patch(
        "api.routes.SessionLocal",
        return_value=MagicMock(
            query=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[job])))
        ),
    )

    response = client.get("/jobs")
    assert response.status_code == 200
    assert response.json()[0]["job_id"] == "1"


def test_pause_job(client):
    job_id = "dummy"
    response = client.post(f"/jobs/{job_id}/pause")
    assert response.status_code == 200
    assert "Pause" in response.json()["message"]
