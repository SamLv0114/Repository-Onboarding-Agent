from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from app.services.usage import track_usage


def fake_model(calls: int) -> GenericFakeChatModel:
    return GenericFakeChatModel(
        messages=iter(
            AIMessage(
                content="ok",
                usage_metadata={
                    "input_tokens": 10,
                    "output_tokens": 2,
                    "total_tokens": 12,
                },
            )
            for _ in range(calls)
        )
    )


def test_tracks_calls_and_tokens():
    model = fake_model(2)

    with track_usage() as tracker:
        model.invoke("a")
        model.invoke("b")

    assert tracker.usage.llm_calls == 2
    assert tracker.usage.input_tokens == 20
    assert tracker.usage.output_tokens == 4


def test_calls_outside_the_context_are_not_counted():
    model = fake_model(2)

    with track_usage() as tracker:
        model.invoke("a")
    model.invoke("b")

    assert tracker.usage.llm_calls == 1


def test_counts_calls_in_threads_that_copy_the_context():
    model = fake_model(4)

    with track_usage() as tracker:
        with ThreadPoolExecutor(max_workers=4) as pool:
            for future in [
                pool.submit(copy_context().run, model.invoke, "x") for _ in range(4)
            ]:
                future.result()

    assert tracker.usage.llm_calls == 4
    assert tracker.usage.input_tokens == 40
