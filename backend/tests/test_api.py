from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app import main
from app.api import routes as routes_module
from app.chat import pipeline as pipeline_module
from app.config import Settings, get_settings

TEST_SETTINGS = Settings(invite_code="test-invite", jwt_secret="test-secret")


@pytest.fixture
def client() -> Iterator[TestClient]:
    main.app.dependency_overrides[get_settings] = lambda: TEST_SETTINGS
    routes_module.conversation_store.clear()
    routes_module.feedback_store.clear()
    with TestClient(main.app) as test_client:
        yield test_client
    main.app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    response = client.post("/api/auth", json={"inviteCode": "test-invite"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['token']}"}


# --- auth --------------------------------------------------------------


def test_auth_rejects_wrong_invite_code(client: TestClient) -> None:
    response = client.post("/api/auth", json={"inviteCode": "wrong"})
    assert response.status_code == 401


def test_auth_issues_a_token_for_the_correct_invite_code(client: TestClient) -> None:
    response = client.post("/api/auth", json={"inviteCode": "test-invite"})
    assert response.status_code == 200
    assert response.json()["token"]


# --- members -------------------------------------------------------------


def test_members_requires_auth(client: TestClient) -> None:
    response = client.get("/api/members")
    assert response.status_code == 401


def test_members_rejects_an_invalid_token(client: TestClient) -> None:
    response = client.get("/api/members", headers={"Authorization": "Bearer garbage"})
    assert response.status_code == 401


def test_members_lists_the_sample_group(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/api/members", headers=auth_headers)
    assert response.status_code == 200
    members = response.json()
    expected_ids = {"joao", "joana", "rita", "tomas", "ines", "diogo"}
    assert {m["id"] for m in members} == expected_ids
    joao = next(m for m in members if m["id"] == "joao")
    assert joao["nickname"] == "Jota"
    # camelCase on the wire, per docs/design.md § API contract
    assert "avatarUrl" in joao


# --- feedback --------------------------------------------------------------


def test_feedback_requires_auth(client: TestClient) -> None:
    response = client.post("/api/feedback", json={"messageId": "m1", "rating": "up"})
    assert response.status_code == 401


def test_feedback_accepts_a_rating(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post(
        "/api/feedback",
        json={"messageId": "m1", "rating": "down", "comment": "wrong city"},
        headers=auth_headers,
    )
    assert response.status_code == 204
    assert len(routes_module.feedback_store._records) == 1


def test_feedback_rejects_an_invalid_rating(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        "/api/feedback", json={"messageId": "m1", "rating": "sideways"}, headers=auth_headers
    )
    assert response.status_code == 422


# --- chat --------------------------------------------------------------


def test_chat_requires_auth(client: TestClient) -> None:
    response = client.post("/api/chat", json={"message": "hi"})
    assert response.status_code == 401


def test_chat_streams_tokens_then_a_done_event(
    client: TestClient, auth_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_stream(messages: list[dict[str, str]], settings: object) -> Iterator[str]:
        return iter(["Jota", " lives in Lisboa."])

    monkeypatch.setattr(pipeline_module, "stream_chat", fake_stream)
    response = client.post(
        "/api/chat", json={"message": "Where does Jota live?"}, headers=auth_headers
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    body = response.text
    assert "event: token" in body
    assert '"token": "Jota"' in body
    assert "event: done" in body
    assert '"member": "joao"' in body  # sources from real retrieval


def test_chat_persists_history_for_a_follow_up(
    client: TestClient, auth_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        pipeline_module, "stream_chat", lambda messages, settings: iter(["João is the oldest."])
    )
    first = client.post(
        "/api/chat",
        json={"message": "Who is the oldest in the group?"},
        headers=auth_headers,
    )
    conversation_id = first.text.split('"conversationId": "')[1].split('"')[0]

    captured_history: list[object] = []

    def capture_rewrite(message: str, history: list[object], settings: object) -> str:
        captured_history.extend(history)
        return message

    monkeypatch.setattr(pipeline_module, "rewrite_query", capture_rewrite)
    client.post(
        "/api/chat",
        json={"message": "And what does he do?", "conversationId": conversation_id},
        headers=auth_headers,
    )
    assert len(captured_history) == 2  # the first turn's user + assistant messages
