import math
import re
from collections import Counter

from app.models.memory import (
    ArchitectureClaim,
    ArchitectureMemory,
)

STOP_WORDS = {
    "a",
    "an",
    "the",
    "is",
    "are",
    "was",
    "what",
    "which",
    "where",
    "when",
    "how",
    "who",
    "why",
    "do",
    "does",
    "in",
    "on",
    "at",
    "for",
    "to",
    "of",
    "and",
    "or",
    "it",
    "this",
    "that",
    "can",
    "you",
    "me",
    "my",
    "code",
    "repository",
    "implemented",
    "implementation",
    "handled",
    "handle",
}


def terms(text: str) -> set[str]:
    return {
        t
        for t in re.findall(r"[a-zA-Z_][a-zA-Z_0-9]*", text.lower())
        if len(t) > 2 and t not in STOP_WORDS
    }


def claim_terms(claim: ArchitectureClaim) -> set[str]:
    paths = [pointer.path for pointer in claim.evidence]
    return terms(" ".join(claim.keywords + [claim.title, claim.text] + paths))


def top_memory_claims(
    question: str,
    memory: ArchitectureMemory,
    k: int = 3,
) -> list[ArchitectureClaim]:
    """Valid claims ranked by overlap with the question, rarer terms weighing more."""

    qterms = terms(question)

    candidates = [
        (claim, claim_terms(claim))
        for claim in memory.claims
        if claim.status == "valid" and claim.evidence
    ]

    # Inverse document frequency over claims: a term shared by every claim
    # (like the package name) says little about which claim is relevant.
    frequency = Counter(term for _, key_terms in candidates for term in key_terms)

    scored: list[tuple[float, ArchitectureClaim]] = []

    for claim, key_terms in candidates:
        overlap = qterms & key_terms
        if overlap:
            score = sum(
                math.log((len(candidates) + 1) / frequency[term]) for term in overlap
            )
            scored.append((score, claim))

    scored.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    return [claim for _, claim in scored[:k]]


def best_memory_claim(
    question: str,
    memory: ArchitectureMemory,
) -> ArchitectureClaim | None:
    claims = top_memory_claims(question, memory, k=1)
    return claims[0] if claims else None
