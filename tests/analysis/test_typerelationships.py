from __future__ import annotations

from pathlib import Path

from rig.analysis import (
    AnalysisContext,
    AnalysisManager,
    AnalysisRegistry,
    AnalysisResult,
    Capability,
)
from rig.analysis.typerelationships import (
    TYPE_RELATIONSHIP_ANALYSIS_ID,
    TypeRelationship,
    TypeRelationshipAnalysis,
    TypeRelationshipGraph,
    TypeRelationshipKind,
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
from rig.types.builder import GoTypeBuilder


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


def _type_declaration_id(context: AnalysisContext, name: str) -> str:
    matches = [
        declaration.id
        for file in context.repository.files
        for declaration in file.declarations
        if declaration.name == name and declaration.kind.value == "type"
    ]
    assert len(matches) == 1, f"expected exactly one type named {name!r}, found {matches}"
    return matches[0]


def _run(context: AnalysisContext, parsed: tuple[ParsedFile, ...]) -> AnalysisResult:
    manager = AnalysisManager(AnalysisRegistry([TypeRelationshipAnalysis(parsed)]))
    return manager.execute_one(TYPE_RELATIONSHIP_ANALYSIS_ID, context)


# --- TypeRelationshipGraph model --------------------------------------------


def test_relationship_graph_outgoing_incoming_and_by_kind() -> None:
    graph = TypeRelationshipGraph(
        edges=(
            TypeRelationship(source_id="a", target_id="b", kind=TypeRelationshipKind.EMBEDS),
            TypeRelationship(
                source_id="a", target_id="c", kind=TypeRelationshipKind.DECLARES_FIELD_OF_TYPE
            ),
            TypeRelationship(source_id="b", target_id="c", kind=TypeRelationshipKind.ALIASES),
        )
    )

    assert graph.outgoing("a") == graph.relationships()[:2]
    assert graph.incoming("c") == (graph.relationships()[1], graph.relationships()[2])
    assert graph.by_kind(TypeRelationshipKind.EMBEDS) == (graph.relationships()[0],)
    assert graph.outgoing("missing") == ()
    assert len(graph) == 3


def test_empty_relationship_graph() -> None:
    graph = TypeRelationshipGraph()

    assert len(graph) == 0
    assert graph.relationships() == ()
    assert graph.outgoing("anything") == ()


# --- Registration and capabilities -------------------------------------------


def test_registers_normally() -> None:
    registry = AnalysisRegistry([TypeRelationshipAnalysis([])])

    assert registry.lookup(TYPE_RELATIONSHIP_ANALYSIS_ID) is not None


def test_required_capabilities_exclude_reference_index() -> None:
    analysis = TypeRelationshipAnalysis([])

    assert analysis.required_capabilities == frozenset(
        {Capability.IR, Capability.SYMBOL_TABLE, Capability.GRAPH}
    )


def test_manager_rejects_execution_when_a_capability_is_missing() -> None:
    from rig.ir.repository import RepositoryIR

    manager = AnalysisManager(AnalysisRegistry([TypeRelationshipAnalysis([])]))
    context = AnalysisContext(repository=RepositoryIR(id="repo:1", root=Path("/repo")))

    result = manager.execute_one(TYPE_RELATIONSHIP_ANALYSIS_ID, context)

    assert result.success is False
    assert len(result.diagnostics) == 2  # missing symbols, graph (not reference index)


# --- Relationship detection (real Go pipeline) ------------------------------


def test_embedding(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "a.go",
        "package p\n\ntype Logger struct{}\n\ntype Server struct {\n\tLogger\n}\n",
    )
    context, parsed = _build_context(tmp_path, ["a.go"])

    result = _run(context, parsed)

    rg: TypeRelationshipGraph = result.artifacts["type_relationships"]
    server_id = _type_declaration_id(context, "Server")
    logger_id = _type_declaration_id(context, "Logger")
    assert rg.relationships() == (
        TypeRelationship(
            source_id=server_id, target_id=logger_id, kind=TypeRelationshipKind.EMBEDS
        ),
    )


def test_pointer_embedding(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "a.go",
        "package p\n\ntype Cache struct{}\n\ntype Server struct {\n\t*Cache\n}\n",
    )
    context, parsed = _build_context(tmp_path, ["a.go"])

    result = _run(context, parsed)

    rg: TypeRelationshipGraph = result.artifacts["type_relationships"]
    server_id = _type_declaration_id(context, "Server")
    cache_id = _type_declaration_id(context, "Cache")
    assert rg.outgoing(server_id) == (
        TypeRelationship(source_id=server_id, target_id=cache_id, kind=TypeRelationshipKind.EMBEDS),
    )


def test_alias_to_repository_type(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "a.go",
        "package p\n\ntype Database struct{}\n\ntype MyAlias = Database\n",
    )
    context, parsed = _build_context(tmp_path, ["a.go"])

    result = _run(context, parsed)

    rg: TypeRelationshipGraph = result.artifacts["type_relationships"]
    alias_id = _type_declaration_id(context, "MyAlias")
    database_id = _type_declaration_id(context, "Database")
    assert rg.outgoing(alias_id) == (
        TypeRelationship(
            source_id=alias_id, target_id=database_id, kind=TypeRelationshipKind.ALIASES
        ),
    )


def test_builtin_aliases_are_ignored(tmp_path: Path) -> None:
    _write(tmp_path, "a.go", "package p\n\ntype MyString = string\n")
    context, parsed = _build_context(tmp_path, ["a.go"])

    result = _run(context, parsed)

    assert result.metadata["aliases"] == 0
    assert result.metadata["total_relationships"] == 0
    assert result.diagnostics == ()


def test_field_type_relationship(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "a.go",
        "package p\n\ntype Database struct{}\n\ntype Config struct {\n\tDB Database\n}\n",
    )
    context, parsed = _build_context(tmp_path, ["a.go"])

    result = _run(context, parsed)

    rg: TypeRelationshipGraph = result.artifacts["type_relationships"]
    config_id = _type_declaration_id(context, "Config")
    database_id = _type_declaration_id(context, "Database")
    assert rg.outgoing(config_id) == (
        TypeRelationship(
            source_id=config_id,
            target_id=database_id,
            kind=TypeRelationshipKind.DECLARES_FIELD_OF_TYPE,
        ),
    )


def test_method_parameter_relationship(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "a.go",
        (
            "package p\n\ntype Server struct{}\ntype Request struct{}\n\n"
            "func (s Server) Handle(req Request) {}\n"
        ),
    )
    context, parsed = _build_context(tmp_path, ["a.go"])

    result = _run(context, parsed)

    rg: TypeRelationshipGraph = result.artifacts["type_relationships"]
    server_id = _type_declaration_id(context, "Server")
    request_id = _type_declaration_id(context, "Request")
    assert rg.outgoing(server_id) == (
        TypeRelationship(
            source_id=server_id,
            target_id=request_id,
            kind=TypeRelationshipKind.DECLARES_METHOD_PARAMETER,
        ),
    )


def test_method_return_relationship(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "a.go",
        (
            "package p\n\ntype Server struct{}\ntype Database struct{}\n\n"
            "func (s *Server) DB() Database { return Database{} }\n"
        ),
    )
    context, parsed = _build_context(tmp_path, ["a.go"])

    result = _run(context, parsed)

    rg: TypeRelationshipGraph = result.artifacts["type_relationships"]
    server_id = _type_declaration_id(context, "Server")
    database_id = _type_declaration_id(context, "Database")
    assert rg.outgoing(server_id) == (
        TypeRelationship(
            source_id=server_id,
            target_id=database_id,
            kind=TypeRelationshipKind.DECLARES_METHOD_RETURNING,
        ),
    )


def test_multi_return_and_builtin_error_is_skipped(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "a.go",
        (
            "package p\n\ntype Server struct{}\ntype Database struct{}\n\n"
            "func (s Server) DB() (Database, error) { return Database{}, nil }\n"
        ),
    )
    context, parsed = _build_context(tmp_path, ["a.go"])

    result = _run(context, parsed)

    assert result.metadata["return_relationships"] == 1
    rg: TypeRelationshipGraph = result.artifacts["type_relationships"]
    server_id = _type_declaration_id(context, "Server")
    database_id = _type_declaration_id(context, "Database")
    assert rg.outgoing(server_id) == (
        TypeRelationship(
            source_id=server_id,
            target_id=database_id,
            kind=TypeRelationshipKind.DECLARES_METHOD_RETURNING,
        ),
    )


def test_unknown_repository_type_produces_diagnostic_and_no_edge(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "a.go",
        "package p\n\ntype Server struct{}\n\nfunc (s Server) Get() Missing { return Missing{} }\n",
    )
    context, parsed = _build_context(tmp_path, ["a.go"])

    result = _run(context, parsed)

    assert result.success is True
    assert result.metadata["total_relationships"] == 0
    assert len(result.diagnostics) == 1
    assert result.diagnostics[0].category == "unknown-repository-type"
    assert "Missing" in result.diagnostics[0].message


def test_ambiguous_type_lookup_produces_diagnostic(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "a.go",
        (
            "package p\n\n"
            "type Point struct { X int }\n\n"
            "type Point struct { Y int }\n\n"
            "type Holder struct {\n\tP Point\n}\n"
        ),
    )
    context, parsed = _build_context(tmp_path, ["a.go"])

    result = _run(context, parsed)

    assert result.metadata["field_relationships"] == 0
    categories = [d.category for d in result.diagnostics]
    assert "ambiguous-type-lookup" in categories


def test_generic_type_declaration_is_unsupported(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "a.go",
        "package p\n\ntype Box[T any] struct {\n\tValue T\n}\n",
    )
    context, parsed = _build_context(tmp_path, ["a.go"])

    result = _run(context, parsed)

    assert result.metadata["total_relationships"] == 0
    diagnostics = [d for d in result.diagnostics if d.category == "unsupported-declaration"]
    assert len(diagnostics) == 1
    assert "generic type" in diagnostics[0].message


def test_generic_receiver_is_unsupported(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "a.go",
        (
            "package p\n\ntype Box[T any] struct {\n\tValue T\n}\n\n"
            "func (b Box[T]) Get() T {\n\tvar v T\n\treturn v\n}\n"
        ),
    )
    context, parsed = _build_context(tmp_path, ["a.go"])

    result = _run(context, parsed)

    diagnostics = [d for d in result.diagnostics if d.category == "unsupported-declaration"]
    # one for the generic type declaration itself, one for the generic receiver
    assert len(diagnostics) == 2


def test_cross_file_relationships(tmp_path: Path) -> None:
    _write(tmp_path, "pkg/a.go", "package pkg\n\ntype Database struct{}\n")
    _write(
        tmp_path,
        "pkg/b.go",
        "package pkg\n\ntype Config struct {\n\tDB Database\n}\n",
    )
    context, parsed = _build_context(tmp_path, ["pkg/a.go", "pkg/b.go"])

    result = _run(context, parsed)

    rg: TypeRelationshipGraph = result.artifacts["type_relationships"]
    config_id = _type_declaration_id(context, "Config")
    database_id = _type_declaration_id(context, "Database")
    assert len(rg.outgoing(config_id)) == 1
    assert rg.outgoing(config_id)[0].target_id == database_id


def test_qualified_import_type_is_skipped_silently(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "a.go",
        "package p\n\ntype Server struct {\n\tpkg2.Remote\n}\n",
    )
    context, parsed = _build_context(tmp_path, ["a.go"])

    result = _run(context, parsed)

    assert result.metadata["total_relationships"] == 0
    assert result.diagnostics == ()


# --- Graph enrichment --------------------------------------------------------


def test_enriched_graph_only_adds_relationship_edges(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "a.go",
        "package p\n\ntype Logger struct{}\n\ntype Server struct {\n\tLogger\n}\n",
    )
    context, parsed = _build_context(tmp_path, ["a.go"])
    assert context.graph is not None
    original_graph = context.graph

    result = _run(context, parsed)

    enriched = result.artifacts["graph"]
    assert enriched.nodes == original_graph.nodes
    new_edges = [e for e in enriched.edges if e not in original_graph.edges]
    assert len(new_edges) == 1
    assert new_edges[0].relationship == RelationshipType.EMBEDS


def test_input_graph_is_never_mutated(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "a.go",
        "package p\n\ntype Logger struct{}\n\ntype Server struct {\n\tLogger\n}\n",
    )
    context, parsed = _build_context(tmp_path, ["a.go"])
    assert context.graph is not None
    original_nodes = context.graph.nodes
    original_edges = context.graph.edges

    _run(context, parsed)

    assert context.graph.nodes == original_nodes
    assert context.graph.edges == original_edges


def test_reuses_existing_type_nodes_no_duplicates_created(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "a.go",
        "package p\n\ntype Logger struct{}\n\ntype Server struct {\n\tLogger\n}\n",
    )
    context, parsed = _build_context(tmp_path, ["a.go"])
    assert context.graph is not None
    original_node_ids = {n.id for n in context.graph.nodes}

    result = _run(context, parsed)

    enriched = result.artifacts["graph"]
    assert {n.id for n in enriched.nodes} == original_node_ids


# --- Determinism -------------------------------------------------------------


def test_deterministic_output_across_repeated_execution(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "a.go",
        (
            "package p\n\ntype A struct{}\ntype B struct{}\ntype C struct{}\n\n"
            "type Root struct {\n\tA\n\tX B\n\tY C\n}\n"
        ),
    )
    context, parsed = _build_context(tmp_path, ["a.go"])

    first = _run(context, parsed)
    second = _run(context, parsed)

    assert first.artifacts["graph"].edges == second.artifacts["graph"].edges
    assert (
        first.artifacts["type_relationships"].relationships()
        == second.artifacts["type_relationships"].relationships()
    )


# --- Metadata ----------------------------------------------------------------


def test_metadata_counts_each_kind(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "a.go",
        (
            "package p\n\n"
            "type Logger struct{}\ntype Request struct{}\ntype Response struct{}\n"
            "type Database struct{}\n\n"
            "type Server struct {\n\tLogger\n\tDB Database\n}\n\n"
            "type MyAlias = Database\n\n"
            "func (s Server) Handle(req Request) Response { return Response{} }\n"
        ),
    )
    context, parsed = _build_context(tmp_path, ["a.go"])

    result = _run(context, parsed)

    metadata = dict(result.metadata)
    assert metadata["embedded_relationships"] == 1
    assert metadata["aliases"] == 1
    assert metadata["field_relationships"] == 1
    assert metadata["parameter_relationships"] == 1
    assert metadata["return_relationships"] == 1
    assert metadata["total_relationships"] == 5


# --- AnalysisManager integration ---------------------------------------------


def test_type_relationship_analysis_via_manager_end_to_end(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "a.go",
        "package p\n\ntype Logger struct{}\n\ntype Server struct {\n\tLogger\n}\n",
    )
    context, parsed = _build_context(tmp_path, ["a.go"])

    manager = AnalysisManager(AnalysisRegistry([TypeRelationshipAnalysis(parsed)]))
    results = manager.execute_all(context)

    assert len(results) == 1
    result = results[0]
    assert result.success is True
    assert result.analysis_id == TYPE_RELATIONSHIP_ANALYSIS_ID
    assert result.repository_id == context.repository.id
    assert result.started_at is not None
    assert result.duration_seconds >= 0.0
    assert isinstance(result.artifacts["type_relationships"], TypeRelationshipGraph)


def test_no_relationships_produces_empty_artifact(tmp_path: Path) -> None:
    _write(tmp_path, "a.go", "package p\n\ntype Solo struct{}\n")
    context, parsed = _build_context(tmp_path, ["a.go"])

    result = _run(context, parsed)

    assert result.metadata["total_relationships"] == 0
    assert len(result.artifacts["type_relationships"]) == 0


def test_analysis_consumes_type_index_via_go_type_builder_consistency(tmp_path: Path) -> None:
    # Confirms declaration ids used by the relationship artifact line up
    # exactly with what GoTypeBuilder itself produces for the same repo.
    _write(
        tmp_path,
        "a.go",
        "package p\n\ntype Logger struct{}\n\ntype Server struct {\n\tLogger\n}\n",
    )
    context, parsed = _build_context(tmp_path, ["a.go"])
    assert context.symbols is not None
    type_index = GoTypeBuilder().build(context.repository, context.symbols)

    result = _run(context, parsed)
    rg: TypeRelationshipGraph = result.artifacts["type_relationships"]

    server_type = type_index.by_name("Server")[0]
    logger_type = type_index.by_name("Logger")[0]
    assert rg.outgoing(server_type.declaration_id)[0].target_id == logger_type.declaration_id
