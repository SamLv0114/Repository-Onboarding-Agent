"""Deterministic QA demo. Replace retrieval/routing with LangGraph agent in a later step.

This module deliberately DOES NOT invoke an LLM or claim semantic correctness.
It's a functional baseline for testing API wiring and the memory-first decision path.
"""

import logging
import os
from pathlib import Path
from time import perf_counter

from dotenv import load_dotenv

from app.models.memory import ArchitectureClaim
from app.models.qa import Citation, QARequest, QAResponse
from app.services.llm_sufficiency import (
    judge_memory_sufficiency,
)
from app.services.repositories import (
    REPO_ROOT,
    get_citation_excerpt,
    get_memory,
    list_source_files,
)
from app.services.retrieval import best_memory_claim, terms
from app.services.sufficiency import is_memory_sufficient

load_dotenv(Path(__file__).resolve().parents[2] / ".env")
logger = logging.getLogger(__name__)


def memory_citations(claim: ArchitectureClaim) -> list[Citation]:
    citations: list[Citation] = []
    for pointer in claim.evidence:
        snippet = get_citation_excerpt(pointer)
        if snippet is not None:
            citations.append(
                Citation(
                    path=pointer.path,
                    start_line=pointer.start_line,
                    end_line=pointer.end_line,
                    preview=snippet,
                )
            )
    return citations


def search_repo(question: str, *, max_results: int = 3) -> list[Citation]:
    """Primitive line-based search: only a fallback placeholder, not multi-hop search."""
    qterms = terms(question)
    if not qterms:
        return []
    hits: list[tuple[int, Citation]] = []
    for path in list_source_files():
        try:
            if path.stat().st_size > 100_000:
                continue
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError):
            continue
        for lineno, line in enumerate(lines, 1):
            score = len(qterms & terms(line))
            if score:
                hits.append(
                    (
                        score,
                        Citation(
                            path=path.relative_to(REPO_ROOT).as_posix(),
                            start_line=lineno,
                            end_line=lineno,
                            preview=line.strip(),
                        ),
                    )
                )
    hits.sort(key=lambda hit: (-hit[0], hit[1].path, hit[1].start_line))
    return [item[1] for item in hits[:max_results]]


def run_qa(request: QARequest) -> QAResponse:
    started = perf_counter()
    memory = get_memory(request.repository_id)
    if request.strategy == "memory_first":
        claim = best_memory_claim(request.question, memory)
        if claim is not None:
            citations = memory_citations(claim)

            mode = os.getenv("QA_SUFFICIENCY_MODE", "keyword")

            if mode == "llm":
                try:
                    decision = judge_memory_sufficiency(
                        question=request.question, claim=claim, citations=citations
                    )
                    print(decision.model_dump_json(indent=2))
                    sufficient = decision.is_sufficient
                except Exception:
                    logger.exception("Sufficiency LLM evaluation failed")
                    # Conservative fallback:
                    # do not trust the memory on failure.
                    sufficient = False

            elif mode == "keyword":
                sufficient = is_memory_sufficient(
                    question=request.question,
                    claim=claim,
                    citations=citations,
                )

            else:
                raise ValueError(f"Unknown sufficiency mode: {mode}")

            if sufficient:
                # Use memory
                return QAResponse(
                    repository_id=request.repository_id,
                    question=request.question,
                    answer=(
                        f"DEMO — memory claim: {claim.text} "
                        "(Evidence relevance not yet LLM-verified.)"
                    ),
                    strategy_used="memory",
                    citations=citations,
                    matched_claim_ids=[claim.claim_id],
                    elapsed_ms=(perf_counter() - started) * 1000,
                )
    # Live search
    citations = search_repo(request.question)
    route = "cold_search" if request.strategy == "cold_search" else "live_search"
    if citations:
        answer = "DEMO — repository search found candidate source lines. Review cited snippets; generative QA is not yet implemented."
    else:
        answer = "No matching evidence in the demo repository. I cannot answer this question from the available source."
        route = "no_evidence"
    return QAResponse(
        repository_id=request.repository_id,
        question=request.question,
        answer=answer,
        strategy_used=route,
        citations=citations,
        elapsed_ms=(perf_counter() - started) * 1000,
    )
