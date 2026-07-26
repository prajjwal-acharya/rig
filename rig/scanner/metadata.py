from __future__ import annotations

import hashlib
import stat as stat_module
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from rig.scanner.models import (
    DirectoryMetadata,
    DiscoveredDirectory,
    DiscoveredFile,
    FileMetadata,
    FilteredWalkResult,
)

_CHECKSUM_CHUNK_SIZE = 1024 * 1024
_EXECUTABLE_BITS = stat_module.S_IXUSR | stat_module.S_IXGRP | stat_module.S_IXOTH


def _to_datetime(timestamp: float) -> datetime:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


def _compute_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(_CHECKSUM_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


class MetadataCollector:
    def __init__(self, root: Path | str) -> None:
        self._root = Path(root)

    def collect_file(self, file: DiscoveredFile) -> DiscoveredFile:
        absolute_path = self._root / file.relative_path
        # lstat, never stat: metadata describes the entry itself, and never
        # follows a symlink to read or hash whatever it happens to point at.
        stat_result = absolute_path.lstat()
        is_symlink = stat_module.S_ISLNK(stat_result.st_mode)
        created_at_ts = getattr(stat_result, "st_birthtime", None)

        metadata = FileMetadata(
            absolute_path=absolute_path,
            relative_path=file.relative_path,
            extension=file.relative_path.suffix,
            size_bytes=stat_result.st_size,
            modified_at=_to_datetime(stat_result.st_mtime),
            created_at=_to_datetime(created_at_ts) if created_at_ts is not None else None,
            checksum_sha256=None if is_symlink else _compute_sha256(absolute_path),
            is_executable=not is_symlink and bool(stat_result.st_mode & _EXECUTABLE_BITS),
            is_symlink=is_symlink,
            is_hidden=file.relative_path.name.startswith("."),
        )
        return replace(file, metadata=metadata)

    def collect_directory(self, directory: DiscoveredDirectory) -> DiscoveredDirectory:
        absolute_path = self._root / directory.relative_path
        stat_result = absolute_path.lstat()
        is_symlink = stat_module.S_ISLNK(stat_result.st_mode)

        metadata = DirectoryMetadata(
            absolute_path=absolute_path,
            relative_path=directory.relative_path,
            is_symlink=is_symlink,
            is_hidden=directory.relative_path.name.startswith("."),
        )
        return replace(directory, metadata=metadata)

    def collect(self, filtered: FilteredWalkResult) -> FilteredWalkResult:
        return replace(
            filtered,
            included_files=[self.collect_file(f) for f in filtered.included_files],
            included_directories=[self.collect_directory(d) for d in filtered.included_directories],
        )


def collect_metadata(filtered: FilteredWalkResult, root: Path | str) -> FilteredWalkResult:
    return MetadataCollector(root).collect(filtered)
