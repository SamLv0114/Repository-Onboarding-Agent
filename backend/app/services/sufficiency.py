
from app.models.memory import ArchitectureClaim
from app.models.qa import Citation
from app.services.retrieval import terms


def is_memory_sufficient(
    question: str,
    claim: ArchitectureClaim,
    citations: list[Citation],
) -> bool:

    # 1. Claim has to be valid
    if claim.status != "valid":
        return False

    # 2. Must include a readable citation
    if not citations:
        return False

    # 3. Extract the keywords from the question
    question_terms = terms(question)

    if not question_terms:
        return False

    # 4. Extract keywords from the claim
    claim_terms = terms(
        " ".join(
            claim.keywords + [
                claim.title,
                claim.text
            ]
        )
    )

    # 5. Only if all the keywords from the question
    # appear in the Claim is reuse provisionally permitted.
    return question_terms.issubset(claim_terms)
