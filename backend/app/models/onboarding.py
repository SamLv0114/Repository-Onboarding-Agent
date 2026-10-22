from pydantic import BaseModel, Field


class DraftEvidence(BaseModel):
    start_line: int = Field(description="First line of the supporting code.")
    end_line: int = Field(description="Last line of the supporting code.")


class DraftClaim(BaseModel):
    title: str = Field(description="Short name for the claim.")
    text: str = Field(description="One or two sentences stating the fact.")
    keywords: list[str] = Field(
        description="Identifiers and terms someone might search for."
    )
    evidence: list[DraftEvidence] = Field(
        description="Line ranges, from the numbered source, that support the claim."
    )


class FileClaimsDraft(BaseModel):
    """Structured output for one source chunk."""

    claims: list[DraftClaim]


class RepositoryClaimDraft(BaseModel):
    title: str = Field(description="Short name for the claim.")
    text: str = Field(description="One to three sentences stating the fact.")
    keywords: list[str] = Field(
        description="Identifiers and terms someone might search for."
    )
    supporting_claim_ids: list[str] = Field(
        description="IDs of the file claims this claim is based on."
    )


class RepositoryClaimsDraft(BaseModel):
    """Structured output for the repository-level summary."""

    claims: list[RepositoryClaimDraft]
