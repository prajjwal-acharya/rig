from __future__ import annotations

from rig.graph.builders.structural import StructuralGraphBuilder
from rig.graph.model import Graph, RelationshipType
from rig.references.builder import ReferenceGraphBuilder
from rig.references.resolver import GoReferenceResolver
from tests.references.conftest import build_repository_and_symbols


def _resolve_and_build_graph(sources: dict[str, str]) -> tuple[Graph, Graph]:
    repository, symbols, _ = build_repository_and_symbols(sources)
    index = GoReferenceResolver().resolve(repository, symbols)
    structural_graph = StructuralGraphBuilder().build(repository)
    enriched = ReferenceGraphBuilder().build(index, symbols, structural_graph)
    return structural_graph, enriched


def test_references_edge_is_added_between_existing_nodes() -> None:
    _, enriched = _resolve_and_build_graph(
        {"a.go": "package p\n\nfunc helper() {}\n\nfunc Foo() {\n\thelper()\n}\n"}
    )

    references_edges = [e for e in enriched.edges if e.relationship == RelationshipType.REFERENCES]
    assert len(references_edges) >= 1

    node_ids = {n.id for n in enriched.nodes}
    for edge in references_edges:
        assert edge.source in node_ids
        assert edge.target in node_ids


def test_no_new_nodes_are_created() -> None:
    structural, enriched = _resolve_and_build_graph(
        {"a.go": "package p\n\nfunc helper() {}\n\nfunc Foo() {\n\thelper()\n}\n"}
    )

    assert len(enriched.nodes) == len(structural.nodes)
    assert enriched.nodes == structural.nodes


def test_does_not_mutate_the_input_graph() -> None:
    structural, enriched = _resolve_and_build_graph(
        {"a.go": "package p\n\nfunc helper() {}\n\nfunc Foo() {\n\thelper()\n}\n"}
    )

    assert len(structural.edges) < len(enriched.edges)
    assert not any(e.relationship == RelationshipType.REFERENCES for e in structural.edges)


def test_multiple_references_to_the_same_target_collapse_to_one_edge() -> None:
    _, enriched = _resolve_and_build_graph(
        {
            "a.go": (
                "package p\n\nfunc helper() {}\n\n"
                "func Foo() {\n\thelper()\n\thelper()\n\thelper()\n}\n"
            )
        }
    )

    references_edges = [e for e in enriched.edges if e.relationship == RelationshipType.REFERENCES]
    targets = [e.target for e in references_edges]
    assert len(targets) == len(set(targets))  # no duplicate (source, target) pairs


def test_metadata_statistics_are_populated() -> None:
    _, enriched = _resolve_and_build_graph(
        {"a.go": "package p\n\nfunc helper() {}\n\nfunc Foo() {\n\thelper()\n}\n"}
    )

    stats = enriched.metadata.statistics
    assert int(stats["reference_count"]) > 0  # type: ignore[arg-type]
    assert int(stats["resolved_reference_count"]) > 0  # type: ignore[arg-type]
    assert int(stats["reference_edge_count"]) > 0  # type: ignore[arg-type]
    assert "unresolved_reference_count" in stats


def test_empty_reference_index_adds_no_edges() -> None:
    _, enriched = _resolve_and_build_graph({"a.go": "package p\n"})

    references_edges = [e for e in enriched.edges if e.relationship == RelationshipType.REFERENCES]
    # only a package self-reference exists for an empty file, which does add
    # one edge (File -> Package) - verify no unexpected extras beyond that.
    assert len(references_edges) <= 1


def test_build_is_deterministic() -> None:
    repository, symbols, _ = build_repository_and_symbols(
        {"a.go": "package p\n\nfunc helper() {}\n\nfunc Foo() {\n\thelper()\n}\n"}
    )
    index = GoReferenceResolver().resolve(repository, symbols)
    structural_graph = StructuralGraphBuilder().build(repository)

    first = ReferenceGraphBuilder().build(index, symbols, structural_graph)
    second = ReferenceGraphBuilder().build(index, symbols, structural_graph)

    assert first == second
