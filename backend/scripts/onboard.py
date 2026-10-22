"""Build architecture memory for a repository pinned in data/repos.json.

Run from backend/: python -m scripts.onboard requests
"""

import argparse
import logging
from pathlib import Path

from dotenv import load_dotenv
from fastapi import HTTPException

from app.onboarding.explore import git_commit
from app.onboarding.generate import build_memory
from app.services.repositories import get_repository

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository_id")
    parser.add_argument(
        "--max-files", type=int, help="Only onboard the first N files (trial run)"
    )
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument(
        "--output",
        type=Path,
        help="Defaults to the repository's registered memory file",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    try:
        repository = get_repository(args.repository_id)
    except HTTPException:
        parser.error(f"Unknown repository: {args.repository_id}")
    if repository.commit is None:
        parser.error("Only repositories pinned in data/repos.json can be onboarded")
    head = git_commit(repository.root)
    if head != repository.commit:
        parser.error(
            f"{repository.root} is at {head}, expected {repository.commit}; "
            "run python -m scripts.fetch_repos"
        )
    if args.max_files and args.output is None:
        parser.error(
            "--max-files needs --output, so a partial memory is never "
            "mistaken for the real one"
        )

    memory = build_memory(
        repository.repository_id,
        repository.root,
        exclude=repository.exclude,
        max_files=args.max_files,
        workers=args.workers,
    )
    output = args.output or repository.memory_file
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(memory.model_dump_json(indent=2, exclude_none=True) + "\n")

    cost = memory.build_cost
    print(f"Wrote {len(memory.claims)} claims to {output}")
    print(
        f"Build cost: {cost.llm_calls} LLM calls, {cost.input_tokens} input + "
        f"{cost.output_tokens} output tokens, {cost.elapsed_s}s ({cost.model})"
    )


if __name__ == "__main__":
    main()
