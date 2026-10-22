from typing import Literal

from pydantic import BaseModel, Field

RepositoryStatus = Literal[
    "ready",
    "not_onboarded",
    "queued",
    "cloning",
    "onboarding",
    "failed",
]


class OnboardingProgress(BaseModel):
    done: int = Field(default=0, ge=0)
    total: int = Field(default=0, ge=0)


class RepositorySummary(BaseModel):
    repository_id: str
    name: str
    url: str | None = None
    snapshot_id: str
    source_available: bool
    memory_available: bool
    status: RepositoryStatus
    progress: OnboardingProgress | None = None
    error: str | None = None


class AddRepositoryRequest(BaseModel):
    url: str = Field(min_length=1, max_length=300)
