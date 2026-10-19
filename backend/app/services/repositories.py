"""Fixture repository store; later replace with a Git commit-pinned repository adapter."""

from pathlib import Path
from fastapi import HTTPException
from app.models.memory import ArchitectureMemory, EvidencePointer

DATA_ROOT = Path(__file__).resolve().parents[2] / "data"
REPO_ROOT = DATA_ROOT / "demo_repo"
MEMORY_FILE = DATA_ROOT / "architecture_memory.json"
SUPPORTED_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx", ".md", ".json"}


def get_memory(repository_id: str) -> ArchitectureMemory:
    memory = ArchitectureMemory.model_validate_json(MEMORY_FILE.read_text(encoding="utf-8"))
    if memory.repository_id != repository_id:
        raise HTTPException(status_code=404, detail="Repository not found")
    return memory


def resolve_repo_file(relative_path: str) -> Path:
    """Reject traversal, absolute paths, symlinks, and unsupported sources."""
    candidate = Path(relative_path)
    if candidate.is_absolute() or ".." in candidate.parts or candidate.suffix not in SUPPORTED_SUFFIXES:
        raise ValueError("Not a permitted repository-relative source path")
    # Strict containment after resolve also rejects symlinks escaping the fixture.
    root = REPO_ROOT.resolve()
    resolved = (root / candidate).resolve(strict=True)
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise ValueError("File outside the allowed repository root")
    return resolved


def get_citation_excerpt(pointer: EvidencePointer) -> str | None:
    try:
        lines = resolve_repo_file(pointer.path).read_text(encoding="utf-8").splitlines()
    except (OSError, ValueError, UnicodeError):
        return None
    if pointer.end_line > len(lines):
        return None
    return "\n".join(lines[pointer.start_line - 1: pointer.end_line])


def list_source_files() -> list[Path]:
    """Small local fixture only. Do not use this as an arbitrary user-supplied filesystem browser."""
    found: list[Path] = []
    for path in REPO_ROOT.rglob("*"):
        if path.is_symlink() or not path.is_file() or path.suffix not in SUPPORTED_SUFFIXES:
            continue
        try:
            resolve_repo_file(path.relative_to(REPO_ROOT).as_posix())
            found.append(path)
        except (ValueError, OSError):
            continue
    return sorted(found)
