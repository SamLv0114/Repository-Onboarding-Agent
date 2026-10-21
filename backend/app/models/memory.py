from typing import Literal

from pydantic import BaseModel, Field, model_validator


class EvidencePointer(BaseModel):
    path: str = Field(min_length=1, description="Repository-relative source path")
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)

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
    status: Literal["valid", "stale", "unknown"] = "unknown"
    evidence: list[EvidencePointer] = Field(default_factory=list)


class ArchitectureMemory(BaseModel):
    repository_id: str = Field(min_length=1)
    snapshot_id: str = Field(min_length=1)
    claims: list[ArchitectureClaim] = Field(default_factory=list)
