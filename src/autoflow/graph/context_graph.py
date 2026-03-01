from typing import Sequence

from autoflow.types import ContextGraphDelta, GraphNode, GraphEdge, ObservationEvent


class ContextGraphBuilder:
    def build_delta(self, events: Sequence[ObservationEvent]) -> ContextGraphDelta:
        nodes = []
        edges = []

        for ev in events:
            node_id = f"event:{ev.event_id}"
            nodes.append(
                GraphNode(
                    node_id=node_id,
                    node_type="event",
                    properties={
                        "name": ev.name,
                        "source": ev.source,
                        **ev.attributes,
                    },
                )
            )

        return ContextGraphDelta(nodes=nodes, edges=edges)