# Repository Onboarding Agent — AMS 691

A lightweight **working full-stack scaffold** for the team's *Repository Onboarding Agent* proposal.

- **Backend:** FastAPI + Pydantic (mocked memory-first QA now; LangGraph extension point included)
- **Frontend:** React + TypeScript + Vite + Tailwind CSS v4 + shadcn/ui-style local components
- **Shared:** Architecture Memory JSON Schema and API contracts
- **Baseline behavior:** `memory_first` and `cold_search` modes exposed in the same API.

> IMPORTANT: This is a development scaffold, **not** the finished research agent. It uses an intentionally small, synthetic repository. Responses are deterministic previews without a real LLM, and its current token/quality benchmark metrics are **not implemented**. Nothing in the sample files is evidence about a real repository.

## Prerequisites

- Python 3.11+ (3.12 recommended) and uv
- Node.js 20.19+ or 22.12+ and pnpm (Vite requirements may change; use a supported Node LTS)

## Run backend

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

URLs: http://localhost:8000/docs and http://localhost:8000/api/health.

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
- `POST /api/qa/ask` — **demo** memory-first and cold-search paths; citations link to fixture line ranges
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

1. Confirm JSON contract with teammates.
2. Replace `app/services/qa.py` demo keyword heuristics with evidence-sufficiency routing.
3. Wire `app/agents/qa_graph.py` into `/api/qa/ask` and introduce a real LLM only after baseline behavior is tested.
4. Introduce a real repository reading interface with commit-pinned source references.
5. Implement evaluation harness and staleness checks; never treat token cost placeholders as results.

## Project layout

```text
backend/
  app/
    api/routes/             health, repositories, qa, benchmarks
    agents/                 LangGraph extension point
    models/                 Pydantic data contracts
    services/               fixture repository + demo QA implementation
    main.py                 FastAPI app + CORS
  data/demo_repo/           toy codebase for deterministic development
  data/architecture_memory.json
  tests/                    FastAPI integration tests
frontend/
  src/components/ui/       locally defined shadcn-style primitives
  src/features/            chat, memory and benchmark screens
  src/lib/                 typed API client
shared/schemas/           JSON Schema contracts
docs/                     API contracts + incremental implementation plan
```
# repository-onboarding-agent
