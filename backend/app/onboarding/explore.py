"""Deterministic first pass over a repository: files, README, history, chunks.

No LLM calls happen here, so this part of onboarding costs no tokens.
"""

import fnmatch
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.services.repositories import list_source_files

ONBOARD_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx"}
MAX_CHUNK_LINES = 400
# Larger files are almost always generated or bundled code.
MAX_FILE_BYTES = 300_000
README_NAMES = ("README.md", "README.rst", "README.txt", "README")
MAX_README_CHARS = 8000
RECENT_COMMITS = 30

# Python: a top-level or method-level definition; chunks are cut just before
# one. Other languages are cut at top-level statements after a blank line.
DEFINITION = re.compile(r"^( {4})?(async def |def |class )")


@dataclass(frozen=True)
class SourceChunk:
    path: str
    start_line: int
    end_line: int
    total_lines: int
    lines: tuple[str, ...]

    def numbered(self) -> str:
        return "\n".join(
            f"{number:>5}| {line}"
            for number, line in enumerate(self.lines, self.start_line)
        )


@dataclass(frozen=True)
class RepositorySnapshot:
    commit: str | None
    files: tuple[str, ...]
    readme: str | None
    recent_commits: tuple[str, ...]


def git_output(root: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip()


def git_commit(root: Path) -> str | None:
    """HEAD of the repository rooted exactly at `root`, not an enclosing one."""
    toplevel = git_output(root, "rev-parse", "--show-toplevel")
    if toplevel is None or Path(toplevel).resolve() != root.resolve():
        return None
    return git_output(root, "rev-parse", "HEAD")


def read_readme(root: Path) -> str | None:
    for name in README_NAMES:
        path = root / name
        if path.is_file() and not path.is_symlink():
            return path.read_text(encoding="utf-8", errors="replace")[:MAX_README_CHARS]
    return None


def onboarding_files(root: Path, exclude: tuple[str, ...] = ()) -> list[str]:
    files = []
    for path in list_source_files(root):
        relative = path.relative_to(root).as_posix()
        if (
            path.suffix in ONBOARD_SUFFIXES
            and path.stat().st_size <= MAX_FILE_BYTES
            and not any(fnmatch.fnmatch(relative, pattern) for pattern in exclude)
            and is_utf8(path)
        ):
            files.append(relative)
    return files


def is_utf8(path: Path) -> bool:
    try:
        path.read_text(encoding="utf-8")
    except UnicodeError:
        return False
    return True


def explore(root: Path, exclude: tuple[str, ...] = ()) -> RepositorySnapshot:
    commit = git_commit(root)
    log = (
        git_output(
            root,
            "log",
            f"-n{RECENT_COMMITS}",
            "--format=%h %ad %s",
            "--date=short",
        )
        if commit
        else None
    )
    return RepositorySnapshot(
        commit=commit,
        files=tuple(onboarding_files(root, exclude)),
        readme=read_readme(root),
        recent_commits=tuple(log.splitlines()) if log else (),
    )


def definition_start(lines: list[str], index: int) -> int:
    """Index where the definition at `index` starts, including its decorators."""
    indent = lines[index][: len(lines[index]) - len(lines[index].lstrip())]
    start = index
    previous = index - 1
    while previous >= 0:
        line = lines[previous]
        if line.startswith(indent + "@"):
            start = previous
        elif not line.strip() or not (
            line.startswith(indent + " ") or line.startswith(indent + ")")
        ):
            # Anything other than a decorator or its continuation lines.
            break
        previous -= 1
    return start


def cut_points(lines: list[str], python: bool) -> list[int]:
    if python:
        points = {
            definition_start(lines, index)
            for index, line in enumerate(lines)
            if DEFINITION.match(line)
        }
    else:
        points = {
            index
            for index, line in enumerate(lines)
            if index and line[:1].strip() and not lines[index - 1].strip()
        }
    return sorted(points)


def chunk_ranges(
    lines: list[str], max_lines: int = MAX_CHUNK_LINES, python: bool = True
) -> list[tuple[int, int]]:
    """1-based inclusive ranges of at most `max_lines`, cut at definitions."""
    cuts = cut_points(lines, python)
    ranges = []
    start = 0
    while len(lines) - start > max_lines:
        cut = max(
            (point for point in cuts if start < point <= start + max_lines),
            default=start + max_lines,
        )
        ranges.append((start + 1, cut))
        start = cut
    if start < len(lines):
        ranges.append((start + 1, len(lines)))
    return ranges


def chunk_file(root: Path, path: str) -> list[SourceChunk]:
    lines = (root / path).read_text(encoding="utf-8").splitlines()
    return [
        SourceChunk(
            path=path,
            start_line=start,
            end_line=end,
            total_lines=len(lines),
            lines=tuple(lines[start - 1 : end]),
        )
        for start, end in chunk_ranges(lines, python=path.endswith(".py"))
    ]
