
from app.models.answer import AnswerResult
from app.models.memory import EvidencePointer
from app.models.qa import Citation
from app.services.citation_validator import (
    validate_source_citations,
)
from app.services.repositories import get_citation_excerpt


def make_answer(preview: str) -> AnswerResult:
    return AnswerResult(
        answer="Authentication uses require_user.",
        citations=[
            Citation(
                path="src/auth.py",
                start_line=4,
                end_line=8,
                preview=preview,
            )
        ],
        status="answered",
    )


def test_valid_citation():
    pointer = EvidencePointer(
        path="src/auth.py",
        start_line=4,
        end_line=8,
    )

    actual = get_citation_excerpt(pointer)
    assert actual is not None

    result = validate_source_citations(
        make_answer(actual)
    )

    assert result.status == "answered"


def test_citation_content_mismatch():
    result = validate_source_citations(
        make_answer("Fake source code")
    )

    assert result.status == "invalid_citations"
    assert result.citations == []


def test_invalid_line_numbers():
    result = AnswerResult(
        answer="Some answer",
        citations=[
            Citation(
                path="src/auth.py",
                start_line=999,
                end_line=1000,
                preview="Nonexistent code",
            )
        ],
        status="answered",
    )

    validated = validate_source_citations(result)

    assert validated.status == "invalid_citations"
