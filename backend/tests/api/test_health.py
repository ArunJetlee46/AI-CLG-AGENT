from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["db"] == "ok"


def test_login_and_me() -> None:
    login = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    assert login.status_code == 200
    token = login.json()["access_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["role"] == "admin"


def test_chat_requires_auth() -> None:
    response = client.post("/api/v1/agents/chat", json={"message": "hello"})
    assert response.status_code == 401


def test_chat_returns_answer() -> None:
    login = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    token = login.json()["access_token"]
    response = client.post(
        "/api/v1/agents/chat",
        json={"message": "What courses are available?"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] in {"academic", "success", "resources", "knowledge"}
    assert body["answer"]
