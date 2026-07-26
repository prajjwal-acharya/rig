from __future__ import annotations

from pathlib import Path

import pytest

from rig.graph.builder import DuplicateEdgeError, DuplicateNodeError, GraphAccumulator, GraphBuilder
from rig.graph.model import Edge, Graph, GraphMetadata, Node, RelationshipType
from rig.ir.repository import RepositoryIR


class FakeGraphBuilder(GraphBuilder):
    def __init__(self, builder_id: str = "fake") -> None:
        self._builder_id = builder_id

    @property
    def builder_id(self) -> str:
        return self._builder_id

    def build(self, repository: RepositoryIR) -> Graph:
        return Graph()


def test_graph_builder_is_abstract() -> None:
    with pytest.raises(TypeError):
        GraphBuilder()  # type: ignore[abstract]


def test_fake_graph_builder_can_build_an_empty_graph() -> None:
    builder = FakeGraphBuilder()
    repository = RepositoryIR(id="repo:1", root=Path("/repos/example"))

    graph = builder.build(repository)

    assert graph == Graph()


def test_add_node_and_build() -> None:
    accumulator = GraphAccumulator()
    node = Node(id="n1", type="File")

    accumulator.add_node(node)
    graph = accumulator.build()

    assert graph.nodes == (node,)


def test_add_edge_and_build() -> None:
    accumulator = GraphAccumulator()
    edge = Edge(id="e1", source="n1", target="n2", relationship=RelationshipType.CONTAINS)

    accumulator.add_edge(edge)
    graph = accumulator.build()

    assert graph.edges == (edge,)


def test_duplicate_node_id_raises() -> None:
    accumulator = GraphAccumulator()
    accumulator.add_node(Node(id="n1", type="File"))

    with pytest.raises(DuplicateNodeError):
        accumulator.add_node(Node(id="n1", type="File"))


def test_duplicate_edge_id_raises() -> None:
    accumulator = GraphAccumulator()
    edge = Edge(id="e1", source="n1", target="n2", relationship=RelationshipType.CONTAINS)
    accumulator.add_edge(edge)

    with pytest.raises(DuplicateEdgeError):
        accumulator.add_edge(edge)


def test_build_on_empty_accumulator_produces_empty_graph() -> None:
    accumulator = GraphAccumulator()

    graph = accumulator.build()

    assert graph.nodes == ()
    assert graph.edges == ()


def test_build_orders_nodes_and_edges_deterministically() -> None:
    accumulator = GraphAccumulator()
    accumulator.add_node(Node(id="n2", type="File"))
    accumulator.add_node(Node(id="n1", type="File"))
    accumulator.add_edge(
        Edge(id="e2", source="a", target="b", relationship=RelationshipType.CONTAINS)
    )
    accumulator.add_edge(
        Edge(id="e1", source="a", target="b", relationship=RelationshipType.CONTAINS)
    )

    graph = accumulator.build()

    assert [n.id for n in graph.nodes] == ["n1", "n2"]
    assert [e.id for e in graph.edges] == ["e1", "e2"]


def test_build_is_deterministic_across_repeated_calls() -> None:
    accumulator = GraphAccumulator()
    accumulator.add_node(Node(id="n1", type="File"))

    first = accumulator.build()
    second = accumulator.build()

    assert first == second


def test_accumulator_preserves_provided_metadata() -> None:
    metadata = GraphMetadata(repository_id="repo:1", generator="test")
    accumulator = GraphAccumulator(metadata=metadata)

    graph = accumulator.build()

    assert graph.metadata == metadata


def test_accumulator_defaults_to_empty_metadata() -> None:
    accumulator = GraphAccumulator()

    graph = accumulator.build()

    assert graph.metadata == GraphMetadata()
