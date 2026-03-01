from contextlib import contextmanager
from typing import Iterator

try:
    from opentelemetry import trace
except Exception:
    trace = None


@contextmanager
def span(name: str) -> Iterator[None]:
    if trace is None:
        yield
        return

    tracer = trace.get_tracer("autoflow")
    with tracer.start_as_current_span(name):
        yield