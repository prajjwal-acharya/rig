from __future__ import annotations

from datetime import datetime, timezone

from rig.graph.builder import DuplicateEdgeError, DuplicateNodeError
from rig.graph.builders.structural import STRUCTURAL_GRAPH_VERSION, StructuralGraphBuilder
from rig.graph.model import GraphIndex, RelationshipType
from rig.graph.registry import GraphBuilderRegistry
from rig.ir.repository import RepositoryIR
from tests.graph.builders.conftest import (
    REPO_ROOT,
    REPOSITORY_ID,
    build_repository,
    make_file,
    make_function,
    make_import,
    make_type,
    make_variable,
)

FIXED_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _builder() -> StructuralGraphBuilder:
    return StructuralGraphBuilder(now=lambda: FIXED_NOW)


def test_builder_id() -> None:
    assert _builder().builder_id == "structural"


def test_empty_repository_produces_only_a_repository_node() -> None:
    repository = build_repository()

    graph = _builder().build(repository)

    assert [n.type for n in graph.nodes] == ["Repository"]
    assert graph.nodes[0].id == repository.id
    assert graph.edges == ()


def test_repository_node_properties() -> None:
    repository = build_repository()

    graph = _builder().build(repository)

    repo_node = graph.nodes[0]
    assert repo_node.properties["name"] == REPO_ROOT.name
    assert repo_node.properties["root_path"] == str(REPO_ROOT)
    assert repo_node.properties["graph_version"] == STRUCTURAL_GRAPH_VERSION


def test_repository_node_language_summary() -> None:
    file = make_file("a.go", package_name="pkg1")
    repository = build_repository(file)

    graph = _builder().build(repository)

    repo_node = next(n for n in graph.nodes if n.type == "Repository")
    assert repo_node.properties["languages"] == ("go",)


def test_package_node_generated_with_properties() -> None:
    function = make_function("Foo", "a.go")
    file = make_file("a.go", package_name="pkg1", declarations=[function])
    repository = build_repository(file)

    graph = _builder().build(repository)

    package_nodes = [n for n in graph.nodes if n.type == "Package"]
    assert len(package_nodes) == 1
    package_node = package_nodes[0]
    assert package_node.id == repository.packages[0].id
    assert package_node.properties["name"] == "pkg1"
    assert package_node.properties["language"] == "go"
    assert package_node.properties["declaration_count"] == 1


def test_repository_contains_package_edge() -> None:
    file = make_file("a.go", package_name="pkg1")
    repository = build_repository(file)

    graph = _builder().build(repository)

    package_node = next(n for n in graph.nodes if n.type == "Package")
    contains_edges = [e for e in graph.edges if e.relationship == RelationshipType.CONTAINS]
    assert any(e.source == repository.id and e.target == package_node.id for e in contains_edges)


def test_file_node_generated_with_properties() -> None:
    function = make_function("Foo", "pkg1/a.go")
    file = make_file("pkg1/a.go", package_name="pkg1", declarations=[function])
    repository = build_repository(file)

    graph = _builder().build(repository)

    file_node = next(n for n in graph.nodes if n.type == "File")
    assert file_node.id == file.id
    assert file_node.properties["relative_path"] == "pkg1/a.go"
    assert file_node.properties["language"] == "go"
    assert file_node.properties["declaration_count"] == 1


def test_package_contains_file_edge() -> None:
    file = make_file("pkg1/a.go", package_name="pkg1")
    repository = build_repository(file)

    graph = _builder().build(repository)

    package_node = next(n for n in graph.nodes if n.type == "Package")
    file_node = next(n for n in graph.nodes if n.type == "File")
    contains_edges = [e for e in graph.edges if e.relationship == RelationshipType.CONTAINS]
    assert any(e.source == package_node.id and e.target == file_node.id for e in contains_edges)


def test_function_declaration_node() -> None:
    function = make_function("Foo", "a.go", is_exported=True)
    file = make_file("a.go", package_name="pkg1", declarations=[function])
    repository = build_repository(file)

    graph = _builder().build(repository)

    node = next(n for n in graph.nodes if n.type == "Function")
    assert node.id == function.id
    assert node.properties["name"] == "Foo"
    assert node.properties["parameter_count"] == 2
    assert node.properties["is_exported"] is True
    assert node.properties["location_file"] == "a.go"


def test_type_declaration_node() -> None:
    type_decl = make_type("Widget", "a.go", underlying_kind="struct")
    file = make_file("a.go", package_name="pkg1", declarations=[type_decl])
    repository = build_repository(file)

    graph = _builder().build(repository)

    node = next(n for n in graph.nodes if n.type == "Type")
    assert node.id == type_decl.id
    assert node.properties["underlying_kind"] == "struct"


def test_variable_declaration_node() -> None:
    variable = make_variable("GlobalX", "a.go", is_constant=False)
    file = make_file("a.go", package_name="pkg1", declarations=[variable])
    repository = build_repository(file)

    graph = _builder().build(repository)

    node = next(n for n in graph.nodes if n.type == "Variable")
    assert node.id == variable.id
    assert node.properties["name"] == "GlobalX"


def test_constant_declaration_node() -> None:
    constant = make_variable("MaxRetries", "a.go", is_constant=True)
    file = make_file("a.go", package_name="pkg1", declarations=[constant])
    repository = build_repository(file)

    graph = _builder().build(repository)

    node = next(n for n in graph.nodes if n.type == "Constant")
    assert node.id == constant.id
    assert not any(n.type == "Variable" for n in graph.nodes)


def test_import_declarations_produce_no_nodes() -> None:
    imp = make_import("fmt", "a.go")
    file = make_file("a.go", package_name="pkg1", declarations=[imp])
    repository = build_repository(file)

    graph = _builder().build(repository)

    assert not any(n.id == imp.id for n in graph.nodes)
    file_node = next(n for n in graph.nodes if n.type == "File")
    assert file_node.properties["declaration_count"] == 0


def test_file_declares_edge_for_each_declaration() -> None:
    function = make_function("Foo", "a.go")
    type_decl = make_type("Widget", "a.go")
    file = make_file("a.go", package_name="pkg1", declarations=[function, type_decl])
    repository = build_repository(file)

    graph = _builder().build(repository)

    file_node = next(n for n in graph.nodes if n.type == "File")
    declares_edges = [e for e in graph.edges if e.relationship == RelationshipType.DECLARES]
    targets = {e.target for e in declares_edges if e.source == file_node.id}
    assert targets == {function.id, type_decl.id}


def test_orphan_file_without_package_attaches_to_repository() -> None:
    file = make_file("orphan.go", package_name=None)
    repository = build_repository(file)

    graph = _builder().build(repository)

    assert repository.packages == ()
    file_node = next(n for n in graph.nodes if n.type == "File")
    contains_edges = [e for e in graph.edges if e.relationship == RelationshipType.CONTAINS]
    assert any(e.source == repository.id and e.target == file_node.id for e in contains_edges)


def test_duplicate_declaration_names_produce_distinct_nodes() -> None:
    foo1 = make_function("Foo", "a.go", occurrence=0)
    foo2 = make_function("Foo", "a.go", occurrence=1)
    file = make_file("a.go", package_name="pkg1", declarations=[foo1, foo2])
    repository = build_repository(file)

    graph = _builder().build(repository)

    function_nodes = [n for n in graph.nodes if n.type == "Function"]
    assert len(function_nodes) == 2
    assert function_nodes[0].id != function_nodes[1].id
    assert {n.id for n in function_nodes} == {foo1.id, foo2.id}


def test_multiple_packages_each_get_their_own_subtree() -> None:
    file1 = make_file(
        "pkg1/a.go", package_name="pkg1", declarations=[make_function("Foo", "pkg1/a.go")]
    )
    file2 = make_file(
        "pkg2/b.go", package_name="pkg2", declarations=[make_function("Bar", "pkg2/b.go")]
    )
    repository = build_repository(file1, file2)

    graph = _builder().build(repository)

    package_nodes = {n.properties["name"] for n in graph.nodes if n.type == "Package"}
    assert package_nodes == {"pkg1", "pkg2"}
    assert len(graph.nodes) == 1 + 2 + 2 + 2  # repo + 2 packages + 2 files + 2 functions


def test_no_duplicate_nodes_or_edges_raised() -> None:
    # A well-formed RepositoryIR (unique IR ids everywhere) must never hit
    # the accumulator's duplicate-detection paths.
    file1 = make_file(
        "pkg1/a.go", package_name="pkg1", declarations=[make_function("Foo", "pkg1/a.go")]
    )
    file2 = make_file(
        "pkg1/b.go", package_name="pkg1", declarations=[make_function("Bar", "pkg1/b.go")]
    )
    repository = build_repository(file1, file2)

    try:
        _builder().build(repository)
    except (DuplicateNodeError, DuplicateEdgeError) as exc:
        raise AssertionError(f"unexpected duplicate detection: {exc}") from None


def test_graph_metadata_population() -> None:
    file1 = make_file(
        "pkg1/a.go", package_name="pkg1", declarations=[make_function("Foo", "pkg1/a.go")]
    )
    file2 = make_file(
        "pkg2/b.go", package_name="pkg2", declarations=[make_function("Bar", "pkg2/b.go")]
    )
    repository = build_repository(file1, file2)

    graph = _builder().build(repository)

    metadata = graph.metadata
    assert metadata.repository_id == repository.id
    assert metadata.language_ids == ("go",)
    assert metadata.generator == "structural"
    assert metadata.generator_version == STRUCTURAL_GRAPH_VERSION
    assert metadata.created_at == FIXED_NOW
    assert metadata.statistics["package_count"] == 2
    assert metadata.statistics["file_count"] == 2
    assert metadata.statistics["declaration_count"] == 2


def test_metadata_declaration_count_excludes_imports() -> None:
    file = make_file(
        "a.go",
        package_name="pkg1",
        declarations=[make_import("fmt", "a.go"), make_function("Foo", "a.go")],
    )
    repository = build_repository(file)

    graph = _builder().build(repository)

    assert graph.metadata.statistics["declaration_count"] == 1


def test_build_is_deterministic_across_repeated_calls() -> None:
    file = make_file("a.go", package_name="pkg1", declarations=[make_function("Foo", "a.go")])
    repository = build_repository(file)
    builder = _builder()

    first = builder.build(repository)
    second = builder.build(repository)

    assert first == second


def test_build_ordering_does_not_depend_on_declaration_insertion_order() -> None:
    foo = make_function("Foo", "a.go")
    bar = make_function("Bar", "a.go", occurrence=0)
    file_forward = make_file("a.go", package_name="pkg1", declarations=[foo, bar])
    file_backward = make_file("a.go", package_name="pkg1", declarations=[bar, foo])

    graph_forward = _builder().build(build_repository(file_forward))
    graph_backward = _builder().build(build_repository(file_backward))

    assert graph_forward.nodes == graph_backward.nodes
    assert graph_forward.edges == graph_backward.edges


def test_graph_index_can_traverse_the_structural_graph() -> None:
    function = make_function("Foo", "pkg1/a.go")
    file = make_file("pkg1/a.go", package_name="pkg1", declarations=[function])
    repository = build_repository(file)

    graph = _builder().build(repository)
    index = GraphIndex(graph)

    package_node = next(n for n in graph.nodes if n.type == "Package")
    file_node = next(n for n in graph.nodes if n.type == "File")

    assert any(e.target == package_node.id for e in index.edges_from(repository.id))
    assert any(e.target == file_node.id for e in index.edges_from(package_node.id))
    assert any(e.target == function.id for e in index.edges_from(file_node.id))


def test_registers_cleanly_with_the_existing_graph_builder_registry() -> None:
    registry = GraphBuilderRegistry([StructuralGraphBuilder()])

    assert registry.lookup("structural") is not None
    assert "structural" in registry
    assert len(registry) == 1


def test_build_default_registry_factory() -> None:
    from rig.graph.builders.structural import build_default_registry

    registry = build_default_registry()

    assert registry.lookup("structural") is not None


def test_repository_with_no_files_but_explicit_construction() -> None:
    repository = RepositoryIR(id=REPOSITORY_ID, root=REPO_ROOT)

    graph = _builder().build(repository)

    assert len(graph.nodes) == 1
    assert graph.nodes[0].type == "Repository"
