
from app.models.answer import AnswerResult
from app.models.memory import EvidencePointer
from app.services.repositories import get_citation_excerpt


def invalid_result() -> AnswerResult:
    return AnswerResult(
        answer="Unable to verify source citations.",
        citations=[],
        status="invalid_citations",
    )


def validate_source_citations(
    result: AnswerResult,
) -> AnswerResult:

    # No generated answer to validate
    if result.status != "answered":
        return result

    # An answered response must have citations
    if not result.citations:
        return invalid_result()

    for citation in result.citations:

        try:
            pointer = EvidencePointer(
                path=citation.path,
                start_line=citation.start_line,
                end_line=citation.end_line,
            )

            # Re-read the original source
            actual_source = get_citation_excerpt(pointer)

        except ValueError:
            return invalid_result()

        # File missing, invalid lines or changed content
        if actual_source is None:
            return invalid_result()

        if actual_source.strip() != citation.preview.strip():
            return invalid_result()

    return result
