from typing import Protocol, Sequence

from autoflow.types import ObservationEvent


class ObservationSink(Protocol):
    def write(self, events: Sequence[ObservationEvent]) -> None: ...


class InMemorySink:
    def __init__(self) -> None:
        self.events: list[ObservationEvent] = []

    def write(self, events: Sequence[ObservationEvent]) -> None:
        self.events.extend(events)