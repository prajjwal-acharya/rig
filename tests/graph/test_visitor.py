from __future__ import annotations

from rig.graph.model import Edge, Graph, Node, RelationshipType
from rig.graph.visitor import GraphVisitor, iter_edges, iter_nodes


def _graph() -> Graph:
    nodes = (Node(id="n1", type="File"), Node(id="n2", type="Function"))
    edge = Edge(id="e1", source="n1", target="n2", relationship=RelationshipType.CONTAINS)
    return Graph(nodes=nodes, edges=(edge,))


def test_iter_nodes_yields_every_node() -> None:
    assert [n.id for n in iter_nodes(_graph())] == ["n1", "n2"]


def test_iter_edges_yields_every_edge() -> None:
    assert [e.id for e in iter_edges(_graph())] == ["e1"]


def test_base_visitor_visit_graph_is_a_safe_no_op() -> None:
    GraphVisitor().visit_graph(_graph())  # must not raise


class RecordingVisitor(GraphVisitor):
    def __init__(self) -> None:
        self.visited_nodes: list[str] = []
        self.contains: list[str] = []
        self.declares: list[str] = []
        self.imports: list[str] = []
        self.calls: list[str] = []
        self.references: list[str] = []
        self.implements: list[str] = []
        self.extends: list[str] = []
        self.owns: list[str] = []

    def visit_node(self, node: Node) -> None:
        self.visited_nodes.append(node.id)

    def visit_contains(self, edge: Edge) -> None:
        self.contains.append(edge.id)

    def visit_declares(self, edge: Edge) -> None:
        self.declares.append(edge.id)

    def visit_imports(self, edge: Edge) -> None:
        self.imports.append(edge.id)

    def visit_calls(self, edge: Edge) -> None:
        self.calls.append(edge.id)

    def visit_references(self, edge: Edge) -> None:
        self.references.append(edge.id)

    def visit_implements(self, edge: Edge) -> None:
        self.implements.append(edge.id)

    def visit_extends(self, edge: Edge) -> None:
        self.extends.append(edge.id)

    def visit_owns(self, edge: Edge) -> None:
        self.owns.append(edge.id)


def test_visitor_visits_every_node() -> None:
    visitor = RecordingVisitor()

    visitor.visit_graph(_graph())

    assert visitor.visited_nodes == ["n1", "n2"]


def test_visitor_dispatches_contains_edges_to_the_override() -> None:
    # Regression test: dispatch must resolve visit_contains via the actual
    # instance (respecting subclass overrides), not a prebuilt reference to
    # the base class's no-op implementation.
    visitor = RecordingVisitor()

    visitor.visit_graph(_graph())

    assert visitor.contains == ["e1"]
    assert visitor.declares == []


def _edge_for(relationship: RelationshipType) -> Edge:
    return Edge(id="e1", source="n1", target="n2", relationship=relationship)


def test_visitor_dispatches_every_relationship_type() -> None:
    cases = [
        (RelationshipType.CONTAINS, "contains"),
        (RelationshipType.DECLARES, "declares"),
        (RelationshipType.IMPORTS, "imports"),
        (RelationshipType.CALLS, "calls"),
        (RelationshipType.REFERENCES, "references"),
        (RelationshipType.IMPLEMENTS, "implements"),
        (RelationshipType.EXTENDS, "extends"),
        (RelationshipType.OWNS, "owns"),
    ]

    for relationship, attr_name in cases:
        visitor = RecordingVisitor()
        visitor.visit_edge(_edge_for(relationship))
        assert getattr(visitor, attr_name) == ["e1"], f"failed for {relationship}"


def test_visit_edge_on_base_class_does_not_raise_for_any_relationship() -> None:
    visitor = GraphVisitor()
    for relationship in RelationshipType:
        visitor.visit_edge(_edge_for(relationship))  # must not raise
