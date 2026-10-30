from fastapi.testclient import TestClient

from app.main import app


def test_health() -> None:
    # TestClient only runs FastAPI's lifespan (which builds the member
    # index) when used as a context manager.
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["indexed_chunks"] > 0
