from __future__ import annotations

import dataclasses

import pytest

from rig.graph.model import Edge, Graph, GraphIndex, GraphMetadata, Node, RelationshipType
from rig.graph.properties import Properties


def test_node_defaults() -> None:
    node = Node(id="n1", type="File")

    assert node.properties == Properties()


def test_node_is_immutable() -> None:
    node = Node(id="n1", type="File")

    with pytest.raises(dataclasses.FrozenInstanceError):
        node.type = "Package"  # type: ignore[misc]


def test_node_is_hashable() -> None:
    a = Node(id="n1", type="File")
    b = Node(id="n1", type="File")

    assert a == b
    assert hash(a) == hash(b)


def test_edge_holds_source_target_and_relationship() -> None:
    edge = Edge(id="e1", source="n1", target="n2", relationship=RelationshipType.CONTAINS)

    assert edge.source == "n1"
    assert edge.target == "n2"
    assert edge.relationship == RelationshipType.CONTAINS


def test_edge_is_immutable() -> None:
    edge = Edge(id="e1", source="n1", target="n2", relationship=RelationshipType.CONTAINS)

    with pytest.raises(dataclasses.FrozenInstanceError):
        edge.source = "n3"  # type: ignore[misc]


def test_relationship_type_has_expected_members() -> None:
    expected = {
        "CONTAINS",
        "DECLARES",
        "IMPORTS",
        "CALLS",
        "REFERENCES",
        "IMPLEMENTS",
        "EXTENDS",
        "OWNS",
        "EMBEDS",
        "ALIASES",
        "DECLARES_FIELD_OF_TYPE",
        "DECLARES_METHOD_PARAMETER",
        "DECLARES_METHOD_RETURNING",
        "DEPENDS_ON",
    }
    assert {member.value for member in RelationshipType} == expected


def test_graph_metadata_defaults() -> None:
    metadata = GraphMetadata()

    assert metadata.repository_id is None
    assert metadata.language_ids == ()
    assert metadata.generator is None
    assert metadata.generator_version is None
    assert metadata.created_at is None
    assert metadata.statistics == Properties()


def test_graph_metadata_is_immutable() -> None:
    metadata = GraphMetadata(repository_id="repo:1")

    with pytest.raises(dataclasses.FrozenInstanceError):
        metadata.repository_id = "repo:2"  # type: ignore[misc]


def test_graph_defaults_to_empty() -> None:
    graph = Graph()

    assert graph.nodes == ()
    assert graph.edges == ()
    assert graph.metadata == GraphMetadata()


def test_graph_is_immutable() -> None:
    graph = Graph()

    with pytest.raises(dataclasses.FrozenInstanceError):
        graph.nodes = ()  # type: ignore[misc]


def test_graph_index_looks_up_node_by_id() -> None:
    node = Node(id="n1", type="File")
    graph = Graph(nodes=(node,))

    index = GraphIndex(graph)

    assert index.get_node("n1") is node
    assert index.get_node("missing") is None


def test_graph_index_contains_and_len() -> None:
    graph = Graph(nodes=(Node(id="n1", type="File"), Node(id="n2", type="File")))

    index = GraphIndex(graph)

    assert "n1" in index
    assert "missing" not in index
    assert len(index) == 2


def test_graph_index_edges_from_and_to() -> None:
    edge = Edge(id="e1", source="n1", target="n2", relationship=RelationshipType.CONTAINS)
    graph = Graph(
        nodes=(Node(id="n1", type="File"), Node(id="n2", type="Function")),
        edges=(edge,),
    )

    index = GraphIndex(graph)

    assert index.edges_from("n1") == (edge,)
    assert index.edges_to("n2") == (edge,)
    assert index.edges_from("n2") == ()
    assert index.edges_to("n1") == ()


def test_graph_index_over_empty_graph() -> None:
    index = GraphIndex(Graph())

    assert len(index) == 0
    assert index.get_node("anything") is None
    assert index.edges_from("anything") == ()
    assert index.edges_to("anything") == ()


def test_graph_index_exposes_the_wrapped_graph() -> None:
    graph = Graph(nodes=(Node(id="n1", type="File"),))

    index = GraphIndex(graph)

    assert index.graph is graph
