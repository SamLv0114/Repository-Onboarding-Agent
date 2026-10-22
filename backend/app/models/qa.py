from typing import Literal

from pydantic import BaseModel, Field

from app.models.usage import QAUsage


class QARequest(BaseModel):
    repository_id: str = Field(min_length=1)
    question: str = Field(min_length=3, max_length=2000)
    strategy: Literal["memory_first", "cold_search"] = "memory_first"


class Citation(BaseModel):
    path: str
    start_line: int
    end_line: int
    preview: str


# Pydantic Data Model
class QAResponse(BaseModel):
    repository_id: str = Field(min_length=1)
    question: str = Field(min_length=3, max_length=2000)
    answer: str
    strategy_used: Literal["memory", "live_search", "cold_search", "no_evidence"]
    citations: list[Citation] = Field(default_factory=list)
    matched_claim_ids: list[str] = Field(default_factory=list)
    is_demo: bool = True
    elapsed_ms: float = Field(ge=0)
    # Set by the agent engine only; the demo engine leaves them empty.
    answer_status: (
        Literal[
            "answered",
            "insufficient_evidence",
            "invalid_citations",
            "generation_error",
        ]
        | None
    ) = None
    usage: QAUsage | None = None
    # Explains a route the caller didn't ask for, e.g. no memory built yet.
    note: str | None = None


NO_MEMORY_NOTE = (
    "This repository has no architecture memory yet, so the code was "
    "searched directly."
)
