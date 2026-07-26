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
from rig.graph.properties import Properties
from rig.ir.model import File, ImportDeclaration, SourceLocation
from rig.ir.repository import Package, RepositoryIR
from rig.parsers.pipeline import ParsedFile
from rig.parsers.treesitter.tree import SyntaxNode, SyntaxTree

DEPENDENCY_ANALYSIS_ID = "dependency-analysis"
DEPENDENCY_ANALYSIS_VERSION = "1.0.0"

# Node ids the graph is enriched with are `Package.id` values - the same ids
# StructuralGraphBuilder already uses for `Package` nodes - so DEPENDS_ON
# edges attach to existing nodes without ever creating new ones.


class DependencyKind(str, Enum):
    IMPORT = "IMPORT"
    TYPE = "TYPE"
    CALL = "CALL"


@dataclass(frozen=True, kw_only=True, slots=True)
class DependencyEdge:
    """One resolved dependency between two repository packages, for one
    specific reason. Multiple reasons between the same pair of packages are
    preserved as separate edges (deduplicated only within the same
    (source, target, kind) triple)."""

    source_id: str
    target_id: str
    kind: DependencyKind


@dataclass(frozen=True, kw_only=True)
class DependencyGraph:
    """Purpose-built architectural view over package-level dependencies - a
    dedicated, typed artifact (mirroring CallGraph and TypeRelationshipGraph)
    so later analyses (cycle detection, architecture validation, impact
    analysis, incremental analysis, the query engine) can query package
    dependencies directly instead of walking generic Knowledge Graph edges.
    """

    edges: tuple[DependencyEdge, ...] = ()
    _outgoing: Mapping[str, tuple[DependencyEdge, ...]] = field(
        init=False, repr=False, default_factory=dict
    )
    _incoming: Mapping[str, tuple[DependencyEdge, ...]] = field(
        init=False, repr=False, default_factory=dict
    )
    _by_kind: Mapping[DependencyKind, tuple[DependencyEdge, ...]] = field(
        init=False, repr=False, default_factory=dict
    )

    def __post_init__(self) -> None:
        outgoing: dict[str, list[DependencyEdge]] = {}
        incoming: dict[str, list[DependencyEdge]] = {}
        by_kind: dict[DependencyKind, list[DependencyEdge]] = {}
        for edge in self.edges:
            outgoing.setdefault(edge.source_id, []).append(edge)
            incoming.setdefault(edge.target_id, []).append(edge)
            by_kind.setdefault(edge.kind, []).append(edge)
        object.__setattr__(self, "_outgoing", {k: tuple(v) for k, v in outgoing.items()})
        object.__setattr__(self, "_incoming", {k: tuple(v) for k, v in incoming.items()})
        object.__setattr__(self, "_by_kind", {k: tuple(v) for k, v in by_kind.items()})

    def dependencies(self) -> tuple[DependencyEdge, ...]:
        return self.edges

    def outgoing(self, package_id: str) -> tuple[DependencyEdge, ...]:
        return self._outgoing.get(package_id, ())

    def incoming(self, package_id: str) -> tuple[DependencyEdge, ...]:
        return self._incoming.get(package_id, ())

    def by_kind(self, kind: DependencyKind) -> tuple[DependencyEdge, ...]:
        return self._by_kind.get(kind, ())

    def transitive(self, package_id: str) -> frozenset[str]:
        # Reachability only (not cycle detection or transitive reduction,
        # both explicitly out of scope) - a visited set just keeps this
        # correct and terminating in the presence of a dependency cycle.
        visited: set[str] = set()
        stack = [package_id]
        while stack:
            current = stack.pop()
            for edge in self.outgoing(current):
                if edge.target_id not in visited:
                    visited.add(edge.target_id)
                    stack.append(edge.target_id)
        return frozenset(visited)

    def __len__(self) -> int:
        return len(self.edges)


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


def _is_exported(name: str) -> bool:
    return bool(name) and name[0].isupper()


def _resolve_import_target(
    import_path: str, packages_by_name: Mapping[str, Package]
) -> Package | None:
    # Convention-based, repository-internal only: the last import path
    # segment is checked against declared package names. Resolving imports
    # outside the repository (module paths, vendoring, GOPATH) is
    # explicitly out of scope - an unmatched import is simply external.
    segment = import_path.rsplit("/", 1)[-1]
    return packages_by_name.get(segment)


def _imports_by_qualifier(file: File) -> dict[str, ImportDeclaration]:
    result: dict[str, ImportDeclaration] = {}
    for declaration in file.declarations:
        if isinstance(declaration, ImportDeclaration):
            if declaration.alias in ("_", "."):
                continue  # blank/dot imports have no usable qualifier
            qualifier = declaration.alias or declaration.import_path.rsplit("/", 1)[-1]
            result[qualifier] = declaration
    return result


def _unwrap_qualified_type(node: SyntaxNode) -> SyntaxNode | None:
    if node.type == "qualified_type":
        return node
    if node.type == "pointer_type":
        inner = next(iter(node.named_children()), None)
        if inner is not None and inner.type == "qualified_type":
            return inner
    return None


def _enrich_graph(graph: Graph, dependency_graph: DependencyGraph) -> Graph:
    metadata = replace(
        graph.metadata,
        statistics=graph.metadata.statistics.with_property(
            "dependency_edge_count", len(dependency_graph)
        ),
    )
    accumulator = GraphAccumulator(metadata=metadata)
    for node in graph.nodes:
        accumulator.add_node(node)
    for edge in graph.edges:
        accumulator.add_edge(edge)
    for dependency in dependency_graph.dependencies():
        accumulator.add_edge(
            Edge(
                # `edge_id` incorporates the kind so multiple reasons between
                # the same package pair get distinct ids, even though every
                # such edge shares the single DEPENDS_ON relationship type.
                id=edge_id(
                    dependency.source_id,
                    dependency.target_id,
                    f"DEPENDS_ON:{dependency.kind.value}",
                ),
                source=dependency.source_id,
                target=dependency.target_id,
                relationship=RelationshipType.DEPENDS_ON,
                properties=Properties.of(kind=dependency.kind.value),
            )
        )
    return accumulator.build()


class _Collector:
    """Accumulates deduplicated dependency edges and diagnostics while a
    repository's syntax trees are walked once. Not part of the public API -
    an internal helper for DependencyAnalysis.execute().
    """

    def __init__(self) -> None:
        self.diagnostics: list[AnalysisDiagnostic] = []
        self._seen: set[tuple[str, str, DependencyKind]] = set()
        self._edges: list[DependencyEdge] = []
        self.counts: dict[DependencyKind, int] = dict.fromkeys(DependencyKind, 0)

    def add(self, source_id: str, target_id: str, kind: DependencyKind) -> None:
        key = (source_id, target_id, kind)
        if key in self._seen:
            return
        self._seen.add(key)
        self._edges.append(DependencyEdge(source_id=source_id, target_id=target_id, kind=kind))
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

    def build(self) -> DependencyGraph:
        edges = sorted(self._edges, key=lambda e: (e.source_id, e.target_id, e.kind.value))
        return DependencyGraph(edges=tuple(edges))


def _process_import(
    declaration: ImportDeclaration,
    source_package: Package,
    packages_by_name: Mapping[str, Package],
    collector: _Collector,
) -> None:
    target = _resolve_import_target(declaration.import_path, packages_by_name)
    if target is None:
        return  # external import, not a repository package - not tracked
    if target.id == source_package.id:
        collector.diagnose(
            message=f"cyclic self-dependency: package {source_package.name!r} imports itself",
            category="cyclic-self-dependency",
            location=declaration.location,
        )
        return
    collector.add(source_package.id, target.id, DependencyKind.IMPORT)


def _handle_qualified_reference(
    qualified_type: SyntaxNode,
    file: File,
    source_package: Package,
    imports_by_qualifier: Mapping[str, ImportDeclaration],
    packages_by_name: Mapping[str, Package],
    collector: _Collector,
    kind: DependencyKind,
) -> None:
    package_node = qualified_type.child_by_field_name("package")
    if package_node is None:
        return
    qualifier = _text(package_node)
    location = _location(file.relative_path, qualified_type)

    import_declaration = imports_by_qualifier.get(qualifier)
    if import_declaration is None:
        # `qualified_type` is unambiguous package.Type syntax (unlike a call's
        # selector_expression, which could just as easily be a method call on
        # a value) - a qualifier not matching any import is a genuine anomaly.
        collector.diagnose(
            message=f"unknown package: {qualifier!r}",
            category="unknown-package",
            location=location,
        )
        return

    target = _resolve_import_target(import_declaration.import_path, packages_by_name)
    if target is None:
        return  # external package, not tracked

    if target.id == source_package.id:
        collector.diagnose(
            message=(
                f"cyclic self-dependency: package {source_package.name!r} "
                f"references itself via {qualifier!r}"
            ),
            category="cyclic-self-dependency",
            location=location,
        )
        return

    collector.add(source_package.id, target.id, kind)


def _process_struct_fields_for_type_deps(
    struct_type: SyntaxNode,
    file: File,
    source_package: Package,
    imports_by_qualifier: Mapping[str, ImportDeclaration],
    packages_by_name: Mapping[str, Package],
    collector: _Collector,
) -> None:
    field_list = next(
        (c for c in struct_type.named_children() if c.type == "field_declaration_list"), None
    )
    if field_list is None:
        return

    for field_declaration in field_list.named_children():
        if field_declaration.type != "field_declaration":
            continue
        type_node = field_declaration.child_by_field_name("type")
        if type_node is None:
            continue
        qualified = _unwrap_qualified_type(type_node)
        if qualified is None:
            continue
        _handle_qualified_reference(
            qualified,
            file,
            source_package,
            imports_by_qualifier,
            packages_by_name,
            collector,
            DependencyKind.TYPE,
        )


def _process_type_declaration_for_deps(
    type_declaration: SyntaxNode,
    file: File,
    source_package: Package,
    imports_by_qualifier: Mapping[str, ImportDeclaration],
    packages_by_name: Mapping[str, Package],
    collector: _Collector,
) -> None:
    # Only PUBLIC (exported) type declarations are considered dependency
    # sources here - an unexported type using another package's type still
    # requires that import, but this analysis's TYPE dependency kind is
    # scoped to a package's exported surface, per the milestone spec.
    for spec in type_declaration.named_children():
        if spec.type == "type_spec":
            name_node = spec.child_by_field_name("name")
            underlying = spec.child_by_field_name("type")
            if name_node is None or underlying is None:
                continue

            if spec.child_by_field_name("type_parameters") is not None:
                collector.diagnose(
                    message=f"unsupported dependency source: generic type {_text(name_node)!r}",
                    category="unsupported-dependency-source",
                    location=_location(file.relative_path, spec),
                )
                continue

            if not _is_exported(_text(name_node)):
                continue

            if underlying.type == "struct_type":
                _process_struct_fields_for_type_deps(
                    underlying,
                    file,
                    source_package,
                    imports_by_qualifier,
                    packages_by_name,
                    collector,
                )
            else:
                qualified = _unwrap_qualified_type(underlying)
                if qualified is not None:
                    _handle_qualified_reference(
                        qualified,
                        file,
                        source_package,
                        imports_by_qualifier,
                        packages_by_name,
                        collector,
                        DependencyKind.TYPE,
                    )

        elif spec.type == "type_alias":
            name_node = spec.child_by_field_name("name")
            underlying = spec.child_by_field_name("type")
            if name_node is None or underlying is None:
                continue
            if not _is_exported(_text(name_node)):
                continue
            qualified = _unwrap_qualified_type(underlying)
            if qualified is not None:
                _handle_qualified_reference(
                    qualified,
                    file,
                    source_package,
                    imports_by_qualifier,
                    packages_by_name,
                    collector,
                    DependencyKind.TYPE,
                )


def _walk_for_call_deps(
    root: SyntaxNode,
    file: File,
    source_package: Package,
    imports_by_qualifier: Mapping[str, ImportDeclaration],
    packages_by_name: Mapping[str, Package],
    collector: _Collector,
) -> None:
    stack: list[SyntaxNode] = [root]
    while stack:
        current = stack.pop()

        if current.type == "call_expression":
            function_node = current.child_by_field_name("function")
            if function_node is not None:
                if function_node.type == "selector_expression":
                    operand = function_node.child_by_field_name("operand")
                    if operand is not None and operand.type == "identifier":
                        qualifier = _text(operand)
                        import_declaration = imports_by_qualifier.get(qualifier)
                        if import_declaration is not None:
                            target = _resolve_import_target(
                                import_declaration.import_path, packages_by_name
                            )
                            if target is not None:
                                location = _location(file.relative_path, current)
                                if target.id == source_package.id:
                                    collector.diagnose(
                                        message=(
                                            f"cyclic self-dependency: package "
                                            f"{source_package.name!r} calls itself via {qualifier!r}"
                                        ),
                                        category="cyclic-self-dependency",
                                        location=location,
                                    )
                                else:
                                    collector.add(source_package.id, target.id, DependencyKind.CALL)
                        # else: qualifier matches no import - almost certainly
                        # a method call on a value (`x.Method()`), which is
                        # inherently ambiguous with a package-qualified call
                        # at this syntax level - silently skip, not an error.
                elif function_node.type != "identifier":
                    collector.diagnose(
                        message="unsupported dependency source: unrecognized call target shape",
                        category="unsupported-dependency-source",
                        location=_location(file.relative_path, current),
                    )

        stack.extend(current.named_children())


class DependencyAnalysis(Analysis):
    """Computes package-level dependencies (imports, cross-package type
    usage, cross-package function calls) and enriches the Knowledge Graph
    with `DEPENDS_ON` edges.

    Requires the parsed syntax trees (not just RepositoryIR + SymbolTable)
    for the same reason CallGraphAnalysis and TypeRelationshipAnalysis do:
    cross-package type/call usage is expressed via qualified references
    (`pkg.Type`, `pkg.Func()`) that earlier milestones deliberately left
    unresolved (CallGraph and TypeRelationshipGraph are, by construction,
    intra-package only - qualified/selector references were explicitly out
    of scope wherever they were produced). Consuming those artifacts here
    would therefore surface no cross-package information at all; this
    analysis performs its own qualified-reference walk instead, while still
    resolving *which* repository package a reference belongs to via
    RepositoryIR's packages rather than reconstructing that from scratch.

    Deliberately does not attempt: cycle detection, layer validation,
    architectural rule enforcement, transitive reduction, build graph
    optimization, import resolution outside the repository, or versioned
    modules.
    """

    def __init__(self, parsed_files: Sequence[ParsedFile]) -> None:
        self._trees_by_path: dict[Path, SyntaxTree] = {
            parsed.file.relative_path: parsed.result.syntax_tree
            for parsed in parsed_files
            if parsed.result.success and parsed.result.syntax_tree is not None
        }

    @property
    def analysis_id(self) -> str:
        return DEPENDENCY_ANALYSIS_ID

    @property
    def display_name(self) -> str:
        return "Package Dependencies"

    @property
    def version(self) -> str | None:
        return DEPENDENCY_ANALYSIS_VERSION

    @property
    def required_capabilities(self) -> frozenset[Capability]:
        return frozenset({Capability.IR, Capability.SYMBOL_TABLE, Capability.GRAPH})

    def execute(self, context: AnalysisContext) -> AnalysisResult:
        # AnalysisManager already validated required_capabilities before
        # calling execute() - these are guaranteed present, not user input.
        assert context.symbols is not None
        assert context.graph is not None

        repository: RepositoryIR = context.repository
        graph = context.graph

        packages_by_name = {package.name: package for package in repository.packages}
        collector = _Collector()

        for file in repository.files:
            if file.package_name is None:
                continue  # orphan files don't participate in package-level dependencies
            source_package = packages_by_name.get(file.package_name)
            if source_package is None:
                continue  # defensive: RepositoryIR always groups by this exact name

            imports_by_qualifier = _imports_by_qualifier(file)
            for declaration in file.declarations:
                if isinstance(declaration, ImportDeclaration):
                    _process_import(declaration, source_package, packages_by_name, collector)

            tree = self._trees_by_path.get(file.relative_path)
            if tree is None:
                continue

            for child in tree.root.named_children():
                if child.type == "type_declaration":
                    _process_type_declaration_for_deps(
                        child,
                        file,
                        source_package,
                        imports_by_qualifier,
                        packages_by_name,
                        collector,
                    )

            _walk_for_call_deps(
                tree.root, file, source_package, imports_by_qualifier, packages_by_name, collector
            )

        dependency_graph = collector.build()
        enriched_graph = _enrich_graph(graph, dependency_graph)

        metadata = {
            "package_count": len(repository.packages),
            "dependency_count": len(dependency_graph),
            "import_dependencies": collector.counts[DependencyKind.IMPORT],
            "type_dependencies": collector.counts[DependencyKind.TYPE],
            "call_dependencies": collector.counts[DependencyKind.CALL],
        }

        return AnalysisResult.ok(
            analysis_id=self.analysis_id,
            repository_id=repository.id,
            diagnostics=tuple(collector.diagnostics),
            artifacts={"graph": enriched_graph, "dependencies": dependency_graph},
            metadata=metadata,
        )
