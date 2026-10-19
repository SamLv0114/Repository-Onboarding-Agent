
from pydantic import BaseModel, Field, ConfigDict

# define a pydantic Model, this is the Schema for Data Returned by an LLM
class SufficiencyDecision(BaseModel):
    # Indicates that extra fields not defined in the schema are not permitted.
    model_config = ConfigDict(extra="forbid")

    is_sufficient: bool = Field(
        description=(
            "Whether the provided evidence fully "
            "answers the user's question."
        )
    )

    reason: str = Field(
        description=(
            "Brief explanation of why the evidence "
            "is sufficient or insufficient."
        )
    )

    missing_information: list[str] = Field(
        description=(
            "Information missing from the evidence. "
            "Use an empty list if sufficient."
        )
    )

# decision = SufficiencyDecision(
#     is_sufficient=False,
#     reason="Missing token rotation details",
#     missing_information=[
#         "How refresh tokens are rotated"
#     ]
# )

# print(decision.is_sufficient)
# print(decision.reason)
# print(decision.model_dump())