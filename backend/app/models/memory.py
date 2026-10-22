from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.models.usage import LLMUsage


class EvidencePointer(BaseModel):
    path: str = Field(min_length=1, description="Repository-relative source path")
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    content_hash: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
        description="SHA-256 of the cited lines when the memory was built",
    )

    @model_validator(mode="after")
    def check_range(self) -> "EvidencePointer":
        if self.end_line < self.start_line:
            raise ValueError("end_line must not precede start_line")
        return self


class ArchitectureClaim(BaseModel):
    claim_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    text: str = Field(min_length=1)
    keywords: list[str] = Field(default_factory=list)
    # "file" claims describe one source file; "repository" claims summarize
    # several file claims and reuse their evidence.
    level: Literal["repository", "file"] = "file"
    status: Literal["valid", "stale", "unknown"] = "unknown"
    evidence: list[EvidencePointer] = Field(default_factory=list)


class BuildCost(LLMUsage):
    """What it cost to build this memory, for the memory-vs-cold-search tradeoff."""

    model: str = Field(min_length=1)
    elapsed_s: float = Field(ge=0)


class ArchitectureMemory(BaseModel):
    repository_id: str = Field(min_length=1)
    # Git commit hash for generated memory; fixtures may use a placeholder.
    snapshot_id: str = Field(min_length=1)
    build_cost: BuildCost | None = None
    claims: list[ArchitectureClaim] = Field(default_factory=list)
