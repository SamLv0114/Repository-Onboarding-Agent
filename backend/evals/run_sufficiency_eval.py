
from pathlib import Path
from time import perf_counter

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from app.models.sufficiency import SufficiencyDecision
from app.services.repositories import get_memory
from app.services.qa import memory_citations
from app.services.llm_sufficiency import (
    judge_memory_sufficiency,
)

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

# Human-labeled evaluation examples
CASES = [
    ("Where is authentication implemented?", True),
    ("Which helper validates the demo token?", True),
    ("What token value does require_user accept?", True),
    ("What does require_user return on success?", True),
    ("How does refresh token rotation work?", False),
    ("How are user passwords hashed?", False),
    ("How are authentication sessions stored in Redis?", False),
    ("Which OAuth provider is used for login?", False),
]


def main():
    memory = get_memory("demo-repo")

    claim = next(
        c for c in memory.claims
        if c.claim_id == "auth-001"
    )

    citations = memory_citations(claim)

    # Reuse one model client for all cases
    llm = ChatOpenAI(
        model="gpt-4.1-mini",
        temperature=0,
        timeout=20,
        max_retries=1,
    )

    judge = llm.with_structured_output(
        SufficiencyDecision,
        method="json_schema",
    )

    tp = tn = fp = fn = 0
    failures = 0

    for question, expected in CASES:
        started = perf_counter()

        try:
            decision = judge_memory_sufficiency(
                question=question,
                claim=claim,
                citations=citations,
                judge=judge,
            )
        except Exception as error:
            failures += 1
            print(f"ERROR: {question} — {type(error).__name__}")
            continue

        predicted = decision.is_sufficient
        elapsed = perf_counter() - started

        if expected and predicted:
            tp += 1
        elif not expected and not predicted:
            tn += 1
        elif not expected and predicted:
            fp += 1
        else:
            fn += 1

        print(f"\nQuestion: {question}")
        print(f"Expected: {expected}")
        print(f"Predicted: {predicted}")
        print(f"Correct: {expected == predicted}")
        print(f"Reason: {decision.reason}")
        print(f"Latency: {elapsed:.2f}s")

    completed = tp + tn + fp + fn
    accuracy = (tp + tn) / completed if completed else 0
    fpr = fp / (fp + tn) if (fp + tn) else 0

    print("\n===== EVALUATION =====")
    print(f"Accuracy: {accuracy:.2%}")
    print(f"False Positive Rate: {fpr:.2%}")
    print(f"TP={tp}, TN={tn}, FP={fp}, FN={fn}")
    print(f"Completed={completed}, Errors={failures}")


if __name__ == "__main__":
    main()
