from __future__ import annotations

import json
from datetime import datetime, timezone

from rig.graph.model import Edge, Graph, GraphMetadata, Node, RelationshipType
from rig.graph.properties import Properties
from rig.graph.serialization import (
    edge_to_dict,
    graph_to_dict,
    graph_to_json,
    metadata_to_dict,
    node_to_dict,
)


def test_node_to_dict() -> None:
    node = Node(id="n1", type="File", properties=Properties.of(path="main.go"))

    result = node_to_dict(node)

    assert result == {"id": "n1", "type": "File", "properties": {"path": "main.go"}}


def test_edge_to_dict() -> None:
    edge = Edge(
        id="e1",
        source="n1",
        target="n2",
        relationship=RelationshipType.CONTAINS,
        properties=Properties.of(weight=1),
    )

    result = edge_to_dict(edge)

    assert result == {
        "id": "e1",
        "source": "n1",
        "target": "n2",
        "relationship": "CONTAINS",
        "properties": {"weight": 1},
    }


def test_metadata_to_dict_with_all_fields() -> None:
    metadata = GraphMetadata(
        repository_id="repo:1",
        language_ids=("go", "python"),
        generator="test-builder",
        generator_version="1.0.0",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        statistics=Properties.of(node_count=10),
    )

    result = metadata_to_dict(metadata)

    assert result["repository_id"] == "repo:1"
    assert result["language_ids"] == ["go", "python"]
    assert result["generator"] == "test-builder"
    assert result["generator_version"] == "1.0.0"
    assert result["created_at"] == "2026-01-01T00:00:00+00:00"
    assert result["statistics"] == {"node_count": 10}


def test_metadata_to_dict_with_defaults() -> None:
    result = metadata_to_dict(GraphMetadata())

    assert result["repository_id"] is None
    assert result["language_ids"] == []
    assert result["created_at"] is None
    assert result["statistics"] == {}


def test_graph_to_dict_combines_nodes_edges_and_metadata() -> None:
    node = Node(id="n1", type="File")
    edge = Edge(id="e1", source="n1", target="n1", relationship=RelationshipType.OWNS)
    graph = Graph(nodes=(node,), edges=(edge,), metadata=GraphMetadata(repository_id="repo:1"))

    result = graph_to_dict(graph)

    assert result["nodes"] == [node_to_dict(node)]
    assert result["edges"] == [edge_to_dict(edge)]
    assert result["metadata"]["repository_id"] == "repo:1"


def test_graph_to_dict_on_empty_graph() -> None:
    result = graph_to_dict(Graph())

    assert result == {
        "nodes": [],
        "edges": [],
        "metadata": {
            "repository_id": None,
            "language_ids": [],
            "generator": None,
            "generator_version": None,
            "created_at": None,
            "statistics": {},
        },
    }


def test_graph_to_json_produces_valid_json() -> None:
    graph = Graph(nodes=(Node(id="n1", type="File"),))

    text = graph_to_json(graph)

    assert json.loads(text) == graph_to_dict(graph)


def test_graph_to_json_is_deterministic() -> None:
    graph = Graph(nodes=(Node(id="n1", type="File", properties=Properties.of(b=2, a=1)),))

    first = graph_to_json(graph)
    second = graph_to_json(graph)

    assert first == second


def test_graph_to_json_sorts_keys() -> None:
    graph = Graph(nodes=(Node(id="n1", type="File", properties=Properties.of(zeta=1, alpha=2)),))

    text = graph_to_json(graph, indent=2)

    alpha_index = text.index('"alpha"')
    zeta_index = text.index('"zeta"')
    assert alpha_index < zeta_index


def test_list_properties_serialize_as_json_arrays() -> None:
    node = Node(id="n1", type="File", properties=Properties.of(tags=["a", "b"]))
    graph = Graph(nodes=(node,))

    result = json.loads(graph_to_json(graph))

    assert result["nodes"][0]["properties"]["tags"] == ["a", "b"]
