from __future__ import annotations

from bisect import bisect_right
from collections.abc import Mapping
from dataclasses import dataclass, field, replace

from rig.analysis.capability import Capability
from rig.analysis.context import AnalysisContext
from rig.analysis.diagnostics import AnalysisDiagnostic, AnalysisDiagnosticSeverity
from rig.analysis.interface import Analysis
from rig.analysis.result import AnalysisResult
from rig.graph.builder import GraphAccumulator
from rig.graph.identifiers import edge_id
from rig.graph.model import Edge, Graph, RelationshipType
from rig.graph.properties import Properties
from rig.ir.model import FunctionDeclaration
from rig.ir.repository import RepositoryIR
from rig.references.index import ReferenceIndex
from rig.references.model import Reference, ReferenceKind, ResolvedReference, UnresolvedReference
from rig.symbols.model import FunctionSymbol
from rig.symbols.table import SymbolTable

CALL_GRAPH_ANALYSIS_ID = "call-graph"
CALL_GRAPH_ANALYSIS_VERSION = "1.0.0"

# Node ids the graph is enriched with are `FunctionDeclaration.id` values -
# the exact ids StructuralGraphBuilder already uses for `Function` nodes -
# so CALLS edges attach to existing nodes without ever creating new ones.


@dataclass(frozen=True, kw_only=True, slots=True)
class CallEdge:
    """One resolved caller -> callee relationship between two functions,
    already deduplicated across every call site between the same pair."""

    caller_id: str
    callee_id: str
    call_count: int = 1
    call_site_lines: tuple[int, ...] = ()


@dataclass(frozen=True, kw_only=True)
class CallGraph:
    """Purpose-built caller/callee view over a repository's direct function
    calls - a dedicated, typed artifact (mirroring how SymbolTable is a
    semantic index beyond the IR, and ReferenceIndex an efficient lookup
    beyond raw references) so later analyses that need caller/callee
    relationships (dead code, impact analysis, recursion/SCC detection) can
    query this directly instead of walking generic Knowledge Graph edges.
    """

    edges: tuple[CallEdge, ...] = ()
    _callees_by_caller: Mapping[str, tuple[str, ...]] = field(
        init=False, repr=False, default_factory=dict
    )
    _callers_by_callee: Mapping[str, tuple[str, ...]] = field(
        init=False, repr=False, default_factory=dict
    )

    def __post_init__(self) -> None:
        callees: dict[str, list[str]] = {}
        callers: dict[str, list[str]] = {}
        for call_edge in self.edges:
            callees.setdefault(call_edge.caller_id, []).append(call_edge.callee_id)
            callers.setdefault(call_edge.callee_id, []).append(call_edge.caller_id)
        object.__setattr__(
            self, "_callees_by_caller", {key: tuple(value) for key, value in callees.items()}
        )
        object.__setattr__(
            self, "_callers_by_callee", {key: tuple(value) for key, value in callers.items()}
        )

    def callees_of(self, caller_id: str) -> tuple[str, ...]:
        return self._callees_by_caller.get(caller_id, ())

    def callers_of(self, callee_id: str) -> tuple[str, ...]:
        return self._callers_by_callee.get(callee_id, ())

    def __len__(self) -> int:
        return len(self.edges)


# (start_line, end_line, function_declaration_id), sorted by start_line per
# file - Go functions never nest or overlap, so a call site's enclosing
# function is found with one bisect over its own file's functions rather
# than re-walking any syntax tree.
_FunctionSpan = tuple[int, int, str]


def _function_spans_by_file(repository: RepositoryIR) -> dict[str, tuple[_FunctionSpan, ...]]:
    spans_by_file: dict[str, tuple[_FunctionSpan, ...]] = {}
    for file in repository.files:
        spans = sorted(
            (declaration.location.start_line, declaration.location.end_line, declaration.id)
            for declaration in file.declarations
            if isinstance(declaration, FunctionDeclaration)
        )
        spans_by_file[file.id] = tuple(spans)
    return spans_by_file


def _enclosing_function_id(
    spans_by_file: Mapping[str, tuple[_FunctionSpan, ...]], file_id: str, line: int
) -> str | None:
    spans = spans_by_file.get(file_id, ())
    if not spans:
        return None
    starts = [span[0] for span in spans]
    index = bisect_right(starts, line) - 1
    if index < 0:
        return None
    start_line, end_line, declaration_id = spans[index]
    if start_line <= line <= end_line:
        return declaration_id
    return None


def _function_name_counts(symbols: SymbolTable) -> dict[str, int]:
    counts: dict[str, int] = {}
    for symbol in symbols.symbols():
        if isinstance(symbol, FunctionSymbol):
            counts[symbol.name] = counts.get(symbol.name, 0) + 1
    return counts


def _enrich_graph(graph: Graph, call_graph: CallGraph) -> Graph:
    metadata = replace(
        graph.metadata,
        statistics=graph.metadata.statistics.with_property("call_edge_count", len(call_graph)),
    )
    accumulator = GraphAccumulator(metadata=metadata)
    for node in graph.nodes:
        accumulator.add_node(node)
    for edge in graph.edges:
        accumulator.add_edge(edge)
    for call_edge in call_graph.edges:
        accumulator.add_edge(
            Edge(
                id=edge_id(call_edge.caller_id, call_edge.callee_id, RelationshipType.CALLS.value),
                source=call_edge.caller_id,
                target=call_edge.callee_id,
                relationship=RelationshipType.CALLS,
                properties=Properties.of(
                    call_count=call_edge.call_count,
                    call_site_lines=call_edge.call_site_lines,
                ),
            )
        )
    return accumulator.build()


class CallGraphAnalysis(Analysis):
    """Detects direct, statically identifiable function calls (`foo()`,
    `bar()`) and enriches the Knowledge Graph with `CALLS` edges.

    Consumes only the existing ReferenceIndex/SymbolTable/RepositoryIR - it
    never re-traverses Tree-sitter syntax. Because qualified calls
    (`pkg.Do()`, `x.Method()`) are selector expressions that the existing
    GoReferenceResolver does not resolve (out of scope for Milestone 3.4),
    those call sites produce no FUNCTION-kind reference for this analysis to
    consume, so only unqualified direct calls are detected. Dynamic
    dispatch, interface calls, method promotion/embedding, reflection,
    generics, closures, goroutines, and function literals are all
    explicitly out of scope.
    """

    @property
    def analysis_id(self) -> str:
        return CALL_GRAPH_ANALYSIS_ID

    @property
    def display_name(self) -> str:
        return "Call Graph"

    @property
    def version(self) -> str | None:
        return CALL_GRAPH_ANALYSIS_VERSION

    @property
    def required_capabilities(self) -> frozenset[Capability]:
        return frozenset(
            {
                Capability.IR,
                Capability.SYMBOL_TABLE,
                Capability.REFERENCE_INDEX,
                Capability.GRAPH,
            }
        )

    def execute(self, context: AnalysisContext) -> AnalysisResult:
        # AnalysisManager already validated required_capabilities before
        # calling execute() - these are guaranteed present, not user input.
        assert context.symbols is not None
        assert context.references is not None
        assert context.graph is not None

        repository = context.repository
        symbols = context.symbols
        references = context.references
        graph = context.graph

        spans_by_file = _function_spans_by_file(repository)
        name_counts = _function_name_counts(symbols)

        call_sites: dict[tuple[str, str], list[int]] = {}
        diagnostics: list[AnalysisDiagnostic] = []
        total_calls = 0
        resolved_calls = 0
        unresolved_calls = 0
        ambiguous_calls = 0

        for reference in _call_references(references):
            total_calls += 1

            caller_id = _enclosing_function_id(
                spans_by_file, reference.file_id, reference.location.start_line
            )
            if caller_id is None:
                # Call occurs outside any function body (e.g. a package-level
                # var initializer) - there is no Function node to be the
                # edge's source, so it cannot become a CALLS edge.
                continue

            if isinstance(reference, UnresolvedReference):
                unresolved_calls += 1
                diagnostics.append(
                    AnalysisDiagnostic(
                        message=f"unresolved call target: {reference.identifier!r}",
                        category="unresolved-call-target",
                        severity=AnalysisDiagnosticSeverity.WARNING,
                        location=reference.location,
                        reference_id=reference.id,
                    )
                )
                continue

            if not isinstance(reference, ResolvedReference):
                # Reference has exactly two concrete subclasses; this branch
                # is unreachable but keeps the narrowing below sound.
                continue

            symbol = symbols.get_symbol(reference.symbol_id)
            if not isinstance(symbol, FunctionSymbol):
                # Unreachable given the current reference resolver (a
                # resolved FUNCTION-kind reference always resolves to a
                # FunctionSymbol) - kept as a defensive guard, not a
                # user-facing diagnostic path.
                continue

            resolved_calls += 1
            if name_counts.get(reference.identifier, 0) > 1:
                ambiguous_calls += 1
                diagnostics.append(
                    AnalysisDiagnostic(
                        message=(
                            f"ambiguous call target: {reference.identifier!r} matches "
                            f"{name_counts[reference.identifier]} functions in the repository"
                        ),
                        category="ambiguous-call-target",
                        severity=AnalysisDiagnosticSeverity.WARNING,
                        location=reference.location,
                        symbol_id=symbol.id,
                        reference_id=reference.id,
                    )
                )

            key = (caller_id, symbol.declaration_id)
            call_sites.setdefault(key, []).append(reference.location.start_line)

        edges = tuple(
            CallEdge(
                caller_id=caller_id,
                callee_id=callee_id,
                call_count=len(lines),
                call_site_lines=tuple(sorted(lines)),
            )
            for (caller_id, callee_id), lines in sorted(call_sites.items())
        )
        call_graph = CallGraph(edges=edges)
        enriched_graph = _enrich_graph(graph, call_graph)

        return AnalysisResult.ok(
            analysis_id=self.analysis_id,
            repository_id=repository.id,
            diagnostics=tuple(diagnostics),
            artifacts={"graph": enriched_graph, "call_graph": call_graph},
            metadata={
                "total_calls": total_calls,
                "resolved_calls": resolved_calls,
                "unresolved_calls": unresolved_calls,
                "ambiguous_calls": ambiguous_calls,
                "generated_edges": len(edges),
            },
        )


def _call_references(references: ReferenceIndex) -> list[Reference]:
    # references() is already sorted by id, so downstream iteration is
    # deterministic regardless of how the index was populated.
    return [
        reference
        for reference in references.references()
        if reference.kind == ReferenceKind.FUNCTION
    ]
