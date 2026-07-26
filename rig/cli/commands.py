from __future__ import annotations

import sys
import time
from collections import Counter

from rig.cli.formatting import (
    done,
    format_count,
    format_duration,
    format_size,
    print_count_table,
    print_percentage_table,
    progress,
    section,
    trim,
)
from rig.cli.pipeline import (
    PipelineError,
    build_language_report,
    build_parsed_files,
    build_reference_index,
    build_repository,
    build_snapshot,
    build_snapshot_with_filtered,
    build_structural_graph,
    build_symbol_table,
    build_type_index,
    enrich_graph_with_references,
    run_semantic_analyses,
)
from rig.ir.model import (
    FunctionDeclaration,
    ImportDeclaration,
    TypeDeclaration,
    VariableDeclaration,
)
from rig.ir.repository import RepositoryIR
from rig.languages.pipeline import RepositoryLanguageReport
from rig.parsers.model import DiagnosticSeverity
from rig.plugins import PluginCache, PluginContext, PluginLogger, PluginManager
from rig.references.model import ResolvedReference, UnresolvedReference
from rig.scanner.models import FilteredWalkResult, RepositorySnapshot

# --- shared helpers ----------------------------------------------------------


def _top_level_ignored(filtered: FilteredWalkResult) -> list[str]:
    excluded_dir_paths = {directory.relative_path for directory in filtered.excluded_directories}

    entries = [
        f"{directory.relative_path.as_posix()}/"
        for directory in filtered.excluded_directories
        if directory.relative_path.parent not in excluded_dir_paths
    ]
    entries += [
        file.relative_path.as_posix()
        for file in filtered.excluded_files
        if file.relative_path.parent not in excluded_dir_paths
    ]
    return sorted(entries)


def _print_verbose_files(
    snapshot: RepositorySnapshot, language_report: RepositoryLanguageReport
) -> None:
    languages_by_path = {
        entry.file.relative_path: entry.language for entry in language_report.files
    }

    for file in sorted(snapshot.files, key=lambda f: f.relative_path.as_posix()):
        print(file.relative_path.as_posix())
        metadata = file.metadata
        if metadata is not None:
            checksum = metadata.checksum_sha256
            print(f"  Size: {format_size(metadata.size_bytes)}")
            print(f"  SHA256: {checksum[:8] + '...' if checksum else 'N/A'}")
            print(f"  Modified: {metadata.modified_at:%Y-%m-%d}")
            print(f"  Hidden: {'Yes' if metadata.is_hidden else 'No'}")
        language = languages_by_path.get(file.relative_path)
        if language is not None:
            print(f"  Language: {language.display_name}")
        print()


def _print_language_statistics(report: RepositoryLanguageReport) -> None:
    print("Languages:")
    if not report.statistics:
        print("  (None)")
        return

    name_width = max(len(entry.language.display_name) for entry in report.statistics)
    for entry in report.statistics:
        print(f"  {entry.language.display_name:<{name_width}}  {entry.count:>7}")


def _language_percentage_rows(report: RepositoryLanguageReport) -> list[tuple[str, float]]:
    total = sum(entry.count for entry in report.statistics)
    if total == 0:
        return []
    return [(entry.language.display_name, entry.count / total * 100) for entry in report.statistics]


def _declaration_counts(repository: RepositoryIR) -> Counter[str]:
    counts: Counter[str] = Counter()
    for file in repository.files:
        for declaration in file.declarations:
            if isinstance(declaration, FunctionDeclaration):
                counts["Functions"] += 1
            elif isinstance(declaration, TypeDeclaration):
                counts["Types"] += 1
            elif isinstance(declaration, VariableDeclaration):
                counts["Constants" if declaration.is_constant else "Variables"] += 1
            elif isinstance(declaration, ImportDeclaration):
                counts["Imports"] += 1
    return counts


# --- scan (preserved, unchanged) ---------------------------------------------


def run_scan(path: str, *, verbose: bool = False) -> int:
    start = time.perf_counter()

    try:
        snapshot, filtered = build_snapshot_with_filtered(path)
    except PipelineError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    language_report = build_language_report(snapshot)

    plugin_manager = PluginManager()
    plugin_context = PluginContext(
        snapshot=snapshot,
        config={},
        logger=PluginLogger("cli"),
        cache=PluginCache(),
    )
    plugin_report = plugin_manager.load_all([], plugin_context)

    elapsed_ms = (time.perf_counter() - start) * 1000

    print(f"Repository: {snapshot.root}")
    print(f"Git Repository: {'Yes' if snapshot.git.is_git_repository else 'No'}")
    print()
    print(f"Files: {snapshot.statistics.files}")
    print(f"Directories: {snapshot.statistics.directories}")
    print()

    print("Ignored:")
    ignored = _top_level_ignored(filtered)
    for ignored_entry in ignored or ["(None)"]:
        print(f"  {ignored_entry}")
    print()

    _print_language_statistics(language_report)
    print()

    print("Plugins:")
    if plugin_report.registered:
        for registered_plugin in plugin_report.registered:
            print(f"  {registered_plugin.manifest.name} ({registered_plugin.manifest.version})")
    else:
        print("  (None)")
    print()

    if verbose:
        _print_verbose_files(snapshot, language_report)

    print(f"Scan completed in {elapsed_ms:.0f} ms")
    return 0


# --- detect -------------------------------------------------------------


def run_detect(path: str) -> int:
    start = time.perf_counter()

    try:
        progress("Scanning")
        snapshot = build_snapshot(path)
        progress("Detecting languages")
        language_report = build_language_report(snapshot)
    except PipelineError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    elapsed = time.perf_counter() - start

    section("Repository")
    print(f"Path: {snapshot.root}")
    print(f"Files: {format_count(snapshot.statistics.files)}")
    print()

    section("Languages")
    print_percentage_table(_language_percentage_rows(language_report))
    print()

    section("File Counts")
    print_count_table(
        [(entry.language.display_name, entry.count) for entry in language_report.statistics]
    )
    print()

    print(f"Detect completed in {format_duration(elapsed)}")
    return 0


# --- parse ----------------------------------------------------------------


def run_parse(path: str) -> int:
    start = time.perf_counter()

    try:
        progress("Scanning")
        snapshot = build_snapshot(path)
        progress("Detecting languages")
        language_report = build_language_report(snapshot)
        progress("Parsing")
        parsed_files = build_parsed_files(snapshot.root, language_report)
    except PipelineError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    elapsed = time.perf_counter() - start

    error_count = sum(
        1
        for parsed in parsed_files
        for diagnostic in parsed.result.diagnostics
        if diagnostic.severity == DiagnosticSeverity.ERROR
    )
    parser_stats: Counter[str] = Counter()
    parser_timing: dict[str, float] = {}
    for parsed in parsed_files:
        parser_stats[parsed.result.parser_id] += 1
        parser_timing[parsed.result.parser_id] = (
            parser_timing.get(parsed.result.parser_id, 0.0) + parsed.result.elapsed_seconds
        )

    section("Parsing")
    print(f"Files parsed: {format_count(len(parsed_files))}")
    print(f"Syntax errors: {format_count(error_count)}")
    print()

    section("Parser Statistics")
    if not parser_stats:
        print("(None)")
    else:
        for parser_id, count in sorted(parser_stats.items()):
            timing = trim(parser_timing[parser_id] * 1000)
            print(f"  {parser_id:<20}  {count:>8} files   {timing:>8} ms")
    print()

    print(f"Parse completed in {format_duration(elapsed)}")
    return 0


# --- ir ---------------------------------------------------------------------


def run_ir(path: str) -> int:
    start = time.perf_counter()

    try:
        progress("Scanning")
        snapshot = build_snapshot(path)
        progress("Detecting languages")
        language_report = build_language_report(snapshot)
        progress("Parsing")
        parsed_files = build_parsed_files(snapshot.root, language_report)
        progress("Building IR")
        repository = build_repository(snapshot.root, parsed_files)
    except PipelineError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    elapsed = time.perf_counter() - start
    declaration_counts = _declaration_counts(repository)

    section("Repository")
    print("Repositories: 1")
    print(f"Packages: {format_count(len(repository.packages))}")
    print(f"Files: {format_count(len(repository.files))}")
    print()

    section("Declarations")
    print_count_table(sorted(declaration_counts.items()))
    print()

    section("Diagnostics")
    print(f"Total: {format_count(len(repository.diagnostics))}")
    for diagnostic in repository.diagnostics:
        print(f"  [{diagnostic.severity.value}] {diagnostic.message}")
    print()

    print(f"IR build completed in {format_duration(elapsed)}")
    return 0


# --- symbols ----------------------------------------------------------------


def run_symbols(path: str, *, verbose: bool = False) -> int:
    start = time.perf_counter()

    try:
        progress("Scanning")
        snapshot = build_snapshot(path)
        progress("Detecting languages")
        language_report = build_language_report(snapshot)
        progress("Parsing")
        parsed_files = build_parsed_files(snapshot.root, language_report)
        progress("Building IR")
        repository = build_repository(snapshot.root, parsed_files)
        progress("Building Symbol Table")
        symbols = build_symbol_table(repository)
    except PipelineError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    elapsed = time.perf_counter() - start
    kind_counts: Counter[str] = Counter(symbol.kind.value for symbol in symbols.symbols())
    duplicate_diagnostics = [d for d in symbols.diagnostics() if "duplicate" in d.message]

    section("Symbols")
    print(f"Total: {format_count(len(symbols))}")
    print(f"Scopes: {format_count(len(symbols.scopes()))}")
    print()

    section("By Kind")
    print_count_table(sorted(kind_counts.items()))
    print()

    section("Duplicate Diagnostics")
    print(f"Total: {format_count(len(duplicate_diagnostics))}")
    for diagnostic in duplicate_diagnostics:
        print(f"  [{diagnostic.severity.value}] {diagnostic.message}")
    print()

    if verbose:
        section("Every Symbol")
        for symbol in symbols.symbols():
            print(f"  [{symbol.kind.value}] {symbol.name} (id={symbol.id})")
        print()

    print(f"Symbol build completed in {format_duration(elapsed)}")
    return 0


# --- references --------------------------------------------------------------


def run_references(path: str, *, verbose: bool = False) -> int:
    start = time.perf_counter()

    try:
        progress("Scanning")
        snapshot = build_snapshot(path)
        progress("Detecting languages")
        language_report = build_language_report(snapshot)
        progress("Parsing")
        parsed_files = build_parsed_files(snapshot.root, language_report)
        progress("Building IR")
        repository = build_repository(snapshot.root, parsed_files)
        progress("Building Symbol Table")
        symbols = build_symbol_table(repository)
        progress("Resolving References")
        references = build_reference_index(parsed_files, repository, symbols)
    except PipelineError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    elapsed = time.perf_counter() - start
    all_references = references.references()
    resolved = [r for r in all_references if isinstance(r, ResolvedReference)]
    unresolved = [r for r in all_references if isinstance(r, UnresolvedReference)]
    total = len(all_references)
    percentage = (len(resolved) / total * 100) if total else 0.0

    section("References")
    print(f"Total: {format_count(total)}")
    print(f"Resolved: {format_count(len(resolved))}")
    print(f"Unresolved: {format_count(len(unresolved))}")
    print(f"Resolution rate: {percentage:.1f}%")
    print()

    section("Diagnostics")
    print(f"Total: {format_count(len(references.diagnostics()))}")
    for diagnostic in references.diagnostics():
        print(f"  [{diagnostic.severity.value}] {diagnostic.message}")
    print()

    if verbose:
        section("Every Reference")
        for reference in all_references:
            status = "resolved" if isinstance(reference, ResolvedReference) else "unresolved"
            print(f"  [{status}] {reference.kind.value} {reference.identifier!r}")
        print()

    print(f"Reference resolution completed in {format_duration(elapsed)}")
    return 0


# --- types -------------------------------------------------------------------


def run_types(path: str, *, verbose: bool = False) -> int:
    start = time.perf_counter()

    try:
        progress("Scanning")
        snapshot = build_snapshot(path)
        progress("Detecting languages")
        language_report = build_language_report(snapshot)
        progress("Parsing")
        parsed_files = build_parsed_files(snapshot.root, language_report)
        progress("Building IR")
        repository = build_repository(snapshot.root, parsed_files)
        progress("Building Symbol Table")
        symbols = build_symbol_table(repository)
        progress("Building Type Index")
        type_index = build_type_index(repository, symbols)
    except PipelineError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    elapsed = time.perf_counter() - start
    stats = type_index.statistics()

    section("Types")
    print_count_table(
        [
            ("Structs", stats["structs"]),
            ("Interfaces", stats["interfaces"]),
            ("Aliases", stats["aliases"]),
            ("Named", stats["named_types"]),
            ("Total", stats["total_types"]),
        ]
    )
    print()

    section("Diagnostics")
    print(f"Total: {format_count(len(type_index.diagnostics()))}")
    for diagnostic in type_index.diagnostics():
        print(f"  [{diagnostic.severity.value}] {diagnostic.message}")
    print()

    if verbose:
        section("Every Type")
        for type_ in type_index.types():
            print(f"  [{type_.kind.value}] {type_.name} (package={type_.package})")
        print()

    print(f"Type build completed in {format_duration(elapsed)}")
    return 0


# --- graph -------------------------------------------------------------------


def run_graph(path: str, *, verbose: bool = False) -> int:
    start = time.perf_counter()

    try:
        progress("Scanning")
        snapshot = build_snapshot(path)
        progress("Detecting languages")
        language_report = build_language_report(snapshot)
        progress("Parsing")
        parsed_files = build_parsed_files(snapshot.root, language_report)
        progress("Building IR")
        repository = build_repository(snapshot.root, parsed_files)
        progress("Building Symbol Table")
        symbols = build_symbol_table(repository)
        progress("Resolving References")
        references = build_reference_index(parsed_files, repository, symbols)
        progress("Building Graph")
        graph = build_structural_graph(repository)
        graph = enrich_graph_with_references(references, symbols, graph)
        progress("Running Analyses")
        analysis_result = run_semantic_analyses(
            repository, symbols, references, graph, parsed_files
        )
        graph = analysis_result.graph
    except PipelineError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    elapsed = time.perf_counter() - start
    relationship_counts = Counter(edge.relationship.value for edge in graph.edges)

    section("Knowledge Graph")
    print(f"Nodes: {format_count(len(graph.nodes))}")
    print(f"Edges: {format_count(len(graph.edges))}")
    print()

    section("Relationships")
    print_count_table(sorted(relationship_counts.items()))
    print()

    if verbose:
        section("Nodes")
        for node in graph.nodes:
            print(f"  {node.id}  [{node.type}]  {node.properties.as_dict()}")
        print()

        section("Edges")
        for edge in graph.edges:
            print(f"  {edge.source} --{edge.relationship.value}--> {edge.target}")
        print()

    print(f"Graph build completed in {format_duration(elapsed)}")
    return 0


# --- analyze -----------------------------------------------------------------


def run_analyze(path: str) -> int:
    start = time.perf_counter()

    try:
        progress("Scanning")
        snapshot = build_snapshot(path)
        progress("Detecting languages")
        language_report = build_language_report(snapshot)
        progress("Parsing")
        parsed_files = build_parsed_files(snapshot.root, language_report)
        progress("Building IR")
        repository = build_repository(snapshot.root, parsed_files)
        progress("Building Symbol Table")
        symbols = build_symbol_table(repository)
        progress("Resolving References")
        references = build_reference_index(parsed_files, repository, symbols)
        progress("Building Type Index")
        type_index = build_type_index(repository, symbols)
        progress("Building Graph")
        graph = build_structural_graph(repository)
        graph = enrich_graph_with_references(references, symbols, graph)
        progress("Running Analyses")
        analysis_result = run_semantic_analyses(
            repository, symbols, references, graph, parsed_files
        )
        graph = analysis_result.graph
    except PipelineError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    done()
    print()

    elapsed = time.perf_counter() - start
    declaration_counts = _declaration_counts(repository)
    resolved_count = sum(1 for r in references.references() if isinstance(r, ResolvedReference))
    relationship_counts = Counter(edge.relationship.value for edge in graph.edges)

    section("Repository")
    print(f"Name: {snapshot.root.name}")
    print(f"Files: {format_count(len(repository.files))}")
    print(f"Packages: {format_count(len(repository.packages))}")
    print()

    section("Languages")
    print_percentage_table(_language_percentage_rows(language_report))
    print()

    section("IR")
    print_count_table(
        [
            ("Declarations", sum(declaration_counts.values())),
            ("Symbols", len(symbols)),
            ("References", len(references)),
            ("Resolved", resolved_count),
            ("Types", len(type_index)),
        ]
    )
    print()

    section("Knowledge Graph")
    print_count_table([("Nodes", len(graph.nodes)), ("Edges", len(graph.edges))])
    print()
    print("Relationships")
    print_count_table(sorted(relationship_counts.items()), indent="  ")
    print()

    section("Analysis")
    for label, result in (
        ("Call Graph", analysis_result.call_graph),
        ("Type Relationships", analysis_result.type_relationships),
        ("Dependency Analysis", analysis_result.dependencies),
    ):
        mark = "✓" if result.success else "✗"
        print(f"  {label:<22} {mark}")
    print()

    print(f"Completed in: {format_duration(elapsed)}")
    return 0


# --- stats -------------------------------------------------------------------


def run_stats(path: str) -> int:
    try:
        snapshot = build_snapshot(path)
        language_report = build_language_report(snapshot)
        parsed_files = build_parsed_files(snapshot.root, language_report)
        repository = build_repository(snapshot.root, parsed_files)
        symbols = build_symbol_table(repository)
        references = build_reference_index(parsed_files, repository, symbols)
        type_index = build_type_index(repository, symbols)
        graph = build_structural_graph(repository)
        graph = enrich_graph_with_references(references, symbols, graph)
        analysis_result = run_semantic_analyses(
            repository, symbols, references, graph, parsed_files
        )
    except PipelineError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    declaration_counts = _declaration_counts(repository)
    resolved_count = sum(1 for r in references.references() if isinstance(r, ResolvedReference))
    unresolved_count = len(references) - resolved_count
    type_stats = type_index.statistics()

    section("Repository Statistics")
    print_count_table(
        [
            ("Packages", len(repository.packages)),
            ("Files", len(repository.files)),
            ("Declarations", sum(declaration_counts.values())),
        ]
    )
    print()

    section("Declarations")
    print_count_table(sorted(declaration_counts.items()))
    print()

    section("Symbols")
    print_count_table([("Total", len(symbols))])
    print()

    section("References")
    print_count_table(
        [
            ("Total", len(references)),
            ("Resolved", resolved_count),
            ("Unresolved", unresolved_count),
        ]
    )
    print()

    section("Types")
    print_count_table(
        [
            ("Structs", type_stats["structs"]),
            ("Interfaces", type_stats["interfaces"]),
            ("Aliases", type_stats["aliases"]),
            ("Named", type_stats["named_types"]),
        ]
    )
    print()

    section("Semantic Analysis")
    print_count_table(
        [
            ("Call graph edges", len(analysis_result.call_graph.artifacts["call_graph"])),
            (
                "Type relationships",
                len(analysis_result.type_relationships.artifacts["type_relationships"]),
            ),
            ("Dependencies", len(analysis_result.dependencies.artifacts["dependencies"])),
        ]
    )
    return 0
