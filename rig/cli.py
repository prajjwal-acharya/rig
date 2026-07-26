from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Sequence

from rig.languages import RepositoryLanguageReport, detect_repository_languages
from rig.plugins import PluginCache, PluginContext, PluginLogger, PluginManager
from rig.scanner import (
    FilteredWalkResult,
    IgnoreEngine,
    MetadataCollector,
    RepositoryPathNotADirectoryError,
    RepositoryPathNotFoundError,
    RepositorySnapshot,
    RepositoryStatistics,
    locate_repository,
    walk_repository,
)


def _format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    size_kb = size_bytes / 1024
    if size_kb < 1024:
        return f"{_trim(size_kb)} KB"
    return f"{_trim(size_kb / 1024)} MB"


def _trim(value: float) -> str:
    text = f"{value:.1f}"
    return text.removesuffix(".0")


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


def _build_snapshot(path: str) -> tuple[RepositorySnapshot, FilteredWalkResult]:
    location = locate_repository(path)
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
            print(f"  Size: {_format_size(metadata.size_bytes)}")
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


def run_scan(path: str, *, verbose: bool = False) -> int:
    start = time.perf_counter()

    try:
        snapshot, filtered = _build_snapshot(path)
    except (RepositoryPathNotFoundError, RepositoryPathNotADirectoryError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    language_report = detect_repository_languages(snapshot.files)

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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rig", description="Repository Intelligence Graph CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser("scan", help="Scan a repository")
    scan_parser.add_argument("path", nargs="?", default=".", help="Path to the repository")
    scan_parser.add_argument("--verbose", "-v", action="store_true", help="Show per-file metadata")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "scan":
        return run_scan(args.path, verbose=args.verbose)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
