"""Count LLM calls and tokens for everything run inside `track_usage()`.

Works like langchain_core's `get_usage_metadata_callback`, but also counts
calls and registers its context variable once instead of on every use. Code
that runs work in threads must copy the context (`contextvars.copy_context`)
so those calls are counted too.
"""

import threading
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from langchain_core.tracers.context import register_configure_hook

from app.models.usage import LLMUsage


class UsageTracker(BaseCallbackHandler):
    def __init__(self) -> None:
        super().__init__()
        self._lock = threading.Lock()
        self._usage = LLMUsage()

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        try:
            usage = response.generations[0][0].message.usage_metadata
        except (IndexError, AttributeError):
            usage = None
        with self._lock:
            self._usage.llm_calls += 1
            if usage:
                self._usage.input_tokens += usage.get("input_tokens", 0)
                self._usage.output_tokens += usage.get("output_tokens", 0)

    @property
    def usage(self) -> LLMUsage:
        with self._lock:
            return self._usage.model_copy()


_tracker: ContextVar[UsageTracker | None] = ContextVar("usage_tracker", default=None)
register_configure_hook(_tracker, inheritable=True)


@contextmanager
def track_usage() -> Iterator[UsageTracker]:
    tracker = UsageTracker()
    token = _tracker.set(tracker)
    try:
        yield tracker
    finally:
        _tracker.reset(token)
