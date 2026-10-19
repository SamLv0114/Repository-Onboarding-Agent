from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_repositories_and_memory():
    repos = client.get("/api/repositories")
    assert repos.status_code == 200
    assert repos.json()[0]["repository_id"] == "demo-repo"
    memory = client.get("/api/repositories/demo-repo/memory")
    assert memory.status_code == 200
    assert len(memory.json()["claims"]) == 3
    assert memory.json()["snapshot_id"] == "demo-snapshot-v1"


def test_memory_first_reuses_valid_claim_with_real_fixture_lines():
    response = client.post("/api/qa/ask", json={"repository_id":"demo-repo", "question":"Where is authentication implemented?", "strategy":"memory_first"})
    assert response.status_code == 200
    body = response.json()
    assert body["strategy_used"] == "memory"
    assert body["matched_claim_ids"] == ["auth-001"]
    assert any(c["path"] == "src/auth.py" for c in body["citations"])
    assert body["is_demo"] is True


def test_forced_cold_search_bypasses_memory():
    response = client.post("/api/qa/ask", json={"repository_id":"demo-repo", "question":"Where is authentication implemented?", "strategy":"cold_search"})
    assert response.status_code == 200
    assert response.json()["strategy_used"] in {"cold_search", "no_evidence"}
    assert response.json()["matched_claim_ids"] == []


def test_missing_memory_searches_source():
    response = client.post("/api/qa/ask", json={"repository_id":"demo-repo", "question":"Which lines raise PermissionError?"})
    assert response.status_code == 200
    assert response.json()["strategy_used"] == "live_search"
    assert any(c["path"] == "src/auth.py" for c in response.json()["citations"])


def test_unsupported_repository_rejected():
    response = client.post("/api/qa/ask", json={"repository_id":"not-a-repo", "question":"Where is authentication implemented?"})
    assert response.status_code == 404


def test_insufficient_question_rejected():
    response = client.post("/api/qa/ask", json={"repository_id":"demo-repo", "question":"hi"})
    assert response.status_code == 422


def test_benchmark_has_no_fabricated_numbers():
    response = client.get("/api/benchmarks/summary")
    assert response.status_code == 200
    assert response.json()["available"] is False
    assert response.json()["metrics"] == []
