from __future__ import annotations

from pathlib import Path
from typing import Protocol

from rig.scanner.errors import RepositoryPathNotADirectoryError, RepositoryPathNotFoundError
from rig.scanner.models import GitInfo, RepositoryLocation


def _resolve_requested_path(path: Path | str) -> Path:
    candidate = Path(path).expanduser()
    if not candidate.exists():
        raise RepositoryPathNotFoundError(f"Path does not exist: {candidate}")

    resolved = candidate.resolve()
    if not resolved.is_dir():
        raise RepositoryPathNotADirectoryError(f"Path is not a directory: {resolved}")

    return resolved


def _find_git_dir(start: Path) -> Path | None:
    for candidate in (start, *start.parents):
        git_path = candidate / ".git"
        if git_path.exists():
            return git_path
    return None


class RepositoryLocator(Protocol):
    def locate(self, path: Path | str) -> RepositoryLocation: ...


class GitRepositoryLocator:
    def locate(self, path: Path | str) -> RepositoryLocation:
        resolved = _resolve_requested_path(path)
        git_dir = _find_git_dir(resolved)

        if git_dir is not None:
            return RepositoryLocation(
                root=git_dir.parent,
                requested_path=resolved,
                git=GitInfo(is_git_repository=True, git_dir=git_dir),
            )

        return RepositoryLocation(
            root=resolved,
            requested_path=resolved,
            git=GitInfo(is_git_repository=False, git_dir=None),
        )


def locate_repository(path: Path | str) -> RepositoryLocation:
    return GitRepositoryLocator().locate(path)
