from __future__ import annotations

import threading
from collections.abc import Iterable

from rig.graph.builder import GraphBuilder


class DuplicateGraphBuilderError(ValueError):
    pass


class GraphBuilderRegistry:
    def __init__(self, builders: Iterable[GraphBuilder] = ()) -> None:
        self._lock = threading.Lock()
        self._by_id: dict[str, GraphBuilder] = {}
        for builder in builders:
            self.register(builder)

    def register(self, builder: GraphBuilder) -> None:
        with self._lock:
            existing = self._by_id.get(builder.builder_id)
            if existing is not None:
                raise DuplicateGraphBuilderError(
                    f"a graph builder is already registered with id {builder.builder_id!r}"
                )
            self._by_id[builder.builder_id] = builder

    def lookup(self, builder_id: str) -> GraphBuilder | None:
        return self._by_id.get(builder_id)

    def builders(self) -> tuple[GraphBuilder, ...]:
        return tuple(self._by_id.values())

    def __len__(self) -> int:
        return len(self._by_id)

    def __contains__(self, builder_id: str) -> bool:
        return builder_id in self._by_id
