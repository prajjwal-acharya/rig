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
from rig.graph.properties import Properties
from rig.ir.model import File, ImportDeclaration, QualifiedUseKind, SourceLocation
from rig.ir.repository import Package, RepositoryIR

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
    repository's IR dependency-use facts are consumed. Not part of the public
    API - an internal helper for DependencyAnalysis.execute().
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


def _handle_qualified_type(
    qualifier: str,
    location: SourceLocation,
    source_package: Package,
    imports_by_qualifier: Mapping[str, ImportDeclaration],
    packages_by_name: Mapping[str, Package],
    collector: _Collector,
) -> None:
    import_declaration = imports_by_qualifier.get(qualifier)
    if import_declaration is None:
        # A package-qualified type whose qualifier matches no import is a
        # genuine anomaly (unlike a call's selector, which could be a method).
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

    collector.add(source_package.id, target.id, DependencyKind.TYPE)


def _handle_qualified_call(
    qualifier: str,
    location: SourceLocation,
    source_package: Package,
    imports_by_qualifier: Mapping[str, ImportDeclaration],
    packages_by_name: Mapping[str, Package],
    collector: _Collector,
) -> None:
    import_declaration = imports_by_qualifier.get(qualifier)
    if import_declaration is None:
        # A qualifier matching no import is almost certainly a method call on a
        # value (`x.Method()`) - inherently ambiguous with a package-qualified
        # call at this level; silently skip, not an error.
        return

    target = _resolve_import_target(import_declaration.import_path, packages_by_name)
    if target is None:
        return

    if target.id == source_package.id:
        collector.diagnose(
            message=(
                f"cyclic self-dependency: package {source_package.name!r} "
                f"calls itself via {qualifier!r}"
            ),
            category="cyclic-self-dependency",
            location=location,
        )
        return

    collector.add(source_package.id, target.id, DependencyKind.CALL)


def _report_unsupported(file: File, collector: _Collector) -> None:
    for unsupported in file.unsupported_dependency_uses:
        if unsupported.reason == "generic_type":
            collector.diagnose(
                message=f"unsupported dependency source: generic type {unsupported.name!r}",
                category="unsupported-dependency-source",
                location=unsupported.location,
            )
        elif unsupported.reason == "unrecognized_call":
            collector.diagnose(
                message="unsupported dependency source: unrecognized call target shape",
                category="unsupported-dependency-source",
                location=unsupported.location,
            )


class DependencyAnalysis(Analysis):
    """Computes package-level dependencies (imports, cross-package type
    usage, cross-package function calls) and enriches the Knowledge Graph
    with `DEPENDS_ON` edges.

    Language-neutral: it consumes the IR's `ImportDeclaration`s and the
    qualified-use facts (`QualifiedUse`) that a frontend already extracted,
    resolving each qualifier to a repository package via the IR's packages. It
    never touches a syntax tree, so nothing here would change for a future
    non-Go frontend.

    Deliberately does not attempt: cycle detection, layer validation,
    architectural rule enforcement, transitive reduction, build graph
    optimization, import resolution outside the repository, or versioned
    modules.
    """

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

            for use in file.qualified_uses:
                if use.kind == QualifiedUseKind.TYPE:
                    _handle_qualified_type(
                        use.qualifier,
                        use.location,
                        source_package,
                        imports_by_qualifier,
                        packages_by_name,
                        collector,
                    )
                else:
                    _handle_qualified_call(
                        use.qualifier,
                        use.location,
                        source_package,
                        imports_by_qualifier,
                        packages_by_name,
                        collector,
                    )

            _report_unsupported(file, collector)

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
