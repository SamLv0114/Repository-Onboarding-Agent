from app.agents.qa_graph import build_qa_graph
from app.models.answer import AnswerDraft
from app.models.sufficiency import SufficiencyDecision


class FakeJudge:
    def __init__(self, sufficient: bool):
        self.calls = 0
        self.sufficient = sufficient

    def invoke(self, messages):
        self.calls += 1

        return SufficiencyDecision(
            is_sufficient=self.sufficient,
            reason="Test decision",
            missing_information=(
                [] if self.sufficient else ["Missing implementation details"]
            ),
        )

class FakeAnswerGenerator:
    def __init__(self, can_answer=True):
        self.calls = 0
        self.can_answer = can_answer

    def invoke(self, messages):
        self.calls += 1

        return AnswerDraft(
            can_answer=self.can_answer,
            answer=("Authentication uses require_user." if self.can_answer else ""),
            evidence_ids=([1] if self.can_answer else []),
        )


def test_sufficient_memory_route():
    judge = FakeJudge(sufficient=True)
    graph = build_qa_graph(
        judge=judge,
        answer_generator=FakeAnswerGenerator(),
    )

    result = graph.invoke(
        {
            "question": "Where is authentication implemented?",
            "repository_id": "demo-repo",
            "strategy": "memory_first",
        }
    )

    assert result["route"] == "memory"
    assert result["decision"].is_sufficient is True
    assert judge.calls == 1


def test_insufficient_memory_route():
    judge = FakeJudge(sufficient=False)
    graph = build_qa_graph(
        judge=judge,
        answer_generator=FakeAnswerGenerator(),
    )

    result = graph.invoke(
        {
            "question": ("How does authentication refresh token rotation work?"),
            "repository_id": "demo-repo",
            "strategy": "memory_first",
        }
    )

    assert result["route"] in {
        "live_search",
        "no_evidence",
    }
    assert judge.calls == 1


def test_cold_search_skips_llm_judge():
    judge = FakeJudge(sufficient=True)
    graph = build_qa_graph(
        judge=judge,
        answer_generator=FakeAnswerGenerator(),
    )

    result = graph.invoke(
        {
            "question": "Where is authentication implemented?",
            "repository_id": "demo-repo",
            "strategy": "cold_search",
        }
    )

    assert result["route"] == "cold_search"
    assert judge.calls == 0


def test_no_matching_memory_skips_judge():
    judge = FakeJudge(sufficient=True)
    graph = build_qa_graph(
        judge=judge,
        answer_generator=FakeAnswerGenerator(),
    )

    result = graph.invoke(
        {
            "question": "Which payment webhook retries failures?",
            "repository_id": "demo-repo",
            "strategy": "memory_first",
        }
    )

    assert result["route"] == "no_evidence"
    assert judge.calls == 0


def test_graph_generates_grounded_answer():

    judge = FakeJudge(sufficient=True)
    answer_generator = FakeAnswerGenerator()

    graph = build_qa_graph(
        judge=judge,
        answer_generator=answer_generator,
    )

    result = graph.invoke(
        {
            "question": "Where is authentication implemented?",
            "repository_id": "demo-repo",
            "strategy": "memory_first",
        }
    )

    assert result["route"] == "memory"
    assert result["answer_status"] == "answered"
    assert result["answer_citations"]
    assert result["answer_citations"][0].path == "src/auth.py"
    assert answer_generator.calls == 1


def test_graph_abstains_when_evidence_insufficient():

    judge = FakeJudge(sufficient=False)
    answer_generator = FakeAnswerGenerator(can_answer=False)

    graph = build_qa_graph(
        judge=judge,
        answer_generator=answer_generator,
    )

    result = graph.invoke(
        {
            "question": ("How does authentication refresh token rotation work?"),
            "repository_id": "demo-repo",
            "strategy": "memory_first",
        }
    )

    assert result["route"] in {
        "live_search",
        "no_evidence",
    }

    assert result["answer_status"] == ("insufficient_evidence")
    assert result["answer_citations"] == []
