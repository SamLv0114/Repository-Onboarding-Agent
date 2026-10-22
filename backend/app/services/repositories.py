"""Repository registry: the demo fixture, pinned repos, and repos added by link.

Pinned evaluation repos (data/repos.json) are cloned into data/repos/<id> by
scripts/fetch_repos.py; their memory lives at data/memory/<id>@<commit[:12]>.json
and is committed. Repos added from a GitHub link live under data/runtime/
(gitignored): the registry in repositories.json, sources in repos/<id>, and
memory in memory/<id>.json.
"""

import hashlib
import json
import threading
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from fastapi import HTTPException

from app.models.memory import ArchitectureMemory, EvidencePointer

DATA_ROOT = Path(__file__).resolve().parents[2] / "data"
REPO_ROOT = DATA_ROOT / "demo_repo"
MEMORY_FILE = DATA_ROOT / "architecture_memory.json"
MANIFEST_FILE = DATA_ROOT / "repos.json"
RUNTIME_ROOT = DATA_ROOT / "runtime"
SUPPORTED_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx", ".md", ".json"}
# Vendored, generated and documentation code isn't worth onboarding tokens.
DEFAULT_EXCLUDE = (
    "docs/*",
    "*node_modules/*",
    "dist/*",
    "build/*",
    "vendor/*",
    "*.min.js",
    "*.d.ts",
)

_registry_lock = threading.Lock()


@dataclass(frozen=True)
class RepositoryConfig:
    repository_id: str
    name: str
    root: Path
    memory_file: Path
    commit: str | None = None
    url: str | None = None
    exclude: tuple[str, ...] = ()


DEMO_REPOSITORY = RepositoryConfig(
    repository_id="demo-repo",
    name="Demo Repository",
    root=REPO_ROOT,
    memory_file=MEMORY_FILE,
)


@cache
def pinned_repositories() -> tuple[RepositoryConfig, ...]:
    entries = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))["repositories"]
    return tuple(
        RepositoryConfig(
            repository_id=entry["repository_id"],
            name=entry["name"],
            root=DATA_ROOT / "repos" / entry["repository_id"],
            memory_file=DATA_ROOT
            / "memory"
            / f"{entry['repository_id']}@{entry['commit'][:12]}.json",
            commit=entry["commit"],
            url=entry["url"],
            exclude=tuple(entry.get("exclude", [])),
        )
        for entry in entries
    )


def added_entries() -> list[dict]:
    """Registry entries (with onboarding status) for repos added from a link."""
    registry = RUNTIME_ROOT / "repositories.json"
    if not registry.is_file():
        return []
    return json.loads(registry.read_text(encoding="utf-8"))["repositories"]


def added_entry(repository_id: str) -> dict | None:
    return next(
        (e for e in added_entries() if e["repository_id"] == repository_id), None
    )


def update_added_entry(repository_id: str, **fields) -> dict:
    """Create or update a registry entry; safe to call from background threads."""
    with _registry_lock:
        entries = added_entries()
        entry = next((e for e in entries if e["repository_id"] == repository_id), None)
        if entry is None:
            entry = {"repository_id": repository_id}
            entries.append(entry)
        entry.update(fields)
        registry = RUNTIME_ROOT / "repositories.json"
        registry.parent.mkdir(parents=True, exist_ok=True)
        temporary = registry.with_suffix(".tmp")
        temporary.write_text(
            json.dumps({"repositories": entries}, indent=2), encoding="utf-8"
        )
        temporary.replace(registry)
    return entry


def list_repositories() -> tuple[RepositoryConfig, ...]:
    added = tuple(
        RepositoryConfig(
            repository_id=entry["repository_id"],
            name=entry["name"],
            root=RUNTIME_ROOT / "repos" / entry["repository_id"],
            memory_file=RUNTIME_ROOT / "memory" / f"{entry['repository_id']}.json",
            commit=entry.get("commit"),
            url=entry["url"],
            exclude=DEFAULT_EXCLUDE,
        )
        for entry in added_entries()
    )
    return (DEMO_REPOSITORY, *pinned_repositories(), *added)


def get_repository(repository_id: str) -> RepositoryConfig:
    for repository in list_repositories():
        if repository.repository_id == repository_id:
            return repository
    raise HTTPException(status_code=404, detail="Repository not found")


def get_memory(repository_id: str) -> ArchitectureMemory:
    repository = get_repository(repository_id)
    if not repository.memory_file.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"No architecture memory for {repository_id} yet; "
            "onboard the repository first",
        )
    memory = ArchitectureMemory.model_validate_json(
        repository.memory_file.read_text(encoding="utf-8")
    )
    if memory.repository_id != repository_id:
        raise HTTPException(status_code=404, detail="Repository not found")
    return memory


def resolve_repo_file(relative_path: str, root: Path = REPO_ROOT) -> Path:
    """Reject traversal, absolute paths, symlinks, and unsupported sources."""
    candidate = Path(relative_path)
    if (
        candidate.is_absolute()
        or ".." in candidate.parts
        or candidate.suffix not in SUPPORTED_SUFFIXES
    ):
        raise ValueError("Not a permitted repository-relative source path")
    # Strict containment after resolve also rejects symlinks escaping the root.
    root = root.resolve()
    resolved = (root / candidate).resolve(strict=True)
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise ValueError("File outside the allowed repository root")
    return resolved


def get_citation_excerpt(
    pointer: EvidencePointer, root: Path = REPO_ROOT
) -> str | None:
    try:
        lines = (
            resolve_repo_file(pointer.path, root)
            .read_text(encoding="utf-8")
            .splitlines()
        )
    except (OSError, ValueError, UnicodeError):
        return None
    if pointer.end_line > len(lines):
        return None
    return "\n".join(lines[pointer.start_line - 1 : pointer.end_line])


def content_hash(excerpt: str) -> str:
    """Fingerprint stored with each evidence pointer to detect changed code."""
    return hashlib.sha256(excerpt.encode("utf-8")).hexdigest()


def list_source_files(root: Path = REPO_ROOT) -> list[Path]:
    """Source files under a registered root. Not an arbitrary filesystem browser."""
    found: list[Path] = []
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if (
            any(part.startswith(".") for part in relative.parts)
            or path.is_symlink()
            or not path.is_file()
            or path.suffix not in SUPPORTED_SUFFIXES
        ):
            continue
        try:
            resolve_repo_file(relative.as_posix(), root)
            found.append(path)
        except (ValueError, OSError):
            continue
    return sorted(found)
