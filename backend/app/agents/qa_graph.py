"""LangGraph integration placeholder — NOT wired into the demo API yet.

Planned graph:
  retrieve_memory -> assess_evidence -> [answer | live_search] -> answer -> END

When implementing, prefer a typed state with separate fields for:
- original question, repository ID, snapshot ID
- candidate claims, evidence, routing decision
- actual tool calls / token usage / errors
- final response + validated citations

Use `langgraph` (pip install -e '.[agent]') and write unit tests for both branches
before replacing `run_qa` in the API router. Importing LangGraph prematurely here
would make simple scaffold startup depend on the optional provider stack.
"""

import logging
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from app.models.answer import AnswerResult
from app.models.memory import ArchitectureClaim
from app.models.qa import Citation
from app.models.sufficiency import SufficiencyDecision
from app.services.answering import generate_grounded_answer
from app.services.citation_validator import (
    validate_source_citations,
)
from app.services.llm_sufficiency import judge_memory_sufficiency
from app.services.qa import memory_citations, search_repo
from app.services.repositories import get_memory
from app.services.retrieval import best_memory_claim

logger = logging.getLogger(__name__)


class QAState(TypedDict):
    # Input
    question: str
    repository_id: str
    strategy: Literal["memory_first", "cold_search"]

    # Memory retrieval
    claim: ArchitectureClaim | None
    citations: list[Citation]

    # LLM sufficiency judgment
    decision: SufficiencyDecision | None

    # Final routing decision
    route: Literal[
        "memory",
        "live_search",
        "cold_search",
        "no_evidence",
    ]

    answer: str
    # from retrieval
    answer_citations: list[Citation]
    answer_status: Literal[
        "answered",
        "insufficient_evidence",
        "invalid_citations",
        "generation_error",
    ]


def build_qa_graph(judge=None, answer_generator=None):

    # Node 1: Retrieve Architecture Memory
    def retrieve_memory_node(state: QAState):

        if state.get("strategy") == "cold_search":
            return {
                "claim": None,
                "citations": [],
            }

        memory = get_memory(state["repository_id"])

        claim = best_memory_claim(
            state["question"],
            memory,
        )

        citations = memory_citations(claim) if claim is not None else []

        return {
            "claim": claim,
            "citations": citations,
        }

    # Node 2: LLM Sufficiency Evaluation
    def assess_sufficiency_node(state: QAState):

        claim = state.get("claim")
        citations = state.get("citations", [])

        if claim is None or not citations:
            return {"decision": None}

        try:
            decision = judge_memory_sufficiency(
                question=state["question"],
                claim=claim,
                citations=citations,
                judge=judge,
            )
        except Exception:
            logger.exception("Sufficiency evaluation failed")
            return {"decision": None}

        return {"decision": decision}

    # Conditional Edge: Choose next node
    def choose_next_node(state: QAState) -> str:

        decision = state.get("decision")

        if (
            state.get("strategy") != "cold_search"
            and decision is not None
            and decision.is_sufficient
        ):
            return "use_memory"

        return "live_search"

    # Node 3A: Memory is sufficient
    def use_memory_node(state: QAState):
        return {"route": "memory"}

    # Node 3B: Memory is insufficient
    def live_search_node(state: QAState):

        citations = search_repo(state["question"])

        if not citations:
            route = "no_evidence"
        elif state.get("strategy") == "cold_search":
            route = "cold_search"
        else:
            route = "live_search"

        return {
            "citations": citations,
            "route": route,
        }

    def generate_answer_node(state: QAState):

        try:
            result = generate_grounded_answer(
                question=state["question"],
                citations=state.get("citations", []),
                generator=answer_generator,
            )

            return {
                "answer": result.answer,
                "answer_citations": result.citations,
                "answer_status": result.status,
            }

        except Exception:
            logger.exception("Answer generation failed")

            return {
                "answer": "Answer generation failed.",
                "answer_citations": [],
                "answer_status": "generation_error",
            }

    def validate_citations_node(state: QAState):

        if state.get("answer_status") != "answered":
            return {}

        result = AnswerResult(
            answer=state["answer"],
            citations=state.get("answer_citations", []),
            status="answered",
        )

        validated = validate_source_citations(result)

        return {
            "answer": validated.answer,
            "answer_citations": validated.citations,
            "answer_status": validated.status,
        }

    # Build the graph
    builder = StateGraph(QAState)

    builder.add_node(
        "retrieve_memory",
        retrieve_memory_node,
    )

    builder.add_node(
        "assess_sufficiency",
        assess_sufficiency_node,
    )

    builder.add_node(
        "validate_citations",
        validate_citations_node,
    )

    builder.add_node("use_memory", use_memory_node)
    builder.add_node("live_search", live_search_node)

    builder.add_edge(START, "retrieve_memory")

    builder.add_edge(
        "retrieve_memory",
        "assess_sufficiency",
    )

    builder.add_conditional_edges(
        "assess_sufficiency",
        choose_next_node,
        {
            "use_memory": "use_memory",
            "live_search": "live_search",
        },
    )

    builder.add_node(
        "generate_answer",
        generate_answer_node,
    )

    builder.add_edge(
        "use_memory",
        "generate_answer",
    )

    builder.add_edge(
        "live_search",
        "generate_answer",
    )

    builder.add_edge("generate_answer", "validate_citations")

    builder.add_edge(
        "validate_citations",
        END,
    )

    return builder.compile()
