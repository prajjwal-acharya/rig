from __future__ import annotations

import threading
from abc import ABC, abstractmethod

from rig.graph.model import Edge, Graph, GraphMetadata, Node
from rig.ir.repository import RepositoryIR


class DuplicateNodeError(ValueError):
    pass


class DuplicateEdgeError(ValueError):
    pass


class GraphBuilder(ABC):
    """Generic contract: consume a Repository IR, produce a Graph.

    No concrete implementation exists yet - this milestone only establishes
    the abstraction that future analyses (import graph, call graph, ...)
    will implement.
    """

    @property
    @abstractmethod
    def builder_id(self) -> str: ...

    @abstractmethod
    def build(self, repository: RepositoryIR) -> Graph: ...


class GraphAccumulator:
    """Incrementally assembles a Graph with O(1) duplicate detection,
    finalizing into an immutable, deterministically-ordered Graph."""

    def __init__(self, metadata: GraphMetadata | None = None) -> None:
        self._lock = threading.Lock()
        self._nodes: dict[str, Node] = {}
        self._edges: dict[str, Edge] = {}
        self._metadata = metadata or GraphMetadata()

    def add_node(self, node: Node) -> None:
        with self._lock:
            if node.id in self._nodes:
                raise DuplicateNodeError(f"node already added: {node.id!r}")
            self._nodes[node.id] = node

    def add_edge(self, edge: Edge) -> None:
        with self._lock:
            if edge.id in self._edges:
                raise DuplicateEdgeError(f"edge already added: {edge.id!r}")
            self._edges[edge.id] = edge

    def build(self) -> Graph:
        with self._lock:
            nodes = tuple(sorted(self._nodes.values(), key=lambda node: node.id))
            edges = tuple(sorted(self._edges.values(), key=lambda edge: edge.id))

        return Graph(nodes=nodes, edges=edges, metadata=self._metadata)
