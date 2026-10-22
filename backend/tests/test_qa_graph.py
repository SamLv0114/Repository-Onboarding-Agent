import pytest
from fastapi import HTTPException

from app.agents.cold_search import keyword_search
from app.agents.qa_graph import answer_question, build_qa_graph
from app.models.answer import AnswerDraft
from app.models.qa import QARequest


class FakeAnswerGenerator:
    """Answers (or declines) in order; repeats the last decision when exhausted."""

    def __init__(self, *can_answer: bool):
        self.calls = 0
        self.decisions = list(can_answer) or [True]

    def invoke(self, messages):
        can_answer = self.decisions[min(self.calls, len(self.decisions) - 1)]
        self.calls += 1

        return AnswerDraft(
            can_answer=can_answer,
            answer=("Authentication uses require_user." if can_answer else ""),
            evidence_ids=([1] if can_answer else []),
        )


class CountingSearcher:
    def __init__(self):
        self.calls = 0

    def __call__(self, question, root):
        self.calls += 1
        return keyword_search(question, root)


def run(question, strategy, generator, searcher=None):
    graph = build_qa_graph(
        answer_generator=generator,
        searcher=searcher or CountingSearcher(),
    )
    return graph.invoke(
        {
            "question": question,
            "repository_id": "demo-repo",
            "strategy": strategy,
        }
    )


def test_memory_hit_costs_one_llm_call():
    generator = FakeAnswerGenerator(True)
    searcher = CountingSearcher()

    result = run(
        "Where is authentication implemented?", "memory_first", generator, searcher
    )

    assert result["route"] == "memory"
    assert result["answer_status"] == "answered"
    assert result["answer_citations"][0].path == "src/auth.py"
    assert result["claims"][0].claim_id == "auth-001"
    assert generator.calls == 1
    assert searcher.calls == 0


def test_memory_miss_falls_back_to_search():
    # Memory has an auth claim, but it doesn't cover token rotation.
    generator = FakeAnswerGenerator(False, True)
    searcher = CountingSearcher()

    result = run(
        "How does authentication refresh token rotation work?",
        "memory_first",
        generator,
        searcher,
    )

    assert result["route"] == "live_search"
    assert result["answer_status"] == "answered"
    assert generator.calls == 2
    assert searcher.calls == 1


def test_cold_search_skips_memory():
    generator = FakeAnswerGenerator(True)
    searcher = CountingSearcher()

    result = run(
        "Where is authentication implemented?", "cold_search", generator, searcher
    )

    assert result["route"] == "cold_search"
    assert result["claims"] == []
    assert generator.calls == 1
    assert searcher.calls == 1


def test_no_matching_memory_goes_straight_to_search():
    generator = FakeAnswerGenerator(True)

    result = run("Which payment webhook retries failures?", "memory_first", generator)

    assert result["route"] == "no_evidence"
    assert result["answer_status"] == "insufficient_evidence"
    # No memory and no search evidence: nothing to send to the LLM.
    assert generator.calls == 0


def test_graph_abstains_when_evidence_insufficient():
    generator = FakeAnswerGenerator(False)

    result = run(
        "How does authentication refresh token rotation work?",
        "memory_first",
        generator,
    )

    assert result["route"] in {"live_search", "no_evidence"}
    assert result["answer_status"] == "insufficient_evidence"
    assert result["answer_citations"] == []


def test_answer_question_reports_route_and_usage():
    graph = build_qa_graph(
        answer_generator=FakeAnswerGenerator(True), searcher=CountingSearcher()
    )

    response = answer_question(
        QARequest(
            repository_id="demo-repo",
            question="Where is authentication implemented?",
            strategy="memory_first",
        ),
        graph=graph,
    )

    assert response.strategy_used == "memory"
    assert response.answer_status == "answered"
    assert response.matched_claim_ids == ["auth-001"]
    assert response.is_demo is False
    assert response.usage is not None
    assert response.usage.tool_calls == 0


def test_answer_question_rejects_unknown_repository():
    with pytest.raises(HTTPException) as error:
        answer_question(
            QARequest(repository_id="not-a-repo", question="Where is auth?"),
            graph=build_qa_graph(answer_generator=FakeAnswerGenerator()),
        )

    assert error.value.status_code == 404


def test_memory_first_without_memory_searches_code(tmp_path, monkeypatch):
    from dataclasses import replace

    from app.services import repositories

    monkeypatch.setattr(
        repositories,
        "DEMO_REPOSITORY",
        replace(repositories.DEMO_REPOSITORY, memory_file=tmp_path / "none.json"),
    )
    generator = FakeAnswerGenerator(True)
    searcher = CountingSearcher()
    graph = build_qa_graph(answer_generator=generator, searcher=searcher)

    response = answer_question(
        QARequest(
            repository_id="demo-repo",
            question="Where is authentication implemented?",
            strategy="memory_first",
        ),
        graph=graph,
    )

    assert response.strategy_used == "live_search"
    assert response.answer_status == "answered"
    assert response.note is not None and "no architecture memory" in response.note
    assert searcher.calls == 1
    # Nothing to answer from memory, so the only LLM call is after the search.
    assert generator.calls == 1


def test_note_is_empty_when_memory_exists():
    graph = build_qa_graph(
        answer_generator=FakeAnswerGenerator(True), searcher=CountingSearcher()
    )

    response = answer_question(
        QARequest(
            repository_id="demo-repo",
            question="Where is authentication implemented?",
        ),
        graph=graph,
    )

    assert response.note is None
