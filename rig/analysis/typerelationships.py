from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from enum import Enum

from rig.analysis.capability import Capability
from rig.analysis.context import AnalysisContext
from rig.analysis.diagnostics import AnalysisDiagnostic, AnalysisDiagnosticSeverity
from rig.analysis.interface import Analysis
from rig.analysis.result import AnalysisResult
from rig.graph.builder import GraphAccumulator
from rig.graph.identifiers import edge_id
from rig.graph.model import Edge, Graph, RelationshipType
from rig.ir.model import DeclaredTypeUses, MethodTypeUses, SourceLocation
from rig.ir.repository import RepositoryIR
from rig.symbols.table import SymbolTable
from rig.types.builder import GoTypeBuilder
from rig.types.index import TypeIndex
from rig.types.model import Type

TYPE_RELATIONSHIP_ANALYSIS_ID = "type-relationships"
TYPE_RELATIONSHIP_ANALYSIS_VERSION = "1.0.0"

# Node ids the graph is enriched with are `declaration_id` values - the same
# ids StructuralGraphBuilder already uses for `Type` nodes - so relationship
# edges attach to existing nodes without ever creating new ones.


class TypeRelationshipKind(str, Enum):
    EMBEDS = "EMBEDS"
    ALIASES = "ALIASES"
    DECLARES_FIELD_OF_TYPE = "DECLARES_FIELD_OF_TYPE"
    DECLARES_METHOD_RETURNING = "DECLARES_METHOD_RETURNING"
    DECLARES_METHOD_PARAMETER = "DECLARES_METHOD_PARAMETER"


@dataclass(frozen=True, kw_only=True, slots=True)
class TypeRelationship:
    """One resolved relationship between two repository-declared types.

    `source_id`/`target_id` are the related types' `declaration_id` values
    (not their `Type.id`) - the exact ids StructuralGraphBuilder already
    uses for `Type` graph nodes, so this artifact's identity scheme lines
    up with the graph's without any translation step.
    """

    source_id: str
    target_id: str
    kind: TypeRelationshipKind


@dataclass(frozen=True, kw_only=True)
class TypeRelationshipGraph:
    """Purpose-built view over relationships between declared types - a
    dedicated, typed artifact (mirroring CallGraph) so later analyses
    (dependency analysis, impact analysis, architecture extraction, query
    execution) can query caller/callee-style relationships directly instead
    of walking generic Knowledge Graph edges.
    """

    edges: tuple[TypeRelationship, ...] = ()
    _outgoing: Mapping[str, tuple[TypeRelationship, ...]] = field(
        init=False, repr=False, default_factory=dict
    )
    _incoming: Mapping[str, tuple[TypeRelationship, ...]] = field(
        init=False, repr=False, default_factory=dict
    )
    _by_kind: Mapping[TypeRelationshipKind, tuple[TypeRelationship, ...]] = field(
        init=False, repr=False, default_factory=dict
    )

    def __post_init__(self) -> None:
        outgoing: dict[str, list[TypeRelationship]] = {}
        incoming: dict[str, list[TypeRelationship]] = {}
        by_kind: dict[TypeRelationshipKind, list[TypeRelationship]] = {}
        for relationship in self.edges:
            outgoing.setdefault(relationship.source_id, []).append(relationship)
            incoming.setdefault(relationship.target_id, []).append(relationship)
            by_kind.setdefault(relationship.kind, []).append(relationship)
        object.__setattr__(self, "_outgoing", {k: tuple(v) for k, v in outgoing.items()})
        object.__setattr__(self, "_incoming", {k: tuple(v) for k, v in incoming.items()})
        object.__setattr__(self, "_by_kind", {k: tuple(v) for k, v in by_kind.items()})

    def relationships(self) -> tuple[TypeRelationship, ...]:
        return self.edges

    def outgoing(self, type_id: str) -> tuple[TypeRelationship, ...]:
        return self._outgoing.get(type_id, ())

    def incoming(self, type_id: str) -> tuple[TypeRelationship, ...]:
        return self._incoming.get(type_id, ())

    def by_kind(self, kind: TypeRelationshipKind) -> tuple[TypeRelationship, ...]:
        return self._by_kind.get(kind, ())

    def __len__(self) -> int:
        return len(self.edges)


def _enrich_graph(graph: Graph, relationship_graph: TypeRelationshipGraph) -> Graph:
    metadata = replace(
        graph.metadata,
        statistics=graph.metadata.statistics.with_property(
            "type_relationship_edge_count", len(relationship_graph)
        ),
    )
    accumulator = GraphAccumulator(metadata=metadata)
    for node in graph.nodes:
        accumulator.add_node(node)
    for edge in graph.edges:
        accumulator.add_edge(edge)
    for relationship in relationship_graph.relationships():
        accumulator.add_edge(
            Edge(
                id=edge_id(relationship.source_id, relationship.target_id, relationship.kind.value),
                source=relationship.source_id,
                target=relationship.target_id,
                relationship=RelationshipType(relationship.kind.value),
            )
        )
    return accumulator.build()


class _Collector:
    """Accumulates deduplicated relationships and diagnostics while a
    repository's IR type-use facts are consumed. Not part of the public API -
    an internal helper for TypeRelationshipAnalysis.execute().
    """

    def __init__(self, type_index: TypeIndex) -> None:
        self.type_index = type_index
        self.diagnostics: list[AnalysisDiagnostic] = []
        self._seen: set[tuple[str, str, TypeRelationshipKind]] = set()
        self._relationships: list[TypeRelationship] = []
        self.counts: dict[TypeRelationshipKind, int] = dict.fromkeys(TypeRelationshipKind, 0)

    def add(self, source_id: str, target_id: str, kind: TypeRelationshipKind) -> None:
        key = (source_id, target_id, kind)
        if key in self._seen:
            return
        self._seen.add(key)
        self._relationships.append(
            TypeRelationship(source_id=source_id, target_id=target_id, kind=kind)
        )
        self.counts[kind] += 1

    def diagnose(self, message: str, category: str, location: SourceLocation | None) -> None:
        self.diagnostics.append(
            AnalysisDiagnostic(
                message=message,
                category=category,
                severity=AnalysisDiagnosticSeverity.WARNING,
                location=location,
            )
        )

    def build(self) -> TypeRelationshipGraph:
        return TypeRelationshipGraph(
            edges=tuple(sorted(self._relationships, key=_relationship_key))
        )

    def resolve_type_name(
        self, name: str, package: str | None, location: SourceLocation
    ) -> Type | None:
        candidates = [t for t in self.type_index.by_name(name) if t.package == package]
        if len(candidates) > 1:
            self.diagnose(
                message=(
                    f"ambiguous type lookup: {name!r} matches {len(candidates)} types "
                    f"in package {package!r}"
                ),
                category="ambiguous-type-lookup",
                location=location,
            )
            return None
        if len(candidates) == 1:
            return candidates[0]
        self.diagnose(
            message=f"unknown repository type: {name!r}",
            category="unknown-repository-type",
            location=location,
        )
        return None

    def find_declaring_type(self, name: str, package: str | None, start_line: int) -> Type | None:
        for candidate in self.type_index.by_name(name):
            if candidate.package == package and candidate.location.start_line == start_line:
                return candidate
        return None


def _relationship_key(relationship: TypeRelationship) -> tuple[str, str, str]:
    return (relationship.source_id, relationship.target_id, relationship.kind.value)


def _process_declared_type(declared: DeclaredTypeUses, collector: _Collector) -> None:
    if declared.is_generic:
        collector.diagnose(
            message=f"unsupported declaration: generic type {declared.name!r}",
            category="unsupported-declaration",
            location=declared.location,
        )
        return

    if declared.kind == "struct":
        declaring = collector.find_declaring_type(
            declared.name, declared.package, declared.start_line
        )
        if declaring is None:
            return  # defensive: GoTypeBuilder should always have indexed this declaration
        for field_use in declared.fields:
            name = field_use.target.name
            if name is None:
                continue
            target = collector.resolve_type_name(name, declared.package, field_use.target.location)
            if target is None:
                continue
            kind = (
                TypeRelationshipKind.EMBEDS
                if field_use.is_embedded
                else TypeRelationshipKind.DECLARES_FIELD_OF_TYPE
            )
            collector.add(declaring.declaration_id, target.declaration_id, kind)

    elif declared.kind == "alias":
        declaring = collector.find_declaring_type(
            declared.name, declared.package, declared.start_line
        )
        if declaring is None:
            return
        alias_target = declared.alias_target
        if alias_target is None or alias_target.name is None:
            return
        target = collector.resolve_type_name(
            alias_target.name, declared.package, alias_target.location
        )
        if target is None:
            return
        collector.add(declaring.declaration_id, target.declaration_id, TypeRelationshipKind.ALIASES)


def _process_method(method: MethodTypeUses, collector: _Collector) -> None:
    if method.receiver.name is None:
        collector.diagnose(
            message="unsupported declaration: method receiver is not a simple named type",
            category="unsupported-declaration",
            location=method.receiver.location,
        )
        return

    declaring = collector.resolve_type_name(
        method.receiver.name, method.package, method.receiver.location
    )
    if declaring is None:
        return

    for parameter in method.parameters:
        if parameter.name is None:
            continue
        target = collector.resolve_type_name(parameter.name, method.package, parameter.location)
        if target is None:
            continue
        collector.add(
            declaring.declaration_id,
            target.declaration_id,
            TypeRelationshipKind.DECLARES_METHOD_PARAMETER,
        )

    for result in method.returns:
        if result.name is None:
            continue
        target = collector.resolve_type_name(result.name, method.package, result.location)
        if target is None:
            continue
        collector.add(
            declaring.declaration_id,
            target.declaration_id,
            TypeRelationshipKind.DECLARES_METHOD_RETURNING,
        )


class TypeRelationshipAnalysis(Analysis):
    """Discovers structural relationships between repository-declared types
    (embedding, aliasing, field/parameter/return type usage) and enriches
    the Knowledge Graph with them.

    Language-neutral: it consumes the IR's type-use facts (`DeclaredTypeUses`
    / `MethodTypeUses`) that a frontend already extracted, and resolves type
    names via the Type Index / Symbol Table. It never touches a syntax tree,
    so nothing here would change for a future non-Go frontend.

    Deliberately does not attempt: interface satisfaction, inheritance,
    generic constraints, method sets, promoted methods, type checking,
    assignability, conversions, pointer analysis, reflection, or import
    resolution (qualified `pkg.Type` references are not modeled here).
    """

    @property
    def analysis_id(self) -> str:
        return TYPE_RELATIONSHIP_ANALYSIS_ID

    @property
    def display_name(self) -> str:
        return "Type Relationships"

    @property
    def version(self) -> str | None:
        return TYPE_RELATIONSHIP_ANALYSIS_VERSION

    @property
    def required_capabilities(self) -> frozenset[Capability]:
        return frozenset({Capability.IR, Capability.SYMBOL_TABLE, Capability.GRAPH})

    def execute(self, context: AnalysisContext) -> AnalysisResult:
        # AnalysisManager already validated required_capabilities before
        # calling execute() - these are guaranteed present, not user input.
        assert context.symbols is not None
        assert context.graph is not None

        repository: RepositoryIR = context.repository
        symbols: SymbolTable = context.symbols
        graph = context.graph

        type_index = GoTypeBuilder().build(repository, symbols)
        collector = _Collector(type_index)

        for file in repository.files:
            for declared in file.declared_type_uses:
                _process_declared_type(declared, collector)
            for method in file.method_type_uses:
                _process_method(method, collector)

        relationship_graph = collector.build()
        enriched_graph = _enrich_graph(graph, relationship_graph)

        metadata = {
            "embedded_relationships": collector.counts[TypeRelationshipKind.EMBEDS],
            "aliases": collector.counts[TypeRelationshipKind.ALIASES],
            "field_relationships": collector.counts[TypeRelationshipKind.DECLARES_FIELD_OF_TYPE],
            "parameter_relationships": collector.counts[
                TypeRelationshipKind.DECLARES_METHOD_PARAMETER
            ],
            "return_relationships": collector.counts[
                TypeRelationshipKind.DECLARES_METHOD_RETURNING
            ],
            "total_relationships": len(relationship_graph),
        }

        return AnalysisResult.ok(
            analysis_id=self.analysis_id,
            repository_id=repository.id,
            diagnostics=tuple(collector.diagnostics),
            artifacts={"graph": enriched_graph, "type_relationships": relationship_graph},
            metadata=metadata,
        )
