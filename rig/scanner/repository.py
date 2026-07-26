from __future__ import annotations

from pathlib import Path

from rig.scanner.ignore import IgnoreEngine
from rig.scanner.locator import GitRepositoryLocator, RepositoryLocator
from rig.scanner.metadata import MetadataCollector
from rig.scanner.models import IgnoreConfig, RepositorySnapshot, RepositoryStatistics
from rig.scanner.walker import FileWalker


def scan_repository(
    path: Path | str,
    locator: RepositoryLocator | None = None,
    walker: FileWalker | None = None,
    ignore_engine: IgnoreEngine | None = None,
    ignore_config: IgnoreConfig | None = None,
    metadata_collector: MetadataCollector | None = None,
) -> RepositorySnapshot:
    locator = locator or GitRepositoryLocator()
    walker = walker or FileWalker()

    location = locator.locate(path)
    walk_result = walker.walk(location.root)

    ignore_engine = ignore_engine or IgnoreEngine(location.root, ignore_config)
    filtered = ignore_engine.filter(walk_result)

    metadata_collector = metadata_collector or MetadataCollector(location.root)
    enriched = metadata_collector.collect(filtered)

    statistics = RepositoryStatistics(
        files=len(enriched.included_files),
        directories=len(enriched.included_directories),
        is_git_repository=location.git.is_git_repository,
    )

    return RepositorySnapshot(
        root=location.root,
        git=location.git,
        files=enriched.included_files,
        directories=enriched.included_directories,
        statistics=statistics,
    )
