"""Memory-first QA graph.

  retrieve_memory -> answer_from_memory -> END                    (memory hit)
                  \\-> search -> generate_answer -> END            (miss, or cold)

A memory hit costs one LLM call. Answering from the retrieved claims doubles
as the sufficiency check: the generator sets can_answer=false when the
evidence doesn't cover the question, and the graph falls back to search.
Every answer's citations are re-read from source before it is returned.

`answer_question` runs the graph for the API and the evaluation harness,
recording latency, LLM calls, tokens and tool calls.
"""

import logging
from time import perf_counter
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents.cold_search import cold_search
from app.models.answer import AnswerResult
from app.models.memory import ArchitectureClaim
from app.models.qa import NO_MEMORY_NOTE, Citation, QARequest, QAResponse
from app.models.usage import QAUsage
from app.services.answering import generate_grounded_answer
from app.services.citation_validator import (
    validate_source_citations,
)
from app.services.qa import memory_citations
from app.services.repositories import get_memory, get_repository
from app.services.retrieval import top_memory_claims
from app.services.usage import track_usage

logger = logging.getLogger(__name__)

MEMORY_CLAIMS = 3


class QAState(TypedDict):
    # Input
    question: str
    repository_id: str
    strategy: Literal["memory_first", "cold_search"]

    # Memory retrieval, later replaced by search results on fallback
    claims: list[ArchitectureClaim]
    citations: list[Citation]
    tool_calls: int
    # memory_first was asked for, but no memory has been built yet
    memory_missing: bool

    # Final routing decision
    route: Literal[
        "memory",
        "live_search",
        "cold_search",
        "no_evidence",
    ]

    answer: str
    # Validated subset of the evidence the answer cites
    answer_citations: list[Citation]
    answer_status: Literal[
        "answered",
        "insufficient_evidence",
        "invalid_citations",
        "generation_error",
    ]


def build_qa_graph(answer_generator=None, searcher=None):
    """`searcher(question, root) -> SearchResult`; defaults to the cold-search agent."""

    searcher = searcher or cold_search

    def grounded_answer(
        state: QAState,
        citations: list[Citation],
        claims: list[ArchitectureClaim] | None = None,
    ) -> AnswerResult:
        try:
            result = generate_grounded_answer(
                question=state["question"],
                citations=citations,
                generator=answer_generator,
                claims=claims,
            )
        except Exception:
            logger.exception("Answer generation failed")
            return AnswerResult(
                answer="Answer generation failed.",
                citations=[],
                status="generation_error",
            )
        root = get_repository(state["repository_id"]).root
        return validate_source_citations(result, root)

    def answer_fields(result: AnswerResult) -> dict:
        return {
            "answer": result.answer,
            "answer_citations": result.citations,
            "answer_status": result.status,
        }

    # Node 1: Retrieve the top claims and re-read their evidence
    def retrieve_memory_node(state: QAState):

        if state.get("strategy") == "cold_search":
            return {"claims": [], "citations": []}

        repository = get_repository(state["repository_id"])
        if not repository.memory_file.is_file():
            # Not onboarded yet (or still onboarding): search the code instead.
            return {"claims": [], "citations": [], "memory_missing": True}

        root = repository.root
        memory = get_memory(state["repository_id"])
        claims = top_memory_claims(state["question"], memory, k=MEMORY_CLAIMS)

        citations: list[Citation] = []
        for claim in claims:
            for citation in memory_citations(claim, root):
                if citation not in citations:
                    citations.append(citation)

        return {"claims": claims, "citations": citations}

    def after_retrieval(state: QAState) -> str:
        return "answer_from_memory" if state["citations"] else "search"

    # Node 2: One LLM call that answers from memory or declines
    def answer_from_memory_node(state: QAState):
        result = grounded_answer(state, state["citations"], claims=state["claims"])
        if result.status != "answered":
            return {"answer_status": result.status}
        return {"route": "memory", **answer_fields(result)}

    def after_memory_answer(state: QAState) -> str:
        return END if state.get("route") == "memory" else "search"

    # Node 3: Search the repository (cold search, or memory-first fallback)
    def search_node(state: QAState):
        root = get_repository(state["repository_id"]).root
        result = searcher(state["question"], root)

        if not result.citations:
            route = "no_evidence"
        elif state.get("strategy") == "cold_search":
            route = "cold_search"
        else:
            route = "live_search"

        return {
            "citations": result.citations,
            "tool_calls": result.tool_calls,
            "route": route,
        }

    # Node 4: Answer from the search evidence
    def generate_answer_node(state: QAState):
        return answer_fields(grounded_answer(state, state["citations"]))

    # Build the graph
    builder = StateGraph(QAState)

    builder.add_node("retrieve_memory", retrieve_memory_node)
    builder.add_node("answer_from_memory", answer_from_memory_node)
    builder.add_node("search", search_node)
    builder.add_node("generate_answer", generate_answer_node)

    builder.add_edge(START, "retrieve_memory")
    builder.add_conditional_edges(
        "retrieve_memory",
        after_retrieval,
        {"answer_from_memory": "answer_from_memory", "search": "search"},
    )
    builder.add_conditional_edges(
        "answer_from_memory",
        after_memory_answer,
        {END: END, "search": "search"},
    )
    builder.add_edge("search", "generate_answer")
    builder.add_edge("generate_answer", END)

    return builder.compile()


def answer_question(request: QARequest, graph=None) -> QAResponse:
    get_repository(request.repository_id)  # 404 before spending any tokens
    graph = graph or build_qa_graph()

    started = perf_counter()
    with track_usage() as tracker:
        state = graph.invoke(
            {
                "question": request.question,
                "repository_id": request.repository_id,
                "strategy": request.strategy,
            }
        )
    route = state["route"]

    return QAResponse(
        repository_id=request.repository_id,
        question=request.question,
        answer=state["answer"],
        strategy_used=route,
        citations=state["answer_citations"],
        matched_claim_ids=(
            [claim.claim_id for claim in state["claims"]] if route == "memory" else []
        ),
        is_demo=False,
        elapsed_ms=(perf_counter() - started) * 1000,
        answer_status=state["answer_status"],
        usage=QAUsage(
            **tracker.usage.model_dump(), tool_calls=state.get("tool_calls", 0)
        ),
        note=NO_MEMORY_NOTE if state.get("memory_missing") else None,
    )
