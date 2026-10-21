from app.models.qa import Citation
from app.models.sufficiency import SufficiencyDecision
from app.services.llm_sufficiency import (
    judge_memory_sufficiency,
)
from app.services.repositories import get_memory


class FakeJudge:
    def __init__(self, decision):
        self.decision = decision
        self.calls = 0

    def invoke(self, messages):
        self.calls += 1
        return self.decision


def test_insufficient_memory():
    memory = get_memory("demo-repo")
    claim = memory.claims[0]

    citations = [
        Citation(
            path="src/auth.py",
            start_line=4,
            end_line=8,
            preview="def require_user(token: str): ...",
        )
    ]

    fake_judge = FakeJudge(
        SufficiencyDecision(
            is_sufficient=False,
            reason="Token rotation is not described.",
            missing_information=["Refresh token rotation mechanism"],
        )
    )

    result = judge_memory_sufficiency(
        question="How does refresh token rotation work?",
        claim=claim,
        citations=citations,
        judge=fake_judge,
    )

    assert result.is_sufficient is False
    assert len(result.missing_information) == 1
    assert fake_judge.calls == 1


def test_no_evidence_skips_llm():
    memory = get_memory("demo-repo")
    claim = memory.claims[0]

    fake_judge = FakeJudge(
        SufficiencyDecision(
            is_sufficient=True,
            reason="Sufficient",
            missing_information=[],
        )
    )

    result = judge_memory_sufficiency(
        question="Where is authentication?",
        claim=claim,
        citations=[],
        judge=fake_judge,
    )

    assert result.is_sufficient is False
    assert fake_judge.calls == 0
