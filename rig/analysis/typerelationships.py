from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from enum import Enum
from pathlib import Path

from rig.analysis.capability import Capability
from rig.analysis.context import AnalysisContext
from rig.analysis.diagnostics import AnalysisDiagnostic, AnalysisDiagnosticSeverity
from rig.analysis.interface import Analysis
from rig.analysis.result import AnalysisResult
from rig.graph.builder import GraphAccumulator
from rig.graph.identifiers import edge_id
from rig.graph.model import Edge, Graph, RelationshipType
from rig.ir.model import File, SourceLocation
from rig.ir.repository import RepositoryIR
from rig.parsers.pipeline import ParsedFile
from rig.parsers.treesitter.tree import SyntaxNode, SyntaxTree
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


# Go's predeclared type names - never repository declarations, so field/
# parameter/return/alias references to them are silently ignored (neither
# a relationship nor a diagnostic), mirroring GoReferenceResolver's handling
# of predeclared identifiers.
_GO_BUILTIN_TYPES = frozenset(
    {
        "any",
        "bool",
        "byte",
        "complex64",
        "complex128",
        "error",
        "float32",
        "float64",
        "int",
        "int8",
        "int16",
        "int32",
        "int64",
        "rune",
        "string",
        "uint",
        "uint8",
        "uint16",
        "uint32",
        "uint64",
        "uintptr",
    }
)


def _location(relative_path: Path, node: SyntaxNode) -> SourceLocation:
    return SourceLocation(
        relative_path=relative_path,
        start_line=node.start_point.row,
        start_column=node.start_point.column,
        end_line=node.end_point.row,
        end_column=node.end_point.column,
        start_byte=node.start_byte,
        end_byte=node.end_byte,
    )


def _text(node: SyntaxNode) -> str:
    return node.text.decode("utf-8", errors="replace")


def _unwrap_named_type(node: SyntaxNode) -> SyntaxNode | None:
    # Only a bare name, or a single pointer indirection to one, is treated
    # as a directly identifiable named type. Qualified names (import-
    # qualified, out of scope), slices, maps, arrays, channels, function
    # types, and generic instantiations are all deliberately unsupported -
    # they are not "explicit language constructs" naming a single repo type.
    if node.type == "type_identifier":
        return node
    if node.type == "pointer_type":
        inner = next(iter(node.named_children()), None)
        if inner is not None and inner.type == "type_identifier":
            return inner
        return None
    return None


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
    repository's syntax trees are walked once. Not part of the public API -
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
        if name in _GO_BUILTIN_TYPES:
            return None
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


def _process_struct_fields(
    struct_type: SyntaxNode,
    declaring: Type,
    file: File,
    collector: _Collector,
) -> None:
    field_list = next(
        (c for c in struct_type.named_children() if c.type == "field_declaration_list"), None
    )
    if field_list is None:
        return

    for field_decl in field_list.named_children():
        if field_decl.type != "field_declaration":
            continue
        type_node = field_decl.child_by_field_name("type")
        if type_node is None:
            continue
        named = _unwrap_named_type(type_node)
        if named is None:
            continue

        location = _location(file.relative_path, named)
        target = collector.resolve_type_name(_text(named), file.package_name, location)
        if target is None:
            continue

        is_embedded = field_decl.child_by_field_name("name") is None
        kind = (
            TypeRelationshipKind.EMBEDS
            if is_embedded
            else TypeRelationshipKind.DECLARES_FIELD_OF_TYPE
        )
        collector.add(declaring.declaration_id, target.declaration_id, kind)


def _process_alias(
    type_alias: SyntaxNode,
    declaring: Type,
    file: File,
    collector: _Collector,
) -> None:
    underlying = type_alias.child_by_field_name("type")
    if underlying is None:
        return
    named = _unwrap_named_type(underlying)
    if named is None:
        return

    location = _location(file.relative_path, named)
    target = collector.resolve_type_name(_text(named), file.package_name, location)
    if target is None:
        return

    collector.add(declaring.declaration_id, target.declaration_id, TypeRelationshipKind.ALIASES)


def _process_type_declaration(
    type_declaration: SyntaxNode, file: File, collector: _Collector
) -> None:
    for spec in type_declaration.named_children():
        if spec.type == "type_spec":
            name_node = spec.child_by_field_name("name")
            underlying = spec.child_by_field_name("type")
            if name_node is None or underlying is None:
                continue

            if spec.child_by_field_name("type_parameters") is not None:
                collector.diagnose(
                    message=f"unsupported declaration: generic type {_text(name_node)!r}",
                    category="unsupported-declaration",
                    location=_location(file.relative_path, spec),
                )
                continue

            declaring = collector.find_declaring_type(
                _text(name_node), file.package_name, spec.start_point.row
            )
            if declaring is None:
                continue  # defensive: GoTypeBuilder should always have indexed this declaration
            if underlying.type == "struct_type":
                _process_struct_fields(underlying, declaring, file, collector)

        elif spec.type == "type_alias":
            name_node = spec.child_by_field_name("name")
            if name_node is None:
                continue
            declaring = collector.find_declaring_type(
                _text(name_node), file.package_name, spec.start_point.row
            )
            if declaring is None:
                continue
            _process_alias(spec, declaring, file, collector)


def _process_method_declaration(method: SyntaxNode, file: File, collector: _Collector) -> None:
    receiver = method.child_by_field_name("receiver")
    if receiver is None:
        return
    receiver_decl = next(iter(receiver.named_children()), None)
    if receiver_decl is None:
        return
    receiver_type_node = receiver_decl.child_by_field_name("type")
    if receiver_type_node is None:
        return

    named = _unwrap_named_type(receiver_type_node)
    if named is None:
        collector.diagnose(
            message="unsupported declaration: method receiver is not a simple named type",
            category="unsupported-declaration",
            location=_location(file.relative_path, receiver_type_node),
        )
        return

    receiver_location = _location(file.relative_path, named)
    declaring = collector.resolve_type_name(_text(named), file.package_name, receiver_location)
    if declaring is None:
        return

    parameters = method.child_by_field_name("parameters")
    if parameters is not None:
        for parameter in parameters.named_children():
            if parameter.type != "parameter_declaration":
                continue
            type_node = parameter.child_by_field_name("type")
            if type_node is None:
                continue
            param_named = _unwrap_named_type(type_node)
            if param_named is None:
                continue
            location = _location(file.relative_path, param_named)
            target = collector.resolve_type_name(_text(param_named), file.package_name, location)
            if target is None:
                continue
            collector.add(
                declaring.declaration_id,
                target.declaration_id,
                TypeRelationshipKind.DECLARES_METHOD_PARAMETER,
            )

    result = method.child_by_field_name("result")
    if result is None:
        return
    result_nodes = (
        [
            c.child_by_field_name("type")
            for c in result.named_children()
            if c.type == "parameter_declaration"
        ]
        if result.type == "parameter_list"
        else [result]
    )
    for type_node in result_nodes:
        if type_node is None:
            continue
        result_named = _unwrap_named_type(type_node)
        if result_named is None:
            continue
        location = _location(file.relative_path, result_named)
        target = collector.resolve_type_name(_text(result_named), file.package_name, location)
        if target is None:
            continue
        collector.add(
            declaring.declaration_id,
            target.declaration_id,
            TypeRelationshipKind.DECLARES_METHOD_RETURNING,
        )


def _process_file(file: File, tree: SyntaxTree, collector: _Collector) -> None:
    for child in tree.root.named_children():
        if child.type == "type_declaration":
            _process_type_declaration(child, file, collector)
        elif child.type == "method_declaration":
            _process_method_declaration(child, file, collector)


class TypeRelationshipAnalysis(Analysis):
    """Discovers structural relationships between repository-declared types
    (embedding, aliasing, field/parameter/return type usage) and enriches
    the Knowledge Graph with them.

    Requires the parsed syntax trees (not just RepositoryIR + SymbolTable)
    because struct fields and method parameter/return type annotations are
    intentionally absent from the IR - Tree-sitter access is confined
    entirely to this analysis, mirroring GoReferenceResolver's precedent.
    Type name resolution itself is delegated to the Type Index/SymbolTable
    (via GoTypeBuilder) rather than reconstructed from syntax.

    Deliberately does not attempt: interface satisfaction, inheritance,
    generic constraints, method sets, promoted methods, type checking,
    assignability, conversions, pointer analysis, reflection, or import
    resolution (qualified `pkg.Type` references are skipped entirely).
    """

    def __init__(self, parsed_files: Sequence[ParsedFile]) -> None:
        self._trees_by_path: dict[Path, SyntaxTree] = {
            parsed.file.relative_path: parsed.result.syntax_tree
            for parsed in parsed_files
            if parsed.result.success and parsed.result.syntax_tree is not None
        }

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
            tree = self._trees_by_path.get(file.relative_path)
            if tree is None:
                continue
            _process_file(file, tree, collector)

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
