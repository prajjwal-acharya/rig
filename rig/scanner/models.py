from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class GitInfo:
    is_git_repository: bool
    git_dir: Path | None


@dataclass(frozen=True)
class RepositoryLocation:
    root: Path
    requested_path: Path
    git: GitInfo


@dataclass(frozen=True)
class FileMetadata:
    absolute_path: Path
    relative_path: Path
    extension: str
    size_bytes: int
    modified_at: datetime
    created_at: datetime | None
    checksum_sha256: str | None
    is_executable: bool
    is_symlink: bool
    is_hidden: bool


@dataclass(frozen=True)
class DirectoryMetadata:
    absolute_path: Path
    relative_path: Path
    is_symlink: bool
    is_hidden: bool


@dataclass(frozen=True)
class DiscoveredFile:
    relative_path: Path
    metadata: FileMetadata | None = None


@dataclass(frozen=True)
class DiscoveredDirectory:
    relative_path: Path
    metadata: DirectoryMetadata | None = None


@dataclass(frozen=True)
class FileWalkResult:
    root: Path
    directories: list[DiscoveredDirectory]
    files: list[DiscoveredFile]


@dataclass(frozen=True)
class RepositoryStatistics:
    files: int
    directories: int
    is_git_repository: bool


@dataclass(frozen=True)
class RepositorySnapshot:
    root: Path
    git: GitInfo
    files: list[DiscoveredFile]
    directories: list[DiscoveredDirectory]
    statistics: RepositoryStatistics
    metadata: Any | None = None


@dataclass(frozen=True)
class IgnoreConfig:
    use_gitignore: bool = True
    extra_patterns: tuple[str, ...] = ()
    ignore_hidden: bool = False


@dataclass(frozen=True)
class FilteredWalkResult:
    root: Path
    included_files: list[DiscoveredFile]
    included_directories: list[DiscoveredDirectory]
    excluded_files: list[DiscoveredFile]
    excluded_directories: list[DiscoveredDirectory]
