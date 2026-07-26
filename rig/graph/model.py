from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from rig.graph.properties import Properties


class RelationshipType(str, Enum):
    CONTAINS = "CONTAINS"
    DECLARES = "DECLARES"
    IMPORTS = "IMPORTS"
    CALLS = "CALLS"
    REFERENCES = "REFERENCES"
    IMPLEMENTS = "IMPLEMENTS"
    EXTENDS = "EXTENDS"
    OWNS = "OWNS"
    EMBEDS = "EMBEDS"
    ALIASES = "ALIASES"
    DECLARES_FIELD_OF_TYPE = "DECLARES_FIELD_OF_TYPE"
    DECLARES_METHOD_PARAMETER = "DECLARES_METHOD_PARAMETER"
    DECLARES_METHOD_RETURNING = "DECLARES_METHOD_RETURNING"
    DEPENDS_ON = "DEPENDS_ON"


@dataclass(frozen=True, kw_only=True, slots=True)
class Node:
    # `type` is a deliberately open string, not an enum: the set of node
    # kinds is owned by whichever GraphBuilder produces them, not by this
    # core model - new node kinds must never require a change here.
    id: str
    type: str
    properties: Properties = field(default_factory=Properties)


@dataclass(frozen=True, kw_only=True, slots=True)
class Edge:
    id: str
    source: str
    target: str
    relationship: RelationshipType
    properties: Properties = field(default_factory=Properties)


@dataclass(frozen=True, kw_only=True, slots=True)
class GraphMetadata:
    repository_id: str | None = None
    language_ids: tuple[str, ...] = ()
    generator: str | None = None
    generator_version: str | None = None
    created_at: datetime | None = None
    statistics: Properties = field(default_factory=Properties)


@dataclass(frozen=True, kw_only=True, slots=True)
class Graph:
    nodes: tuple[Node, ...] = ()
    edges: tuple[Edge, ...] = ()
    metadata: GraphMetadata = field(default_factory=GraphMetadata)


class GraphIndex:
    """O(1) lookup view over an already-built Graph.

    Graph itself stays a plain, cheap-to-construct value object; this index
    is built once (by whoever needs fast lookups) and never mutates.
    """

    def __init__(self, graph: Graph) -> None:
        self._graph = graph
        self._nodes_by_id: Mapping[str, Node] = {node.id: node for node in graph.nodes}

        edges_by_source: dict[str, list[Edge]] = {}
        edges_by_target: dict[str, list[Edge]] = {}
        for edge in graph.edges:
            edges_by_source.setdefault(edge.source, []).append(edge)
            edges_by_target.setdefault(edge.target, []).append(edge)

        self._edges_by_source: Mapping[str, tuple[Edge, ...]] = {
            key: tuple(value) for key, value in edges_by_source.items()
        }
        self._edges_by_target: Mapping[str, tuple[Edge, ...]] = {
            key: tuple(value) for key, value in edges_by_target.items()
        }

    @property
    def graph(self) -> Graph:
        return self._graph

    def get_node(self, node_id: str) -> Node | None:
        return self._nodes_by_id.get(node_id)

    def edges_from(self, node_id: str) -> tuple[Edge, ...]:
        return self._edges_by_source.get(node_id, ())

    def edges_to(self, node_id: str) -> tuple[Edge, ...]:
        return self._edges_by_target.get(node_id, ())

    def __contains__(self, node_id: str) -> bool:
        return node_id in self._nodes_by_id

    def __len__(self) -> int:
        return len(self._nodes_by_id)
