from pathlib import Path
import pytest
from pydantic import ValidationError

from app.models.memory import EvidencePointer
from app.services.repositories import get_citation_excerpt, resolve_repo_file


def test_citation_is_real_fixture_source():
    excerpt = get_citation_excerpt(EvidencePointer(path="src/auth.py", start_line=4, end_line=8))
    assert excerpt is not None
    assert "require_user" in excerpt


def test_path_traversal_rejected():
    with pytest.raises(ValueError):
        resolve_repo_file("../../../../../etc/passwd")


def test_absolute_path_rejected():
    with pytest.raises(ValueError):
        resolve_repo_file("/tmp/secrets.py")


def test_invalid_line_range_rejected():
    with pytest.raises(ValidationError):
        EvidencePointer(path="src/auth.py", start_line=12, end_line=3)


def test_nonexistent_citation_is_not_used():
    assert get_citation_excerpt(EvidencePointer(path="src/auth.py", start_line=2, end_line=99999)) is None
