from __future__ import annotations

from pathlib import Path

from rig.analysis import (
    AnalysisContext,
    AnalysisManager,
    AnalysisRegistry,
    AnalysisResult,
    Capability,
)
from rig.analysis.dependency import (
    DEPENDENCY_ANALYSIS_ID,
    DependencyAnalysis,
    DependencyEdge,
    DependencyGraph,
    DependencyKind,
)
from rig.graph.builders.structural import StructuralGraphBuilder
from rig.graph.model import RelationshipType
from rig.ir.builder import IRBuilderRegistry
from rig.ir.builders.go import GoIRBuilder
from rig.ir.repository import build_repository_ir
from rig.languages import DEFAULT_REGISTRY
from rig.languages.pipeline import LanguageAnnotatedFile
from rig.parsers.manager import ParserManager
from rig.parsers.pipeline import ParsedFile, parse_repository_files
from rig.parsers.treesitter.factory import build_default_registry as build_parser_registry
from rig.scanner.models import DiscoveredFile
from rig.symbols.builder import GoSymbolTableBuilder
from rig.symbols.table import SymbolTable


def _write(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def _build_context(
    root: Path, relative_paths: list[str]
) -> tuple[AnalysisContext, tuple[ParsedFile, ...]]:
    go_language = DEFAULT_REGISTRY.lookup_extension(".go")
    assert go_language is not None
    annotated = [
        LanguageAnnotatedFile(file=DiscoveredFile(relative_path=Path(p)), language=go_language)
        for p in relative_paths
    ]
    parser_manager = ParserManager(build_parser_registry())
    parsed: tuple[ParsedFile, ...] = parse_repository_files(root, annotated, parser_manager)

    ir_registry = IRBuilderRegistry([GoIRBuilder()])
    repository = build_repository_ir(root, parsed, ir_registry)

    symbols: SymbolTable = GoSymbolTableBuilder().build(repository)
    graph = StructuralGraphBuilder().build(repository)

    context = AnalysisContext(repository=repository, symbols=symbols, graph=graph)
    return context, parsed


def _package_id(context: AnalysisContext, name: str) -> str:
    matches = [p.id for p in context.repository.packages if p.name == name]
    assert len(matches) == 1, f"expected exactly one package named {name!r}, found {matches}"
    return matches[0]


def _run(context: AnalysisContext, parsed: tuple[ParsedFile, ...]) -> AnalysisResult:
    manager = AnalysisManager(AnalysisRegistry([DependencyAnalysis(parsed)]))
    return manager.execute_one(DEPENDENCY_ANALYSIS_ID, context)


# --- DependencyGraph model ---------------------------------------------------


def test_dependency_graph_outgoing_incoming_by_kind_and_transitive() -> None:
    graph = DependencyGraph(
        edges=(
            DependencyEdge(source_id="a", target_id="b", kind=DependencyKind.IMPORT),
            DependencyEdge(source_id="a", target_id="c", kind=DependencyKind.TYPE),
            DependencyEdge(source_id="b", target_id="c", kind=DependencyKind.CALL),
        )
    )

    assert graph.outgoing("a") == graph.dependencies()[:2]
    assert graph.incoming("c") == (graph.dependencies()[1], graph.dependencies()[2])
    assert graph.by_kind(DependencyKind.IMPORT) == (graph.dependencies()[0],)
    assert graph.outgoing("missing") == ()
    assert graph.transitive("a") == frozenset({"b", "c"})
    assert graph.transitive("c") == frozenset()
    assert len(graph) == 3


def test_transitive_terminates_on_a_cycle() -> None:
    graph = DependencyGraph(
        edges=(
            DependencyEdge(source_id="a", target_id="b", kind=DependencyKind.IMPORT),
            DependencyEdge(source_id="b", target_id="a", kind=DependencyKind.IMPORT),
        )
    )

    assert graph.transitive("a") == frozenset({"a", "b"})


def test_empty_dependency_graph() -> None:
    graph = DependencyGraph()

    assert len(graph) == 0
    assert graph.dependencies() == ()
    assert graph.transitive("anything") == frozenset()


# --- Registration and capabilities -------------------------------------------


def test_registers_normally() -> None:
    registry = AnalysisRegistry([DependencyAnalysis([])])

    assert registry.lookup(DEPENDENCY_ANALYSIS_ID) is not None


def test_required_capabilities_exclude_reference_index() -> None:
    analysis = DependencyAnalysis([])

    assert analysis.required_capabilities == frozenset(
        {Capability.IR, Capability.SYMBOL_TABLE, Capability.GRAPH}
    )


def test_manager_rejects_execution_when_a_capability_is_missing() -> None:
    from rig.ir.repository import RepositoryIR

    manager = AnalysisManager(AnalysisRegistry([DependencyAnalysis([])]))
    context = AnalysisContext(repository=RepositoryIR(id="repo:1", root=Path("/repo")))

    result = manager.execute_one(DEPENDENCY_ANALYSIS_ID, context)

    assert result.success is False
    assert len(result.diagnostics) == 2  # missing symbols, graph (not reference index)


# --- Dependency detection (real Go pipeline) --------------------------------


def test_import_dependency(tmp_path: Path) -> None:
    _write(tmp_path, "api/a.go", 'package api\n\nimport "myrepo/service"\n\nfunc F() {}\n')
    _write(tmp_path, "service/b.go", "package service\n\nfunc G() {}\n")
    context, parsed = _build_context(tmp_path, ["api/a.go", "service/b.go"])

    result = _run(context, parsed)

    dg: DependencyGraph = result.artifacts["dependencies"]
    api_id = _package_id(context, "api")
    service_id = _package_id(context, "service")
    assert dg.dependencies() == (
        DependencyEdge(source_id=api_id, target_id=service_id, kind=DependencyKind.IMPORT),
    )


def test_type_dependency_via_exported_struct_field(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "api/a.go",
        (
            'package api\n\nimport "myrepo/service"\n\n'
            "type Handler struct {\n\tSvc service.Service\n}\n"
        ),
    )
    _write(tmp_path, "service/b.go", "package service\n\ntype Service struct{}\n")
    context, parsed = _build_context(tmp_path, ["api/a.go", "service/b.go"])

    result = _run(context, parsed)

    dg: DependencyGraph = result.artifacts["dependencies"]
    api_id = _package_id(context, "api")
    service_id = _package_id(context, "service")
    assert (
        DependencyEdge(source_id=api_id, target_id=service_id, kind=DependencyKind.TYPE)
        in dg.dependencies()
    )


def test_type_dependency_via_alias(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "api/a.go",
        'package api\n\nimport "myrepo/model"\n\ntype Config = model.Settings\n',
    )
    _write(tmp_path, "model/b.go", "package model\n\ntype Settings struct{}\n")
    context, parsed = _build_context(tmp_path, ["api/a.go", "model/b.go"])

    result = _run(context, parsed)

    dg: DependencyGraph = result.artifacts["dependencies"]
    api_id = _package_id(context, "api")
    model_id = _package_id(context, "model")
    assert (
        DependencyEdge(source_id=api_id, target_id=model_id, kind=DependencyKind.TYPE)
        in dg.dependencies()
    )


def test_type_dependency_is_scoped_to_exported_types(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "api/a.go",
        (
            'package api\n\nimport "myrepo/service"\n\n'
            "type handler struct {\n\tSvc service.Service\n}\n"
        ),
    )
    _write(tmp_path, "service/b.go", "package service\n\ntype Service struct{}\n")
    context, parsed = _build_context(tmp_path, ["api/a.go", "service/b.go"])

    result = _run(context, parsed)

    assert result.metadata["type_dependencies"] == 0


def test_call_dependency(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "api/a.go",
        'package api\n\nimport "myrepo/service"\n\nfunc F() {\n\tservice.Start()\n}\n',
    )
    _write(tmp_path, "service/b.go", "package service\n\nfunc Start() {}\n")
    context, parsed = _build_context(tmp_path, ["api/a.go", "service/b.go"])

    result = _run(context, parsed)

    dg: DependencyGraph = result.artifacts["dependencies"]
    api_id = _package_id(context, "api")
    service_id = _package_id(context, "service")
    assert (
        DependencyEdge(source_id=api_id, target_id=service_id, kind=DependencyKind.CALL)
        in dg.dependencies()
    )


def test_method_call_on_a_value_is_not_a_dependency(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "api/a.go",
        (
            "package api\n\ntype Widget struct{}\n\nfunc (w Widget) Method() {}\n\n"
            "func F() {\n\tw := Widget{}\n\tw.Method()\n}\n"
        ),
    )
    context, parsed = _build_context(tmp_path, ["api/a.go"])

    result = _run(context, parsed)

    assert result.metadata["call_dependencies"] == 0
    assert result.diagnostics == ()


def test_multiple_reasons_between_the_same_package_pair_are_preserved(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "api/a.go",
        (
            'package api\n\nimport "myrepo/service"\n\n'
            "type Handler struct {\n\tSvc service.Service\n}\n\n"
            "func F() {\n\tservice.Start()\n}\n"
        ),
    )
    _write(
        tmp_path,
        "service/b.go",
        "package service\n\ntype Service struct{}\n\nfunc Start() {}\n",
    )
    context, parsed = _build_context(tmp_path, ["api/a.go", "service/b.go"])

    result = _run(context, parsed)

    dg: DependencyGraph = result.artifacts["dependencies"]
    api_id = _package_id(context, "api")
    service_id = _package_id(context, "service")
    kinds = {e.kind for e in dg.outgoing(api_id) if e.target_id == service_id}
    assert kinds == {DependencyKind.IMPORT, DependencyKind.TYPE, DependencyKind.CALL}
    assert result.metadata["dependency_count"] == 3


def test_duplicate_call_sites_deduplicate_into_one_edge(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "api/a.go",
        (
            'package api\n\nimport "myrepo/service"\n\n'
            "func F() {\n\tservice.Start()\n\tservice.Start()\n}\n"
        ),
    )
    _write(tmp_path, "service/b.go", "package service\n\nfunc Start() {}\n")
    context, parsed = _build_context(tmp_path, ["api/a.go", "service/b.go"])

    result = _run(context, parsed)

    assert result.metadata["call_dependencies"] == 1


def test_external_import_is_not_tracked(tmp_path: Path) -> None:
    _write(tmp_path, "api/a.go", 'package api\n\nimport "fmt"\n\nfunc F() {\n\tfmt.Println()\n}\n')
    context, parsed = _build_context(tmp_path, ["api/a.go"])

    result = _run(context, parsed)

    assert result.metadata["dependency_count"] == 0
    assert result.diagnostics == ()


def test_unknown_package_diagnostic(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "api/a.go",
        "package api\n\ntype Handler struct {\n\tX missingpkg.Thing\n}\n",
    )
    context, parsed = _build_context(tmp_path, ["api/a.go"])

    result = _run(context, parsed)

    categories = [d.category for d in result.diagnostics]
    assert "unknown-package" in categories
    assert result.metadata["type_dependencies"] == 0


def test_unsupported_dependency_source_for_generic_type(tmp_path: Path) -> None:
    _write(tmp_path, "api/a.go", "package api\n\ntype Box[T any] struct {\n\tValue T\n}\n")
    context, parsed = _build_context(tmp_path, ["api/a.go"])

    result = _run(context, parsed)

    diagnostics = [d for d in result.diagnostics if d.category == "unsupported-dependency-source"]
    assert len(diagnostics) == 1
    assert "generic type" in diagnostics[0].message


def test_unsupported_dependency_source_for_unusual_call_shape(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "api/a.go",
        "package api\n\nfunc F() {\n\tfuncs := []func(){}\n\tfuncs[0]()\n}\n",
    )
    context, parsed = _build_context(tmp_path, ["api/a.go"])

    result = _run(context, parsed)

    diagnostics = [d for d in result.diagnostics if d.category == "unsupported-dependency-source"]
    assert len(diagnostics) == 1


def test_cyclic_self_dependency_diagnostic_and_no_edge() -> None:
    from rig.analysis.dependency import _Collector, _process_import
    from rig.ir.identifiers import package_id
    from rig.ir.model import ImportDeclaration, SourceLocation
    from rig.ir.repository import Package

    location = SourceLocation(
        relative_path=Path("a.go"), start_line=0, start_column=0, end_line=0, end_column=1
    )
    pkg = Package(id=package_id("repo:1", "self"), name="self", file_ids=("f1",))
    declaration = ImportDeclaration(
        id="declaration:1", name="self", location=location, import_path="myrepo/self"
    )
    collector = _Collector()

    _process_import(declaration, pkg, {"self": pkg}, collector)

    assert len(collector.diagnostics) == 1
    assert collector.diagnostics[0].category == "cyclic-self-dependency"
    assert collector.build().dependencies() == ()


# --- Graph enrichment --------------------------------------------------------


def test_enriched_graph_only_adds_depends_on_edges_with_kind_metadata(tmp_path: Path) -> None:
    _write(tmp_path, "api/a.go", 'package api\n\nimport "myrepo/service"\n\nfunc F() {}\n')
    _write(tmp_path, "service/b.go", "package service\n\nfunc G() {}\n")
    context, parsed = _build_context(tmp_path, ["api/a.go", "service/b.go"])
    assert context.graph is not None
    original_graph = context.graph

    result = _run(context, parsed)

    enriched = result.artifacts["graph"]
    assert enriched.nodes == original_graph.nodes
    new_edges = [e for e in enriched.edges if e not in original_graph.edges]
    assert len(new_edges) == 1
    assert new_edges[0].relationship == RelationshipType.DEPENDS_ON
    assert new_edges[0].properties.get("kind") == "IMPORT"


def test_input_graph_is_never_mutated(tmp_path: Path) -> None:
    _write(tmp_path, "api/a.go", 'package api\n\nimport "myrepo/service"\n\nfunc F() {}\n')
    _write(tmp_path, "service/b.go", "package service\n\nfunc G() {}\n")
    context, parsed = _build_context(tmp_path, ["api/a.go", "service/b.go"])
    assert context.graph is not None
    original_nodes = context.graph.nodes
    original_edges = context.graph.edges

    _run(context, parsed)

    assert context.graph.nodes == original_nodes
    assert context.graph.edges == original_edges


def test_reuses_existing_package_nodes_no_duplicates_created(tmp_path: Path) -> None:
    _write(tmp_path, "api/a.go", 'package api\n\nimport "myrepo/service"\n\nfunc F() {}\n')
    _write(tmp_path, "service/b.go", "package service\n\nfunc G() {}\n")
    context, parsed = _build_context(tmp_path, ["api/a.go", "service/b.go"])
    assert context.graph is not None
    original_node_ids = {n.id for n in context.graph.nodes}

    result = _run(context, parsed)

    enriched = result.artifacts["graph"]
    assert {n.id for n in enriched.nodes} == original_node_ids


# --- Determinism -------------------------------------------------------------


def test_deterministic_output_across_repeated_execution(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "api/a.go",
        (
            'package api\n\nimport "myrepo/service"\n\n'
            "type Handler struct {\n\tSvc service.Service\n}\n\n"
            "func F() {\n\tservice.Start()\n}\n"
        ),
    )
    _write(
        tmp_path,
        "service/b.go",
        "package service\n\ntype Service struct{}\n\nfunc Start() {}\n",
    )
    context, parsed = _build_context(tmp_path, ["api/a.go", "service/b.go"])

    first = _run(context, parsed)
    second = _run(context, parsed)

    assert first.artifacts["graph"].edges == second.artifacts["graph"].edges
    assert (
        first.artifacts["dependencies"].dependencies()
        == second.artifacts["dependencies"].dependencies()
    )


# --- Metadata ----------------------------------------------------------------


def test_metadata_counts_each_kind(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "api/a.go",
        (
            'package api\n\nimport "myrepo/service"\n\n'
            "type Handler struct {\n\tSvc service.Service\n}\n\n"
            "func F() {\n\tservice.Start()\n}\n"
        ),
    )
    _write(
        tmp_path,
        "service/b.go",
        "package service\n\ntype Service struct{}\n\nfunc Start() {}\n",
    )
    context, parsed = _build_context(tmp_path, ["api/a.go", "service/b.go"])

    result = _run(context, parsed)

    metadata = dict(result.metadata)
    assert metadata["package_count"] == 2
    assert metadata["import_dependencies"] == 1
    assert metadata["type_dependencies"] == 1
    assert metadata["call_dependencies"] == 1
    assert metadata["dependency_count"] == 3


# --- AnalysisManager integration ---------------------------------------------


def test_dependency_analysis_via_manager_end_to_end(tmp_path: Path) -> None:
    _write(tmp_path, "api/a.go", 'package api\n\nimport "myrepo/service"\n\nfunc F() {}\n')
    _write(tmp_path, "service/b.go", "package service\n\nfunc G() {}\n")
    context, parsed = _build_context(tmp_path, ["api/a.go", "service/b.go"])

    manager = AnalysisManager(AnalysisRegistry([DependencyAnalysis(parsed)]))
    results = manager.execute_all(context)

    assert len(results) == 1
    result = results[0]
    assert result.success is True
    assert result.analysis_id == DEPENDENCY_ANALYSIS_ID
    assert result.repository_id == context.repository.id
    assert result.started_at is not None
    assert result.duration_seconds >= 0.0
    assert isinstance(result.artifacts["dependencies"], DependencyGraph)


def test_transitive_across_a_three_package_chain(tmp_path: Path) -> None:
    _write(tmp_path, "api/a.go", 'package api\n\nimport "myrepo/service"\n\nfunc F() {}\n')
    _write(tmp_path, "service/b.go", 'package service\n\nimport "myrepo/storage"\n\nfunc G() {}\n')
    _write(tmp_path, "storage/c.go", "package storage\n\nfunc H() {}\n")
    context, parsed = _build_context(tmp_path, ["api/a.go", "service/b.go", "storage/c.go"])

    result = _run(context, parsed)

    dg: DependencyGraph = result.artifacts["dependencies"]
    api_id = _package_id(context, "api")
    storage_id = _package_id(context, "storage")
    assert storage_id in dg.transitive(api_id)


def test_no_dependencies_produces_empty_artifact(tmp_path: Path) -> None:
    _write(tmp_path, "a.go", "package solo\n\nfunc F() {}\n")
    context, parsed = _build_context(tmp_path, ["a.go"])

    result = _run(context, parsed)

    assert result.metadata["dependency_count"] == 0
    assert len(result.artifacts["dependencies"]) == 0
