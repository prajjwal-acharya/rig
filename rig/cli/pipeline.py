from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from rig.analysis import (
    CALL_GRAPH_ANALYSIS_ID,
    DEPENDENCY_ANALYSIS_ID,
    TYPE_RELATIONSHIP_ANALYSIS_ID,
    AnalysisContext,
    AnalysisManager,
    AnalysisRegistry,
    AnalysisResult,
    CallGraphAnalysis,
    DependencyAnalysis,
    TypeRelationshipAnalysis,
)
from rig.frontends.go import GoIRBuilder
from rig.graph.builders.imports import ImportGraphBuilder
from rig.graph.builders.structural import StructuralGraphBuilder
from rig.graph.model import Graph
from rig.ir.builder import IRBuilderRegistry
from rig.ir.repository import RepositoryIR, build_repository_ir
from rig.languages.pipeline import RepositoryLanguageReport, detect_repository_languages
from rig.parsers.factory import build_default_parser_registry
from rig.parsers.manager import ParserManager
from rig.parsers.pipeline import ParsedFile, parse_repository_files
from rig.references.builder import ReferenceGraphBuilder
from rig.references.index import ReferenceIndex
from rig.references.resolver import IRReferenceResolver
from rig.scanner.errors import RepositoryPathNotADirectoryError, RepositoryPathNotFoundError
from rig.scanner.ignore import IgnoreEngine
from rig.scanner.locator import locate_repository
from rig.scanner.metadata import MetadataCollector
from rig.scanner.models import FilteredWalkResult, RepositorySnapshot, RepositoryStatistics
from rig.scanner.repository import scan_repository
from rig.scanner.walker import walk_repository
from rig.symbols.builder import GoSymbolTableBuilder
from rig.symbols.table import SymbolTable
from rig.types.builder import GoTypeBuilder
from rig.types.index import TypeIndex


class PipelineError(Exception):
    """Raised when a pipeline stage cannot proceed for a user-facing reason
    (invalid repository path). The CLI translates this into an `error: ...`
    message and a non-zero exit code, rather than a raw traceback."""


def build_snapshot(path: str) -> RepositorySnapshot:
    try:
        return scan_repository(path)
    except (RepositoryPathNotFoundError, RepositoryPathNotADirectoryError) as exc:
        raise PipelineError(str(exc)) from exc


def build_snapshot_with_filtered(path: str) -> tuple[RepositorySnapshot, FilteredWalkResult]:
    # Only `scan` needs the intermediate FilteredWalkResult (to report what
    # was ignored) - every other command uses the simpler `build_snapshot`.
    try:
        location = locate_repository(path)
    except (RepositoryPathNotFoundError, RepositoryPathNotADirectoryError) as exc:
        raise PipelineError(str(exc)) from exc

    walk_result = walk_repository(location.root)
    filtered = IgnoreEngine(location.root).filter(walk_result)
    enriched = MetadataCollector(location.root).collect(filtered)

    statistics = RepositoryStatistics(
        files=len(enriched.included_files),
        directories=len(enriched.included_directories),
        is_git_repository=location.git.is_git_repository,
    )
    snapshot = RepositorySnapshot(
        root=location.root,
        git=location.git,
        files=enriched.included_files,
        directories=enriched.included_directories,
        statistics=statistics,
    )
    return snapshot, enriched


def build_language_report(snapshot: RepositorySnapshot) -> RepositoryLanguageReport:
    return detect_repository_languages(snapshot.files)


def build_parsed_files(
    root: Path, language_report: RepositoryLanguageReport
) -> tuple[ParsedFile, ...]:
    parser_manager = ParserManager(build_default_parser_registry())
    return parse_repository_files(root, language_report.files, parser_manager)


def build_repository(root: Path, parsed_files: Sequence[ParsedFile]) -> RepositoryIR:
    ir_registry = IRBuilderRegistry([GoIRBuilder()])
    return build_repository_ir(root, parsed_files, ir_registry)


def build_symbol_table(repository: RepositoryIR) -> SymbolTable:
    return GoSymbolTableBuilder().build(repository)


def build_reference_index(repository: RepositoryIR, symbols: SymbolTable) -> ReferenceIndex:
    return IRReferenceResolver().resolve(repository, symbols)


def build_type_index(repository: RepositoryIR, symbols: SymbolTable) -> TypeIndex:
    return GoTypeBuilder().build(repository, symbols)


def build_structural_graph(repository: RepositoryIR) -> Graph:
    graph = StructuralGraphBuilder().build(repository)
    return ImportGraphBuilder().build(repository, graph)


def enrich_graph_with_references(
    references: ReferenceIndex, symbols: SymbolTable, graph: Graph
) -> Graph:
    return ReferenceGraphBuilder().build(references, symbols, graph)


@dataclass(frozen=True)
class SemanticAnalysisResult:
    graph: Graph
    call_graph: AnalysisResult
    type_relationships: AnalysisResult
    dependencies: AnalysisResult


def run_semantic_analyses(
    repository: RepositoryIR,
    symbols: SymbolTable,
    references: ReferenceIndex,
    graph: Graph,
) -> SemanticAnalysisResult:
    # Each analysis enriches the graph independently, so the resulting
    # graph from one is threaded into the context for the next - this is
    # how three separate graph-enriching analyses compose into a single
    # final graph via the existing AnalysisManager, with no framework
    # changes: just sequential, natural use of execute_one.
    registry = AnalysisRegistry(
        [
            CallGraphAnalysis(),
            TypeRelationshipAnalysis(),
            DependencyAnalysis(),
        ]
    )
    manager = AnalysisManager(registry)

    context = AnalysisContext(
        repository=repository, symbols=symbols, references=references, graph=graph
    )
    call_graph_result = manager.execute_one(CALL_GRAPH_ANALYSIS_ID, context)
    graph = call_graph_result.artifacts.get("graph", graph)

    context = AnalysisContext(
        repository=repository, symbols=symbols, references=references, graph=graph
    )
    type_relationship_result = manager.execute_one(TYPE_RELATIONSHIP_ANALYSIS_ID, context)
    graph = type_relationship_result.artifacts.get("graph", graph)

    context = AnalysisContext(
        repository=repository, symbols=symbols, references=references, graph=graph
    )
    dependency_result = manager.execute_one(DEPENDENCY_ANALYSIS_ID, context)
    graph = dependency_result.artifacts.get("graph", graph)

    return SemanticAnalysisResult(
        graph=graph,
        call_graph=call_graph_result,
        type_relationships=type_relationship_result,
        dependencies=dependency_result,
    )
