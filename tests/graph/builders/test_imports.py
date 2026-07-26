from __future__ import annotations

from dataclasses import replace

from rig.graph.builders.imports import ImportGraphBuilder
from rig.graph.builders.structural import StructuralGraphBuilder
from rig.graph.model import Graph, RelationshipType
from rig.ir.model import ImportDeclaration
from rig.ir.repository import RepositoryIR
from tests.graph.builders.conftest import (
    build_repository,
    make_file,
    make_function,
    make_import,
)


def _base_graph(repository: RepositoryIR) -> Graph:
    return StructuralGraphBuilder().build(repository)


def _with_alias(import_declaration: ImportDeclaration, alias: str) -> ImportDeclaration:
    return replace(import_declaration, alias=alias)


def test_single_import_creates_node_and_edge() -> None:
    imp = make_import("fmt", "a.go")
    file = make_file("a.go", package_name="pkg1", declarations=[imp])
    repository = build_repository(file)
    graph = _base_graph(repository)

    enriched = ImportGraphBuilder().build(repository, graph)

    import_nodes = [n for n in enriched.nodes if n.type == "Import"]
    assert len(import_nodes) == 1
    assert import_nodes[0].properties["import_path"] == "fmt"

    imports_edges = [e for e in enriched.edges if e.relationship == RelationshipType.IMPORTS]
    file_node = next(n for n in enriched.nodes if n.type == "File")
    assert len(imports_edges) == 1
    assert imports_edges[0].source == file_node.id
    assert imports_edges[0].target == import_nodes[0].id


def test_grouped_imports_each_become_their_own_node() -> None:
    imp1 = make_import("fmt", "a.go")
    imp2 = make_import("context", "a.go")
    file = make_file("a.go", package_name="pkg1", declarations=[imp1, imp2])
    repository = build_repository(file)
    graph = _base_graph(repository)

    enriched = ImportGraphBuilder().build(repository, graph)

    import_nodes = {n.properties["import_path"] for n in enriched.nodes if n.type == "Import"}
    assert import_nodes == {"fmt", "context"}


def test_aliased_import_stores_alias_property() -> None:
    imp = make_import("fmt", "a.go")
    imp = _with_alias(imp, "f")
    file = make_file("a.go", package_name="pkg1", declarations=[imp])
    repository = build_repository(file)
    graph = _base_graph(repository)

    enriched = ImportGraphBuilder().build(repository, graph)

    import_node = next(n for n in enriched.nodes if n.type == "Import")
    assert import_node.properties["alias"] == "f"
    assert import_node.properties["is_blank"] is False
    assert import_node.properties["is_dot"] is False


def test_blank_import_is_flagged() -> None:
    imp = _with_alias(make_import("net/http/pprof", "a.go"), "_")
    file = make_file("a.go", package_name="pkg1", declarations=[imp])
    repository = build_repository(file)
    graph = _base_graph(repository)

    enriched = ImportGraphBuilder().build(repository, graph)

    import_node = next(n for n in enriched.nodes if n.type == "Import")
    assert import_node.properties["is_blank"] is True
    assert import_node.properties["alias"] == "_"


def test_dot_import_is_flagged() -> None:
    imp = _with_alias(make_import("strings", "a.go"), ".")
    file = make_file("a.go", package_name="pkg1", declarations=[imp])
    repository = build_repository(file)
    graph = _base_graph(repository)

    enriched = ImportGraphBuilder().build(repository, graph)

    import_node = next(n for n in enriched.nodes if n.type == "Import")
    assert import_node.properties["is_dot"] is True
    assert import_node.properties["alias"] == "."


def test_plain_import_has_no_alias_property() -> None:
    imp = make_import("fmt", "a.go")
    file = make_file("a.go", package_name="pkg1", declarations=[imp])
    repository = build_repository(file)
    graph = _base_graph(repository)

    enriched = ImportGraphBuilder().build(repository, graph)

    import_node = next(n for n in enriched.nodes if n.type == "Import")
    assert "alias" not in import_node.properties


def test_same_import_path_and_alias_across_files_reuses_one_node() -> None:
    imp1 = make_import("fmt", "pkg1/a.go")
    imp2 = make_import("fmt", "pkg1/b.go")
    file1 = make_file("pkg1/a.go", package_name="pkg1", declarations=[imp1])
    file2 = make_file("pkg1/b.go", package_name="pkg1", declarations=[imp2])
    repository = build_repository(file1, file2)
    graph = _base_graph(repository)

    enriched = ImportGraphBuilder().build(repository, graph)

    import_nodes = [n for n in enriched.nodes if n.type == "Import"]
    assert len(import_nodes) == 1

    imports_edges = [e for e in enriched.edges if e.relationship == RelationshipType.IMPORTS]
    assert len(imports_edges) == 2
    targets = {e.target for e in imports_edges}
    assert targets == {import_nodes[0].id}


def test_different_alias_for_same_path_creates_distinct_nodes() -> None:
    plain = make_import("fmt", "a.go")
    aliased = _with_alias(make_import("fmt", "a.go", occurrence=1), "f")
    file = make_file("a.go", package_name="pkg1", declarations=[plain, aliased])
    repository = build_repository(file)
    graph = _base_graph(repository)

    enriched = ImportGraphBuilder().build(repository, graph)

    import_nodes = [n for n in enriched.nodes if n.type == "Import"]
    assert len(import_nodes) == 2


def test_does_not_mutate_the_input_graph() -> None:
    imp = make_import("fmt", "a.go")
    file = make_file("a.go", package_name="pkg1", declarations=[imp])
    repository = build_repository(file)
    graph = _base_graph(repository)
    original_node_count = len(graph.nodes)
    original_edge_count = len(graph.edges)

    ImportGraphBuilder().build(repository, graph)

    assert len(graph.nodes) == original_node_count
    assert len(graph.edges) == original_edge_count
    assert not any(n.type == "Import" for n in graph.nodes)


def test_empty_imports_leaves_graph_unchanged_except_metadata() -> None:
    file = make_file("a.go", package_name="pkg1", declarations=[make_function("Foo", "a.go")])
    repository = build_repository(file)
    graph = _base_graph(repository)

    enriched = ImportGraphBuilder().build(repository, graph)

    assert len(enriched.nodes) == len(graph.nodes)
    assert len(enriched.edges) == len(graph.edges)
    assert enriched.metadata.statistics["import_count"] == 0
    assert enriched.metadata.statistics["import_node_count"] == 0
    assert enriched.metadata.statistics["import_edge_count"] == 0


def test_metadata_counts() -> None:
    imp1 = make_import("fmt", "pkg1/a.go")
    imp2 = make_import("fmt", "pkg1/b.go")
    imp3 = make_import("context", "pkg1/a.go", occurrence=1)
    file1 = make_file("pkg1/a.go", package_name="pkg1", declarations=[imp1, imp3])
    file2 = make_file("pkg1/b.go", package_name="pkg1", declarations=[imp2])
    repository = build_repository(file1, file2)
    graph = _base_graph(repository)

    enriched = ImportGraphBuilder().build(repository, graph)

    assert enriched.metadata.statistics["import_count"] == 3
    assert enriched.metadata.statistics["import_node_count"] == 2  # fmt (shared), context
    assert enriched.metadata.statistics["import_edge_count"] == 3


def test_build_is_deterministic_across_repeated_calls() -> None:
    imp1 = make_import("fmt", "pkg1/a.go")
    imp2 = make_import("context", "pkg1/a.go", occurrence=1)
    file = make_file("pkg1/a.go", package_name="pkg1", declarations=[imp1, imp2])
    repository = build_repository(file)
    graph = _base_graph(repository)

    first = ImportGraphBuilder().build(repository, graph)
    second = ImportGraphBuilder().build(repository, graph)

    assert first == second
