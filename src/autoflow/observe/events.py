from datetime import datetime, timezone
from typing import Any, Mapping
from uuid import uuid4

from autoflow.types import ObservationEvent


def make_event(*, source: str, name: str, attributes: Mapping[str, Any]) -> ObservationEvent:
    return ObservationEvent(
        event_id=str(uuid4()),
        timestamp=datetime.now(timezone.utc),
        source=source,
        name=name,
        attributes=dict(attributes),
    )