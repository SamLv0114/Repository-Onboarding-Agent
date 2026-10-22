from pydantic import BaseModel, Field


class LLMUsage(BaseModel):
    """Token usage summed over every chat-model call in one unit of work."""

    llm_calls: int = Field(default=0, ge=0)
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)


class QAUsage(LLMUsage):
    """Usage for answering one question; tool_calls counts repository tool use."""

    tool_calls: int = Field(default=0, ge=0)
