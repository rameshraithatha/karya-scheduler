from unittest.mock import MagicMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from api.actions import router
from db.models import Action
from main import app

app.include_router(router)
client = TestClient(app)


@pytest.fixture
def action_data():
    return {
        "name": "TestAction",
        "type": "http",
        "config": {"url": "https://example.com"},
    }


def test_create_action_success(action_data, mocker):
    mock_db = MagicMock()
    mocker.patch("api.actions.SessionLocal", return_value=mock_db)
    mock_db.query.return_value.filter.return_value.first.return_value = None

    response = client.post("/actions", json=action_data)

    assert response.status_code == 200
    assert response.json()["message"] == f"Action '{action_data['name']}' created"
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()


def test_create_action_conflict(action_data, mocker):
    mock_db = MagicMock()
    mocker.patch("api.actions.SessionLocal", return_value=mock_db)
    mock_db.query.return_value.filter.return_value.first.return_value = Action(
        **action_data
    )

    response = client.post("/actions", json=action_data)

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["detail"] == "Action already exists"


def test_get_action_success(action_data, mocker):
    mock_db = MagicMock()
    mock_action = Action(**action_data)
    mocker.patch("api.actions.SessionLocal", return_value=mock_db)
    mock_db.query.return_value.filter.return_value.first.return_value = mock_action

    response = client.get(f"/actions/{action_data['name']}")

    assert response.status_code == 200
    assert response.json()["name"] == action_data["name"]


def test_get_action_not_found(mocker):
    mock_db = MagicMock()
    mocker.patch("api.actions.SessionLocal", return_value=mock_db)
    mock_db.query.return_value.filter.return_value.first.return_value = None

    response = client.get("/actions/NonExistent")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Action not found"


def test_update_action_success(action_data, mocker):
    mock_db = MagicMock()
    existing_action = Action(**action_data)
    mocker.patch("api.actions.SessionLocal", return_value=mock_db)
    mock_db.query.return_value.filter.return_value.first.return_value = existing_action

    updated = action_data.copy()
    updated.pop("name")
    updated["type"] = "new_type"
    updated["config"] = {"url": "https://updated.com"}

    response = client.put(f"/actions/{action_data['name']}", json=updated)

    assert response.status_code == 200
    assert "updated" in response.json()["message"]
    mock_db.commit.assert_called_once()


def test_update_action_not_found(action_data, mocker):
    mock_db = MagicMock()
    mocker.patch("api.actions.SessionLocal", return_value=mock_db)
    mock_db.query.return_value.filter.return_value.first.return_value = None

    response = client.put(f"/actions/{action_data['name']}", json=action_data)

    assert response.status_code == 404
    assert response.json()["detail"] == "Action not found"


def test_delete_action_success(action_data, mocker):
    mock_db = MagicMock()
    mock_action = Action(**action_data)
    mocker.patch("api.actions.SessionLocal", return_value=mock_db)
    mock_db.query.return_value.filter.return_value.first.return_value = mock_action

    response = client.delete(f"/actions/{action_data['name']}")

    assert response.status_code == 200
    assert "deleted" in response.json()["message"]
    mock_db.delete.assert_called_once()
    mock_db.commit.assert_called_once()


def test_delete_action_not_found(mocker):
    mock_db = MagicMock()
    mocker.patch("api.actions.SessionLocal", return_value=mock_db)
    mock_db.query.return_value.filter.return_value.first.return_value = None

    response = client.delete("/actions/NonExistent")

    assert response.status_code == 404
    assert response.json()["detail"] == "Action not found"


def test_list_actions(mocker):
    mock_db = MagicMock()
    actions = [
        Action(name="A1", type="http", config={}),
        Action(name="A2", type="http", config={}),
    ]
    mocker.patch("api.actions.SessionLocal", return_value=mock_db)
    mock_db.query.return_value.all.return_value = actions

    response = client.get("/actions")

    assert response.status_code == 200
    assert len(response.json()) == 2
