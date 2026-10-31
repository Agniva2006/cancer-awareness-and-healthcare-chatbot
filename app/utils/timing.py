"""Timing helpers."""

import time
from contextlib import contextmanager


class Timer:
    """Simple elapsed-time stopwatch (seconds)."""

    def __init__(self):
        self.start = time.perf_counter()

    def elapsed(self) -> float:
        return round(time.perf_counter() - self.start, 3)


@contextmanager
def timed(label: str = "operation"):
    """Context manager that logs how long a block took."""
    start = time.perf_counter()
    try:
        yield
    finally:
        import logging

        logging.getLogger(__name__).info(
            "%s took %.3fs", label, time.perf_counter() - start
        )
