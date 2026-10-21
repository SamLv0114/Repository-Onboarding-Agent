import re

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


def best_memory_claim(
    question: str,
    memory: ArchitectureMemory,
) -> ArchitectureClaim | None:

    qterms = terms(question)

    scored: list[tuple[int, ArchitectureClaim]] = []

    for claim in memory.claims:
        if claim.status != "valid" or not claim.evidence:
            continue

        key_terms = terms(" ".join(claim.keywords + [claim.title, claim.text]))

        score = len(qterms & key_terms)

        if score:
            scored.append((score, claim))

    scored.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    return scored[0][1] if scored else None
