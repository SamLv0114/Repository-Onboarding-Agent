"""Learn a repository from a GitHub link: clone it, then onboard it in the background.

Status moves queued -> cloning -> onboarding -> ready (or failed) and is kept
in the runtime registry, so the frontend can poll it. Cloning never runs
code from the repository: no hooks, no submodules, no LFS downloads, and
symlinks are checked out as plain files.
"""

import logging
import os
import re
import shutil
import subprocess
import threading

from app.models.repository import OnboardingProgress, RepositorySummary
from app.onboarding.explore import git_commit, onboarding_files
from app.onboarding.generate import build_memory
from app.services.repositories import (
    DEMO_REPOSITORY,
    RepositoryConfig,
    added_entry,
    get_memory,
    get_repository,
    list_repositories,
    pinned_repositories,
    update_added_entry,
)

logger = logging.getLogger(__name__)

GITHUB_URL = re.compile(
    r"^https://github\.com/([A-Za-z0-9-]{1,39})/([A-Za-z0-9._-]{1,100}?)(?:\.git)?/?$"
)
# Roughly $0.03 of gpt-4.1-mini per 10k lines; raise it for bigger repos.
MAX_ONBOARD_LINES = int(os.getenv("MAX_ONBOARD_LINES", "60000"))
CLONE_TIMEOUT_S = 300
RUNNING_STATUSES = {"queued", "cloning", "onboarding"}

_running: set[str] = set()
_running_lock = threading.Lock()
# One onboarding at a time keeps cost and API rate limits predictable.
_onboarding_slot = threading.Semaphore(1)


class IngestionError(Exception):
    """A failure to show the user as-is."""


def parse_github_url(url: str) -> tuple[str, str]:
    match = GITHUB_URL.match(url.strip())
    if not match or match.group(2) in {".", ".."}:
        raise ValueError(
            "Enter a GitHub repository link like https://github.com/owner/repo"
        )
    return match.group(1), match.group(2)


def repository_summary(repository: RepositoryConfig) -> RepositorySummary:
    entry = added_entry(repository.repository_id)
    memory_available = repository.memory_file.is_file()
    progress = error = None
    if entry is None:
        status = "ready" if memory_available else "not_onboarded"
    else:
        status = entry["status"]
        error = entry.get("error")
        if entry.get("progress"):
            progress = OnboardingProgress(**entry["progress"])
        if status in RUNNING_STATUSES and repository.repository_id not in _running:
            status = "failed"
            error = "Interrupted (the server restarted). Add the link again to retry."

    snapshot_id = repository.commit or ""
    if not snapshot_id and memory_available:
        snapshot_id = get_memory(repository.repository_id).snapshot_id

    return RepositorySummary(
        repository_id=repository.repository_id,
        name=repository.name,
        url=repository.url,
        snapshot_id=snapshot_id,
        source_available=repository.root.is_dir(),
        memory_available=memory_available,
        status=status,
        progress=progress,
        error=error,
    )


def list_summaries() -> list[RepositorySummary]:
    return [repository_summary(repository) for repository in list_repositories()]


def start_ingestion(url: str) -> RepositorySummary:
    """Register the repository and onboard it in a background thread."""
    owner, name = parse_github_url(url)
    repository_id = f"{owner}-{name}".lower()
    if repository_id in {
        r.repository_id for r in (DEMO_REPOSITORY, *pinned_repositories())
    }:
        raise ValueError(f"{repository_id} is already a built-in repository")

    with _running_lock:
        entry = added_entry(repository_id)
        if repository_id in _running or (entry and entry["status"] == "ready"):
            return repository_summary(get_repository(repository_id))
        _running.add(repository_id)

    update_added_entry(
        repository_id,
        name=f"{owner}/{name}",
        url=f"https://github.com/{owner}/{name}.git",
        commit=None,
        status="queued",
        progress=None,
        error=None,
    )
    threading.Thread(
        target=run_in_background, args=(repository_id,), daemon=True
    ).start()
    return repository_summary(get_repository(repository_id))


def run_in_background(repository_id: str) -> None:
    try:
        with _onboarding_slot:
            run_ingestion(repository_id)
    finally:
        with _running_lock:
            _running.discard(repository_id)


def clone(url: str, repository: RepositoryConfig) -> None:
    if repository.root.exists():
        shutil.rmtree(repository.root)
    repository.root.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "git",
            "-c",
            "core.symlinks=false",
            "clone",
            "--quiet",
            "--filter=blob:none",  # full history for git log, files fetched lazily
            "--single-branch",
            "--no-tags",
            url,
            str(repository.root),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=CLONE_TIMEOUT_S,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_LFS_SKIP_SMUDGE": "1"},
    )


def run_ingestion(repository_id: str, clone_url: str | None = None, **build_options):
    """Clone and onboard one registered repository, recording status as it goes.

    `clone_url` and `build_options` (e.g. fake generators) are for tests.
    """
    repository = get_repository(repository_id)

    def update(**fields):
        update_added_entry(repository_id, **fields)

    try:
        update(status="cloning")
        clone(clone_url or repository.url, repository)
        commit = git_commit(repository.root)

        files = onboarding_files(repository.root, repository.exclude)
        if not files:
            raise IngestionError(
                "No supported source files (.py, .js, .jsx, .ts, .tsx) found"
            )
        lines = sum(
            len((repository.root / path).read_text(encoding="utf-8").splitlines())
            for path in files
        )
        if lines > MAX_ONBOARD_LINES:
            raise IngestionError(
                f"The repository has {lines:,} lines of source; the limit is "
                f"{MAX_ONBOARD_LINES:,} (set MAX_ONBOARD_LINES to raise it)"
            )

        update(commit=commit, status="onboarding", progress={"done": 0, "total": 0})
        memory = build_memory(
            repository_id,
            repository.root,
            exclude=repository.exclude,
            on_progress=lambda done, total: update(
                progress={"done": done, "total": total}
            ),
            **build_options,
        )
        repository.memory_file.parent.mkdir(parents=True, exist_ok=True)
        repository.memory_file.write_text(
            memory.model_dump_json(indent=2, exclude_none=True) + "\n",
            encoding="utf-8",
        )
        update(status="ready")
    except subprocess.CalledProcessError as error:
        message = error.stderr.strip().splitlines()[-1:] or ["unknown error"]
        update(status="failed", error=f"git clone failed: {message[0][:300]}")
    except subprocess.TimeoutExpired:
        update(status="failed", error="git clone timed out")
    except IngestionError as error:
        update(status="failed", error=str(error))
    except Exception as error:
        logger.exception("Ingestion failed for %s", repository_id)
        update(
            status="failed",
            error=f"Onboarding failed: {type(error).__name__}: {error}"[:300],
        )
