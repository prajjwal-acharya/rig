from __future__ import annotations

from collections.abc import Iterator

from rig.graph.model import Edge, Graph, Node, RelationshipType

_EDGE_METHOD_NAMES: dict[RelationshipType, str] = {
    RelationshipType.CONTAINS: "visit_contains",
    RelationshipType.DECLARES: "visit_declares",
    RelationshipType.IMPORTS: "visit_imports",
    RelationshipType.CALLS: "visit_calls",
    RelationshipType.REFERENCES: "visit_references",
    RelationshipType.IMPLEMENTS: "visit_implements",
    RelationshipType.EXTENDS: "visit_extends",
    RelationshipType.OWNS: "visit_owns",
}


def iter_nodes(graph: Graph) -> Iterator[Node]:
    yield from graph.nodes


def iter_edges(graph: Graph) -> Iterator[Edge]:
    yield from graph.edges


class GraphVisitor:
    """Base visitor over graph objects. Subclass and override only the
    `visit_*` methods you care about; the rest provide default traversal."""

    def visit_graph(self, graph: Graph) -> None:
        for node in graph.nodes:
            self.visit_node(node)
        for edge in graph.edges:
            self.visit_edge(edge)

    def visit_node(self, node: Node) -> None:
        pass

    def visit_edge(self, edge: Edge) -> None:
        # Looked up by name on `self` (not a prebuilt function-object dict)
        # so subclass overrides are actually respected via normal dispatch.
        method_name = _EDGE_METHOD_NAMES.get(edge.relationship)
        if method_name is not None:
            getattr(self, method_name)(edge)

    def visit_contains(self, edge: Edge) -> None:
        pass

    def visit_declares(self, edge: Edge) -> None:
        pass

    def visit_imports(self, edge: Edge) -> None:
        pass

    def visit_calls(self, edge: Edge) -> None:
        pass

    def visit_references(self, edge: Edge) -> None:
        pass

    def visit_implements(self, edge: Edge) -> None:
        pass

    def visit_extends(self, edge: Edge) -> None:
        pass

    def visit_owns(self, edge: Edge) -> None:
        pass
