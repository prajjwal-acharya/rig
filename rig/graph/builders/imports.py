from __future__ import annotations

import hashlib
from dataclasses import replace
from typing import Any

from rig.graph.builder import GraphAccumulator
from rig.graph.identifiers import edge_id
from rig.graph.model import Edge, Graph, Node, RelationshipType
from rig.graph.properties import Properties
from rig.ir.model import File, ImportDeclaration
from rig.ir.repository import RepositoryIR

# Deliberately self-contained (not imported from rig.graph.identifiers), the
# same way rig.graph.identifiers itself doesn't import from rig.ir.identifiers
# - Import node identity isn't tied to any single IR object, so it needs its
# own scheme rather than reusing an existing one.
_SEPARATOR = "\x1f"


def _digest(*parts: str) -> str:
    return hashlib.sha256(_SEPARATOR.join(parts).encode("utf-8")).hexdigest()[:16]


def _import_node_id(repository_id: str, import_path: str, alias: str | None) -> str:
    return f"import:{_digest(repository_id, import_path, alias or '')}"


def _import_properties(declaration: ImportDeclaration, language_id: str) -> Properties:
    values: dict[str, Any] = {
        "import_path": declaration.import_path,
        "is_blank": declaration.alias == "_",
        "is_dot": declaration.alias == ".",
        "language": language_id,
    }
    if declaration.alias is not None:
        values["alias"] = declaration.alias
    return Properties.from_mapping(values)


class ImportGraphBuilder:
    """Enriches an existing Graph with IMPORTS edges, derived purely from
    RepositoryIR's ImportDeclaration objects. Does not implement the
    GraphBuilder interface (which builds a graph from nothing) - this
    consumes an existing Graph and returns a new one, never mutating the
    input, so it deliberately has its own `build(repository, graph)` shape.
    """

    def build(self, repository: RepositoryIR, graph: Graph) -> Graph:
        import_specs: list[tuple[File, ImportDeclaration]] = [
            (file, declaration)
            for file in repository.files
            for declaration in file.declarations
            if isinstance(declaration, ImportDeclaration)
        ]

        new_nodes: list[Node] = []
        new_edges: list[Edge] = []
        node_id_by_key: dict[tuple[str, str | None], str] = {}
        seen_edge_keys: set[tuple[str, str]] = set()

        for file, declaration in import_specs:
            key = (declaration.import_path, declaration.alias)
            node_id = node_id_by_key.get(key)
            if node_id is None:
                node_id = _import_node_id(repository.id, declaration.import_path, declaration.alias)
                node_id_by_key[key] = node_id
                new_nodes.append(
                    Node(
                        id=node_id,
                        type="Import",
                        properties=_import_properties(declaration, file.language_id),
                    )
                )

            edge_key = (file.id, node_id)
            if edge_key not in seen_edge_keys:
                seen_edge_keys.add(edge_key)
                new_edges.append(
                    Edge(
                        id=edge_id(file.id, node_id, RelationshipType.IMPORTS.value),
                        source=file.id,
                        target=node_id,
                        relationship=RelationshipType.IMPORTS,
                    )
                )

        statistics = graph.metadata.statistics
        statistics = statistics.with_property("import_count", len(import_specs))
        statistics = statistics.with_property("import_node_count", len(new_nodes))
        statistics = statistics.with_property("import_edge_count", len(new_edges))
        metadata = replace(graph.metadata, statistics=statistics)

        accumulator = GraphAccumulator(metadata=metadata)
        for node in graph.nodes:
            accumulator.add_node(node)
        for edge in graph.edges:
            accumulator.add_edge(edge)
        for node in new_nodes:
            accumulator.add_node(node)
        for edge in new_edges:
            accumulator.add_edge(edge)

        return accumulator.build()
