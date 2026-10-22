# Repository Onboarding Agent — AMS 691

A lightweight **working full-stack scaffold** for the team's *Repository Onboarding Agent* proposal.

- **Backend:** FastAPI + Pydantic + LangGraph (memory-first QA, cold-search agent, onboarding)
- **Frontend:** React + TypeScript + Vite + Tailwind CSS v4 + shadcn/ui-style local components
- **Shared:** Architecture Memory JSON Schema and API contracts
- **Baseline behavior:** `memory_first` and `cold_search` modes exposed in the same API.

> IMPORTANT: This is a research prototype, not the finished agent. The benchmark harness is **not implemented** yet, so there are no accuracy or cost results. `demo-repo` is a synthetic fixture; nothing in it is evidence about a real repository.

## Prerequisites

- Python 3.11+ (3.12 recommended) and uv
- Node.js 20.19+ or 22.12+ and pnpm (Vite requirements may change; use a supported Node LTS)

## Run backend

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --reload-dir app --port 8000
```

`--reload-dir app` matters: repositories added from a link are cloned under `backend/data/`, and a plain `--reload` would restart the server (and kill the onboarding job) as soon as the clone writes `.py` files.

URLs: http://localhost:8000/docs and http://localhost:8000/api/health.

The API answers with the LangGraph agent, which needs `OPENAI_API_KEY` in `backend/.env` (model: `LLM_MODEL`, default `gpt-4.1-mini`). Set `QA_ENGINE=demo` to use the offline keyword demo instead.

## Evaluation repository and memory

Evaluation repositories are pinned in `backend/data/repos.json`. The first is **requests v2.32.5**, the commit whose line numbers match the SWE-QA `requests` questions.

```bash
cd backend
uv run python -m scripts.fetch_repos          # clone into data/repos/ and check out the pinned commit
uv run python -m scripts.onboard requests     # build memory -> data/memory/requests@b25c87d7cb8d.json
```

Onboarding makes one LLM call per source chunk (files over 400 lines are split at definitions) and one repository-level call. Evidence ranges are checked against the files and fingerprinted (`content_hash`); claims without valid evidence are dropped. The token cost and time are stored in the memory's `build_cost`. Commit the memory file used for experiments so everyone evaluates against the same one. For a trial run, use `--max-files 3 --output /tmp/trial.json`.

## Learn any GitHub repository

In the web app, paste a link like `https://github.com/owner/repo` into **Learn a repository**. The backend clones it into `backend/data/runtime/` (gitignored), onboards it in the background, and shows progress. When it's ready, it's selected automatically and you can ask questions. The same thing is available through the API as `POST /api/repositories {"url": ...}`; poll `GET /api/repositories/{id}` for `status` and `progress`.

- Only public `https://github.com/owner/repo` links are accepted. Cloning runs no repository code: no hooks, no submodules, no LFS, and symlinks are checked out as plain files.
- Python and JS/TS files are onboarded. `docs/`, `node_modules/`, `dist/`, `build/`, `vendor/`, minified files, and files over 300 KB are skipped.
- Repositories with more than 60,000 lines of source are refused to cap cost (about $0.03 of gpt-4.1-mini per 10k lines). Raise the limit with `MAX_ONBOARD_LINES` in `backend/.env`.
- One repository is onboarded at a time; others wait in the queue.

## Run frontend (second terminal)

```bash
cd frontend
pnpm install
pnpm run dev
```

Open http://localhost:5173. The Vite dev proxy forwards `/api` calls to `http://localhost:8000`.

## Run tests

```bash
cd backend
uv run pytest -q
```

And to verify frontend types/build after dependencies are installed:

```bash
cd frontend
pnpm run build
```

## Current API

- `GET /api/health` — simple health check
- `GET /api/repositories` — list configured test repositories
- `GET /api/repositories/{repository_id}/memory` — display architecture memory
- `GET /api/repositories` lists repositories with `status` (`ready`, `not_onboarded`, `queued`, `cloning`, `onboarding`, `failed`)
- `POST /api/repositories` — learn a GitHub repository from its link (runs in the background)
- `GET /api/repositories/{repository_id}` — status and onboarding progress
- `POST /api/qa/ask` — `memory_first` or `cold_search`; returns route, validated citations, `answer_status`, and `usage` (LLM calls, tokens, tool calls)
- `GET /api/benchmarks/summary` — placeholder; no invented measurements

Example:

```bash
curl -s -X POST http://localhost:8000/api/qa/ask \\
  -H 'Content-Type: application/json' \\
  -d '{"repository_id":"demo-repo","question":"Where is authentication implemented?","strategy":"memory_first"}'
```

## Team integration contracts

See `docs/INTEGRATION.md` and `shared/schemas/architecture-memory.schema.json`.

- **Onboarding / Exploration:** produces claim-based architecture memory with file-line pointers and a snapshot ID.
- **QA:** consumes those claims; searches the repo if relevant evidence is insufficient; returns `strategy_used`, `citations`, and a status.
- **Evaluation / Staleness:** can mark claim `status` as `stale` and compare forced cold search with memory-first on a fixed question set. Stable measurements will need a shared model, snapshot, token tracker and evaluation rubric.

## Next steps

1. Build and commit the requests memory (`scripts.onboard requests`).
2. Evaluation harness over SWE-QA requests questions: cold search vs memory-first vs memory-only, with accuracy, latency, tokens, and the break-even point against `build_cost`.
3. Staleness: compare `content_hash` and `git diff` ranges against claim evidence after a later commit.
4. Call graph (`ast`) to improve repository-level claims and staleness propagation.

## Project layout

```text
backend/
  app/
    api/routes/             health, repositories, qa, benchmarks
    agents/                 QA graph (memory first) + cold-search tool agent
    onboarding/             repository exploration + claim generation
    models/                 Pydantic data contracts
    services/               repository registry, retrieval, answering, citations, usage tracking
    main.py                 FastAPI app + CORS
  data/demo_repo/           toy codebase for deterministic development
  data/architecture_memory.json   hand-written memory for demo_repo (test fixture)
  data/repos.json           pinned evaluation repositories
  data/memory/              generated memory, one file per repository@commit
  scripts/                  fetch_repos, onboard, test_graph
  tests/                    FastAPI integration tests
frontend/
  src/components/ui/       locally defined shadcn-style primitives
  src/features/            chat, memory and benchmark screens
  src/lib/                 typed API client
shared/schemas/           JSON Schema contracts
docs/                     API contracts + incremental implementation plan
```
# repository-onboarding-agent
