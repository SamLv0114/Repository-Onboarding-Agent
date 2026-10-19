
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_simple_auth_question_uses_memory():
    response = client.post(
        "/api/qa/ask",
        json={
            "repository_id": "demo-repo",
            "question": "Where is authentication implemented?",
            "strategy": "memory_first",
        },
    )

    assert response.status_code == 200
    assert response.json()["strategy_used"] == "memory"


def test_refresh_token_question_falls_back():
    response = client.post(
        "/api/qa/ask",
        json={
            "repository_id": "demo-repo",
            "question": (
                "How does authentication "
                "refresh token rotation work?"
            ),
            "strategy": "memory_first",
        },
    )

    assert response.status_code == 200
    assert response.json()["strategy_used"] != "memory"


def test_cold_search_skips_memory():
    response = client.post(
        "/api/qa/ask",
        json={
            "repository_id": "demo-repo",
            "question": "Where is authentication implemented?",
            "strategy": "cold_search",
        },
    )

    assert response.status_code == 200
    assert response.json()["strategy_used"] != "memory"
