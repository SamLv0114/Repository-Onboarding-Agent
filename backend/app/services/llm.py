"""One place to choose the chat model, so every experiment uses the same one."""

import os

from langchain_openai import ChatOpenAI

DEFAULT_MODEL = "gpt-4.1-mini"


def model_name() -> str:
    return os.getenv("LLM_MODEL", DEFAULT_MODEL)


def chat_model(**kwargs) -> ChatOpenAI:
    options = {"timeout": 60, "max_retries": 2, **kwargs}
    return ChatOpenAI(model=model_name(), temperature=0, **options)
