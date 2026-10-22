import json
import shutil
import subprocess

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import ingestion, repositories
from app.services.repositories import REPO_ROOT, added_entry, update_added_entry
from tests.test_onboarding import FakeFileGenerator, FakeRepositoryGenerator

client = TestClient(app)


@pytest.fixture(autouse=True)
def runtime_dir(tmp_path, monkeypatch):
    """Keep added repositories out of the real data/runtime directory."""
    monkeypatch.setattr(repositories, "RUNTIME_ROOT", tmp_path / "runtime")
    monkeypatch.setattr(ingestion, "_running", set())


@pytest.fixture
def source_repo(tmp_path):
    """A local git repository with the demo sources, standing in for GitHub."""
    source = tmp_path / "source"
    shutil.copytree(REPO_ROOT, source)
    for args in (
        ["init", "--quiet"],
        ["add", "."],
        ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "--quiet", "-m", "x"],
    ):
        subprocess.run(["git", "-C", str(source), *args], check=True)
    return source


def register(repository_id="acme-widgets"):
    update_added_entry(
        repository_id,
        name="acme/widgets",
        url="https://github.com/acme/widgets.git",
        commit=None,
        status="queued",
    )
    return repository_id


def ingest(repository_id, source):
    ingestion.run_ingestion(
        repository_id,
        clone_url=str(source),
        workers=1,
        file_generator=FakeFileGenerator(),
        repository_generator=FakeRepositoryGenerator(),
    )


@pytest.mark.parametrize(
    "url",
    [
        "https://github.com/psf/requests",
        "https://github.com/psf/requests.git",
        "https://github.com/psf/requests/",
        " https://github.com/pallets/flask ",
    ],
)
def test_accepts_github_repository_links(url):
    assert ingestion.parse_github_url(url)[0] in {"psf", "pallets"}


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/psf/requests",
        "https://gitlab.com/psf/requests",
        "https://github.com/psf",
        "https://github.com/psf/requests/tree/main",
        "https://github.com/psf/..",
        "file:///etc/passwd",
        "--upload-pack=touch /tmp/x",
    ],
)
def test_rejects_other_links(url):
    with pytest.raises(ValueError):
        ingestion.parse_github_url(url)


def test_add_repository_rejects_invalid_link():
    response = client.post("/api/repositories", json={"url": "https://example.com/x"})

    assert response.status_code == 422
    assert "github.com/owner/repo" in response.json()["detail"]


def test_add_repository_starts_background_onboarding(monkeypatch):
    started = []
    monkeypatch.setattr(ingestion, "run_in_background", started.append)

    response = client.post(
        "/api/repositories", json={"url": "https://github.com/Acme/Widgets"}
    )

    assert response.status_code == 202
    assert response.json()["repository_id"] == "acme-widgets"
    assert response.json()["status"] == "queued"
    assert started == ["acme-widgets"]
    # Adding the same link while it runs doesn't start a second job.
    client.post("/api/repositories", json={"url": "https://github.com/acme/widgets"})
    assert started == ["acme-widgets"]


def test_ingestion_clones_and_builds_memory(source_repo):
    repository_id = register()

    ingest(repository_id, source_repo)

    summary = client.get(f"/api/repositories/{repository_id}").json()
    assert summary["status"] == "ready", summary["error"]
    assert summary["memory_available"] is True
    assert summary["progress"] == {"done": 3, "total": 3}
    assert len(summary["snapshot_id"]) == 40

    memory = client.get(f"/api/repositories/{repository_id}/memory").json()
    assert memory["snapshot_id"] == summary["snapshot_id"]
    assert [c["claim_id"] for c in memory["claims"]] == [
        "repository-001",
        "src.auth-001",
    ]
    listed = [r["repository_id"] for r in client.get("/api/repositories").json()]
    assert repository_id in listed


def test_ingestion_enforces_size_limit(source_repo, monkeypatch):
    monkeypatch.setattr(ingestion, "MAX_ONBOARD_LINES", 5)
    repository_id = register()

    ingest(repository_id, source_repo)

    entry = added_entry(repository_id)
    assert entry["status"] == "failed"
    assert "limit is 5" in entry["error"]


def test_ingestion_reports_clone_failure(tmp_path):
    repository_id = register()

    ingest(repository_id, tmp_path / "does-not-exist")

    entry = added_entry(repository_id)
    assert entry["status"] == "failed"
    assert entry["error"].startswith("git clone failed")


def test_unfinished_job_after_restart_shows_as_failed():
    repository_id = register()
    update_added_entry(repository_id, status="onboarding")

    summary = client.get(f"/api/repositories/{repository_id}").json()

    assert summary["status"] == "failed"
    assert "Interrupted" in summary["error"]


def test_registry_file_is_valid_json_after_updates():
    register("a-b")
    register("c-d")
    update_added_entry("a-b", status="ready")

    registry = json.loads((repositories.RUNTIME_ROOT / "repositories.json").read_text())
    assert [e["status"] for e in registry["repositories"]] == ["ready", "queued"]
