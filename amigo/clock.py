"""Wall seconds per step of one question, for a latency study (AMIGO and the baselines)."""

import contextvars
import time


class Clock:
    """Wall seconds per step of one question, for a latency study: lap(step) books the
    time since the last lap (or the start) to `step`; a step met twice adds up."""

    def __init__(self):
        self.seconds: dict[str, float] = {}
        self.started = self._last = time.monotonic()

    def lap(self, step: str) -> None:
        now = time.monotonic()
        self.seconds[step] = round(self.seconds.get(step, 0.0) + now - self._last, 3)
        self._last = now


CLOCK: contextvars.ContextVar[Clock | None] = contextvars.ContextVar("clock", default=None)


def lap(step: str) -> None:
    """Book a step on the clock run.py started for this thread's question; steps whose name
    starts with "llm" hold LLM calls. Nothing happens when no clock runs."""
    if (clock := CLOCK.get()) is not None:
        clock.lap(step)
