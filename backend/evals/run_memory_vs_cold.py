"""Memory-first vs cold search on SWE-QA questions for a pinned repository.

Each question is answered twice, once per strategy, with the same model.
Every run is written to a JSONL file (with the reference answer, for grading
later), followed by a summary of routes, LLM calls, tokens and latency, and
the break-even point against the memory's build cost.

Answers are NOT graded here. As a rough retrieval check, `file_hit` records
whether any cited file is one the reference answer mentions.

Run from backend/:
  python -m evals.run_memory_vs_cold --limit 10
"""

import argparse
import json
import random
import re
import statistics
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from app.agents.qa_graph import answer_question
from app.models.qa import QARequest
from app.services.repositories import get_memory
from app.services.llm import model_name

BACKEND_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_ROOT / ".env")

QUESTION_FILES = {"requests": BACKEND_ROOT / "evals/data/swe_qa_requests.jsonl"}
RESULTS_DIR = BACKEND_ROOT / "evals/results"
STRATEGIES = ("memory_first", "cold_search")
PYTHON_FILE = re.compile(r"[\w./-]*?(\w+\.py)\b")


def load_questions(repository_id: str, limit: int | None, seed: int) -> list[dict]:
    rows = [
        {"index": index, **json.loads(line)}
        for index, line in enumerate(
            QUESTION_FILES[repository_id].read_text(encoding="utf-8").splitlines()
        )
    ]
    if limit and limit < len(rows):
        rows = sorted(random.Random(seed).sample(rows, limit), key=lambda r: r["index"])
    return rows


def file_hit(citations: list[dict], reference: str) -> bool | None:
    """Whether the answer cites a file the reference names; None if it names none."""
    referenced = set(PYTHON_FILE.findall(reference))
    if not referenced:
        return None
    return any(Path(c["path"]).name in referenced for c in citations)


def run_one(repository_id: str, row: dict, strategy: str) -> dict:
    record = {
        "question_index": row["index"],
        "strategy": strategy,
        "question": row["question"],
        "reference_answer": row["answer"],
    }
    try:
        response = answer_question(
            QARequest(
                repository_id=repository_id,
                question=row["question"],
                strategy=strategy,
            )
        )
    except Exception as error:
        return {**record, "error": f"{type(error).__name__}: {error}"}
    citations = [c.model_dump(exclude={"preview"}) for c in response.citations]
    return {
        **record,
        "route": response.strategy_used,
        "answer_status": response.answer_status,
        "answer": response.answer,
        "citations": citations,
        "matched_claim_ids": response.matched_claim_ids,
        "elapsed_s": round(response.elapsed_ms / 1000, 2),
        **response.usage.model_dump(),
        "file_hit": file_hit(citations, row["answer"]),
    }


def summarize(records: list[dict], build_cost) -> dict:
    summary = {}
    for strategy in STRATEGIES:
        runs = [r for r in records if r["strategy"] == strategy and "error" not in r]
        if not runs:
            continue
        hits = [r["file_hit"] for r in runs if r["file_hit"] is not None]
        tokens = [r["input_tokens"] + r["output_tokens"] for r in runs]
        summary[strategy] = {
            "runs": len(runs),
            "errors": sum(1 for r in records if r["strategy"] == strategy) - len(runs),
            "routes": {
                route: sum(1 for r in runs if r["route"] == route)
                for route in sorted({r["route"] for r in runs})
            },
            "answered": sum(1 for r in runs if r["answer_status"] == "answered"),
            "file_hit_rate": round(sum(hits) / len(hits), 2) if hits else None,
            "mean_llm_calls": round(statistics.mean(r["llm_calls"] for r in runs), 2),
            "mean_tool_calls": round(statistics.mean(r["tool_calls"] for r in runs), 2),
            "mean_input_tokens": round(statistics.mean(r["input_tokens"] for r in runs)),
            "mean_output_tokens": round(
                statistics.mean(r["output_tokens"] for r in runs)
            ),
            "mean_total_tokens": round(statistics.mean(tokens)),
            "median_latency_s": round(statistics.median(r["elapsed_s"] for r in runs), 2),
            "mean_latency_s": round(statistics.mean(r["elapsed_s"] for r in runs), 2),
        }

    if build_cost and all(s in summary for s in STRATEGIES):
        build_tokens = build_cost.input_tokens + build_cost.output_tokens
        saved = (
            summary["cold_search"]["mean_total_tokens"]
            - summary["memory_first"]["mean_total_tokens"]
        )
        summary["build_cost"] = build_cost.model_dump()
        summary["tokens_saved_per_question"] = saved
        summary["break_even_questions"] = (
            round(build_tokens / saved, 1) if saved > 0 else None
        )
    return summary


def print_summary(summary: dict) -> None:
    rows = [
        ("Routes", "routes"),
        ("Answered", "answered"),
        ("Cites a referenced file", "file_hit_rate"),
        ("LLM calls / question", "mean_llm_calls"),
        ("Tool calls / question", "mean_tool_calls"),
        ("Input tokens / question", "mean_input_tokens"),
        ("Output tokens / question", "mean_output_tokens"),
        ("Total tokens / question", "mean_total_tokens"),
        ("Median latency (s)", "median_latency_s"),
        ("Mean latency (s)", "mean_latency_s"),
    ]
    print(f"\n{'':26}{'memory_first':>28}{'cold_search':>28}")
    for label, key in rows:
        values = [str(summary.get(s, {}).get(key, "-")) for s in STRATEGIES]
        print(f"{label:26}{values[0]:>28}{values[1]:>28}")
    if "break_even_questions" in summary:
        cost = summary["build_cost"]
        print(
            f"\nMemory build cost: {cost['input_tokens'] + cost['output_tokens']:,} "
            f"tokens in {cost['llm_calls']} calls"
        )
        print(f"Tokens saved per question: {summary['tokens_saved_per_question']:,}")
        print(f"Break-even after ~{summary['break_even_questions']} questions")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", default="requests", choices=QUESTION_FILES)
    parser.add_argument("--limit", type=int, help="Random sample of N questions")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    memory = get_memory(args.repository)
    questions = load_questions(args.repository, args.limit, args.seed)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output = RESULTS_DIR / f"{args.repository}-{stamp}.jsonl"

    print(
        f"{len(questions)} questions x {len(STRATEGIES)} strategies on "
        f"{args.repository}@{memory.snapshot_id[:12]} with {model_name()}"
    )
    records = []
    with output.open("w", encoding="utf-8") as file:
        for number, row in enumerate(questions, 1):
            for strategy in STRATEGIES:
                record = run_one(args.repository, row, strategy)
                records.append(record)
                file.write(json.dumps(record, ensure_ascii=False) + "\n")
                file.flush()
                outcome = record.get("error") or (
                    f"{record['route']}, {record['answer_status']}, "
                    f"{record['llm_calls']} calls, "
                    f"{record['input_tokens'] + record['output_tokens']} tokens, "
                    f"{record['elapsed_s']}s"
                )
                print(f"[{number}/{len(questions)}] Q{row['index']} {strategy}: {outcome}")

    summary = summarize(records, memory.build_cost)
    summary.update(
        repository=args.repository,
        snapshot_id=memory.snapshot_id,
        model=model_name(),
        question_indices=[row["index"] for row in questions],
        seed=args.seed,
        results_file=output.name,
    )
    output.with_suffix(".summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print_summary(summary)
    print(f"\nRuns: {output}\nSummary: {output.with_suffix('.summary.json')}")


if __name__ == "__main__":
    main()
