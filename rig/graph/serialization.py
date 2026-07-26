from __future__ import annotations

import json
from typing import Any

from rig.graph.model import Edge, Graph, GraphMetadata, Node
from rig.graph.properties import Properties


def properties_to_dict(properties: Properties) -> dict[str, Any]:
    return dict(properties.items())


def node_to_dict(node: Node) -> dict[str, Any]:
    return {
        "id": node.id,
        "type": node.type,
        "properties": properties_to_dict(node.properties),
    }


def edge_to_dict(edge: Edge) -> dict[str, Any]:
    return {
        "id": edge.id,
        "source": edge.source,
        "target": edge.target,
        "relationship": edge.relationship.value,
        "properties": properties_to_dict(edge.properties),
    }


def metadata_to_dict(metadata: GraphMetadata) -> dict[str, Any]:
    return {
        "repository_id": metadata.repository_id,
        "language_ids": list(metadata.language_ids),
        "generator": metadata.generator,
        "generator_version": metadata.generator_version,
        "created_at": metadata.created_at.isoformat() if metadata.created_at is not None else None,
        "statistics": properties_to_dict(metadata.statistics),
    }


def graph_to_dict(graph: Graph) -> dict[str, Any]:
    return {
        "nodes": [node_to_dict(node) for node in graph.nodes],
        "edges": [edge_to_dict(edge) for edge in graph.edges],
        "metadata": metadata_to_dict(graph.metadata),
    }


def graph_to_json(graph: Graph, *, indent: int | None = None) -> str:
    return json.dumps(graph_to_dict(graph), indent=indent, sort_keys=True)
