from __future__ import annotations

from pathlib import Path

import pytest

from rig.analysis import (
    AnalysisContext,
    AnalysisManager,
    AnalysisRegistry,
    AnalysisResult,
    Capability,
)
from rig.analysis.callgraph import CALL_GRAPH_ANALYSIS_ID, CallEdge, CallGraph, CallGraphAnalysis
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
from rig.references.index import ReferenceIndex
from rig.references.resolver import GoReferenceResolver
from rig.scanner.models import DiscoveredFile
from rig.symbols.builder import GoSymbolTableBuilder
from rig.symbols.table import SymbolTable


def _write(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def _build_context(root: Path, relative_paths: list[str]) -> AnalysisContext:
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
    references: ReferenceIndex = GoReferenceResolver(parsed).resolve(repository, symbols)
    graph = StructuralGraphBuilder().build(repository)

    return AnalysisContext(
        repository=repository, symbols=symbols, references=references, graph=graph
    )


def _function_id(context: AnalysisContext, name: str) -> str:
    assert context.symbols is not None
    matches = [
        declaration.id
        for file in context.repository.files
        for declaration in file.declarations
        if declaration.name == name and declaration.kind.value == "function"
    ]
    assert len(matches) == 1, f"expected exactly one function named {name!r}, found {matches}"
    return matches[0]


def _run(context: AnalysisContext) -> AnalysisResult:
    manager = AnalysisManager(AnalysisRegistry([CallGraphAnalysis()]))
    return manager.execute_one(CALL_GRAPH_ANALYSIS_ID, context)


# --- CallGraph / CallEdge model -------------------------------------------


def test_call_graph_callees_and_callers_lookup() -> None:
    call_graph = CallGraph(
        edges=(
            CallEdge(caller_id="a", callee_id="b"),
            CallEdge(caller_id="a", callee_id="c"),
            CallEdge(caller_id="b", callee_id="c"),
        )
    )

    assert call_graph.callees_of("a") == ("b", "c")
    assert call_graph.callers_of("c") == ("a", "b")
    assert call_graph.callees_of("missing") == ()
    assert call_graph.callers_of("missing") == ()
    assert len(call_graph) == 3


def test_empty_call_graph() -> None:
    call_graph = CallGraph()

    assert len(call_graph) == 0
    assert call_graph.callees_of("anything") == ()


# --- Registration ----------------------------------------------------------


def test_call_graph_analysis_registers_normally() -> None:
    registry = AnalysisRegistry([CallGraphAnalysis()])

    assert registry.lookup(CALL_GRAPH_ANALYSIS_ID) is not None
    assert CALL_GRAPH_ANALYSIS_ID in registry


def test_call_graph_analysis_declares_required_capabilities() -> None:
    analysis = CallGraphAnalysis()

    assert analysis.required_capabilities == frozenset(
        {
            Capability.IR,
            Capability.SYMBOL_TABLE,
            Capability.REFERENCE_INDEX,
            Capability.GRAPH,
        }
    )


def test_manager_rejects_execution_when_a_capability_is_missing() -> None:
    from rig.ir.repository import RepositoryIR

    manager = AnalysisManager(AnalysisRegistry([CallGraphAnalysis()]))
    context = AnalysisContext(repository=RepositoryIR(id="repo:1", root=Path("/repo")))

    result = manager.execute_one(CALL_GRAPH_ANALYSIS_ID, context)

    assert result.success is False
    assert len(result.diagnostics) == 3  # missing symbols, references, graph


# --- Call detection scenarios (real Go pipeline) ---------------------------


def test_single_function_call(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "a.go",
        "package p\n\nfunc helper() {}\n\nfunc Foo() {\n\thelper()\n}\n",
    )
    context = _build_context(tmp_path, ["a.go"])

    result = _run(context)

    call_graph: CallGraph = result.artifacts["call_graph"]
    foo_id = _function_id(context, "Foo")
    helper_id = _function_id(context, "helper")
    assert call_graph.callees_of(foo_id) == (helper_id,)
    assert result.metadata["total_calls"] == 1
    assert result.metadata["resolved_calls"] == 1
    assert result.metadata["generated_edges"] == 1


def test_recursive_call(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "a.go",
        "package p\n\nfunc recurse(n int) int {\n\tif n <= 0 {\n\t\treturn 0\n\t}\n\treturn recurse(n - 1)\n}\n",
    )
    context = _build_context(tmp_path, ["a.go"])

    result = _run(context)

    call_graph: CallGraph = result.artifacts["call_graph"]
    recurse_id = _function_id(context, "recurse")
    assert call_graph.callees_of(recurse_id) == (recurse_id,)
    assert call_graph.callers_of(recurse_id) == (recurse_id,)


def test_mutual_recursion(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "a.go",
        (
            "package p\n\n"
            "func even(n int) bool {\n\tif n == 0 {\n\t\treturn true\n\t}\n\treturn odd(n - 1)\n}\n\n"
            "func odd(n int) bool {\n\tif n == 0 {\n\t\treturn false\n\t}\n\treturn even(n - 1)\n}\n"
        ),
    )
    context = _build_context(tmp_path, ["a.go"])

    result = _run(context)

    call_graph: CallGraph = result.artifacts["call_graph"]
    even_id = _function_id(context, "even")
    odd_id = _function_id(context, "odd")
    assert call_graph.callees_of(even_id) == (odd_id,)
    assert call_graph.callees_of(odd_id) == (even_id,)


def test_cross_file_calls(tmp_path: Path) -> None:
    _write(tmp_path, "pkg/a.go", "package pkg\n\nfunc helper() {}\n")
    _write(
        tmp_path,
        "pkg/b.go",
        "package pkg\n\nfunc CrossFile() {\n\thelper()\n}\n",
    )
    context = _build_context(tmp_path, ["pkg/a.go", "pkg/b.go"])

    result = _run(context)

    call_graph: CallGraph = result.artifacts["call_graph"]
    cross_file_id = _function_id(context, "CrossFile")
    helper_id = _function_id(context, "helper")
    assert call_graph.callees_of(cross_file_id) == (helper_id,)


def test_duplicate_call_sites_are_deduplicated_into_one_edge_with_a_count(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "a.go",
        "package p\n\nfunc helper() {}\n\nfunc Foo() {\n\thelper()\n\thelper()\n\thelper()\n}\n",
    )
    context = _build_context(tmp_path, ["a.go"])

    result = _run(context)

    call_graph: CallGraph = result.artifacts["call_graph"]
    foo_id = _function_id(context, "Foo")
    helper_id = _function_id(context, "helper")
    edges = [e for e in call_graph.edges if e.caller_id == foo_id and e.callee_id == helper_id]
    assert len(edges) == 1
    assert edges[0].call_count == 3
    assert len(edges[0].call_site_lines) == 3
    assert result.metadata["generated_edges"] == 1


def test_unresolved_calls_produce_diagnostics_but_no_edge(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "a.go",
        "package p\n\nfunc Foo() {\n\tdoesNotExist()\n}\n",
    )
    context = _build_context(tmp_path, ["a.go"])

    result = _run(context)

    assert result.success is True
    assert result.metadata["unresolved_calls"] == 1
    assert result.metadata["generated_edges"] == 0
    diagnostics = result.diagnostics
    assert len(diagnostics) == 1
    assert diagnostics[0].category == "unresolved-call-target"
    assert "doesNotExist" in diagnostics[0].message


def test_ambiguous_call_targets_produce_diagnostics(tmp_path: Path) -> None:
    _write(tmp_path, "pkg1/a.go", "package pkg1\n\nfunc Run() {}\n\nfunc Caller() {\n\tRun()\n}\n")
    _write(tmp_path, "pkg2/b.go", "package pkg2\n\nfunc Run() {}\n")
    context = _build_context(tmp_path, ["pkg1/a.go", "pkg2/b.go"])

    result = _run(context)

    assert result.metadata["ambiguous_calls"] == 1
    categories = {d.category for d in result.diagnostics}
    assert "ambiguous-call-target" in categories


# --- Graph enrichment --------------------------------------------------------


def test_enriched_graph_only_adds_calls_edges(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "a.go",
        "package p\n\nfunc helper() {}\n\nfunc Foo() {\n\thelper()\n}\n",
    )
    context = _build_context(tmp_path, ["a.go"])
    assert context.graph is not None
    original_graph = context.graph

    result = _run(context)

    enriched = result.artifacts["graph"]
    assert enriched.nodes == original_graph.nodes  # no nodes added or removed
    new_edges = [e for e in enriched.edges if e not in original_graph.edges]
    assert all(e.relationship == RelationshipType.CALLS for e in new_edges)
    assert len(new_edges) == 1


def test_input_graph_is_never_mutated(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "a.go",
        "package p\n\nfunc helper() {}\n\nfunc Foo() {\n\thelper()\n}\n",
    )
    context = _build_context(tmp_path, ["a.go"])
    assert context.graph is not None
    original_nodes = context.graph.nodes
    original_edges = context.graph.edges

    _run(context)

    assert context.graph.nodes == original_nodes
    assert context.graph.edges == original_edges


def test_reuses_existing_function_nodes_no_duplicates_created(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "a.go",
        "package p\n\nfunc helper() {}\n\nfunc Foo() {\n\thelper()\n}\n",
    )
    context = _build_context(tmp_path, ["a.go"])
    assert context.graph is not None
    original_node_ids = {n.id for n in context.graph.nodes}

    result = _run(context)

    enriched = result.artifacts["graph"]
    enriched_node_ids = {n.id for n in enriched.nodes}
    assert enriched_node_ids == original_node_ids


# --- Determinism -------------------------------------------------------------


def test_deterministic_output_across_repeated_execution(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "a.go",
        (
            "package p\n\n"
            "func a() {}\nfunc b() {}\nfunc c() {}\n\n"
            "func Root() {\n\ta()\n\tb()\n\tc()\n\ta()\n}\n"
        ),
    )
    context = _build_context(tmp_path, ["a.go"])

    first = _run(context)
    second = _run(context)

    assert first.artifacts["graph"].nodes == second.artifacts["graph"].nodes
    assert first.artifacts["graph"].edges == second.artifacts["graph"].edges
    assert first.artifacts["call_graph"].edges == second.artifacts["call_graph"].edges


# --- Metadata ----------------------------------------------------------------


def test_metadata_counts_are_populated(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "a.go",
        "package p\n\nfunc helper() {}\n\nfunc Foo() {\n\thelper()\n\tdoesNotExist()\n}\n",
    )
    context = _build_context(tmp_path, ["a.go"])

    result = _run(context)

    metadata = dict(result.metadata)
    assert metadata["total_calls"] == 2
    assert metadata["resolved_calls"] == 1
    assert metadata["unresolved_calls"] == 1
    assert metadata["generated_edges"] == 1


# --- AnalysisManager integration ---------------------------------------------


def test_call_graph_analysis_via_manager_end_to_end(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "a.go",
        "package p\n\nfunc helper() {}\n\nfunc Foo() {\n\thelper()\n}\n",
    )
    context = _build_context(tmp_path, ["a.go"])

    manager = AnalysisManager(AnalysisRegistry([CallGraphAnalysis()]))
    results = manager.execute_all(context)

    assert len(results) == 1
    result = results[0]
    assert result.success is True
    assert result.analysis_id == CALL_GRAPH_ANALYSIS_ID
    assert result.repository_id == context.repository.id
    assert result.started_at is not None
    assert result.duration_seconds >= 0.0
    assert isinstance(result.artifacts["call_graph"], CallGraph)


def test_call_with_no_enclosing_function_produces_no_edge(tmp_path: Path) -> None:
    # A package-level var initializer calling a function isn't inside any
    # FunctionDeclaration, so there is no Function source node for an edge.
    _write(
        tmp_path,
        "a.go",
        "package p\n\nfunc helper() int {\n\treturn 1\n}\n\nvar x = helper()\n",
    )
    context = _build_context(tmp_path, ["a.go"])

    result = _run(context)

    assert result.metadata["generated_edges"] == 0


@pytest.mark.parametrize("relative_path", ["a.go"])
def test_no_calls_produces_empty_call_graph(tmp_path: Path, relative_path: str) -> None:
    _write(tmp_path, relative_path, "package p\n\nfunc Foo() {}\n")
    context = _build_context(tmp_path, [relative_path])

    result = _run(context)

    assert result.metadata["total_calls"] == 0
    assert len(result.artifacts["call_graph"]) == 0
