from __future__ import annotations

from pathlib import Path

import pathspec

from rig.scanner.models import (
    DiscoveredDirectory,
    DiscoveredFile,
    FileWalkResult,
    FilteredWalkResult,
    IgnoreConfig,
)

GITIGNORE_FILENAME = ".gitignore"


class _CompiledIgnoreFile:
    def __init__(self, lines: list[str]) -> None:
        stripped = [line.removeprefix("!") for line in lines]
        self._full_spec = pathspec.GitIgnoreSpec.from_lines(lines)
        self._touch_spec = pathspec.PathSpec.from_lines("gitignore", stripped)

    def decide(self, match_path: str) -> bool | None:
        # A directory's gitignore only overrides its ancestors for paths it
        # actually mentions; otherwise the decision falls through to the parent.
        if not self._touch_spec.match_file(match_path):
            return None
        return self._full_spec.match_file(match_path)


def _ancestor_directories(start: Path) -> list[Path]:
    return [start, *start.parents]


def _match_path(relative_path: Path, base: Path, *, is_dir: bool) -> str:
    rel = relative_path if base == Path() else relative_path.relative_to(base)
    text = rel.as_posix()
    return f"{text}/" if is_dir else text


class IgnoreEngine:
    def __init__(self, root: Path | str, config: IgnoreConfig | None = None) -> None:
        self._root = Path(root)
        self._config = config or IgnoreConfig()
        self._gitignore_files: dict[Path, _CompiledIgnoreFile] = {}
        self._extra_ignore: _CompiledIgnoreFile | None = (
            _CompiledIgnoreFile(list(self._config.extra_patterns))
            if self._config.extra_patterns
            else None
        )

    def load(self, walk_result: FileWalkResult) -> None:
        if not self._config.use_gitignore:
            return

        for file in walk_result.files:
            if file.relative_path.name != GITIGNORE_FILENAME:
                continue

            gitignore_path = self._root / file.relative_path
            content = gitignore_path.read_text(encoding="utf-8", errors="ignore")
            directory = file.relative_path.parent
            self._gitignore_files[directory] = _CompiledIgnoreFile(content.splitlines())

    def is_ignored(self, relative_path: Path, *, is_dir: bool) -> bool:
        for directory in _ancestor_directories(relative_path.parent):
            compiled = self._gitignore_files.get(directory)
            if compiled is None:
                continue

            match_path = _match_path(relative_path, directory, is_dir=is_dir)
            decision = compiled.decide(match_path)
            if decision is not None:
                return decision

        if self._extra_ignore is not None:
            match_path = _match_path(relative_path, Path(), is_dir=is_dir)
            decision = self._extra_ignore.decide(match_path)
            if decision is not None:
                return decision

        return self._config.ignore_hidden and any(
            part.startswith(".") for part in relative_path.parts
        )

    def filter(self, walk_result: FileWalkResult) -> FilteredWalkResult:
        self.load(walk_result)

        ignored_prefixes: list[str] = []
        included_directories: list[DiscoveredDirectory] = []
        excluded_directories: list[DiscoveredDirectory] = []
        included_files: list[DiscoveredFile] = []
        excluded_files: list[DiscoveredFile] = []

        for directory in walk_result.directories:
            rel_posix = directory.relative_path.as_posix()
            if any(rel_posix.startswith(prefix) for prefix in ignored_prefixes):
                excluded_directories.append(directory)
                continue

            if self.is_ignored(directory.relative_path, is_dir=True):
                excluded_directories.append(directory)
                ignored_prefixes.append(f"{rel_posix}/")
            else:
                included_directories.append(directory)

        for file in walk_result.files:
            rel_posix = file.relative_path.as_posix()
            if any(rel_posix.startswith(prefix) for prefix in ignored_prefixes):
                excluded_files.append(file)
                continue

            if self.is_ignored(file.relative_path, is_dir=False):
                excluded_files.append(file)
            else:
                included_files.append(file)

        return FilteredWalkResult(
            root=walk_result.root,
            included_files=included_files,
            included_directories=included_directories,
            excluded_files=excluded_files,
            excluded_directories=excluded_directories,
        )


def filter_repository(
    walk_result: FileWalkResult,
    root: Path | str,
    config: IgnoreConfig | None = None,
) -> FilteredWalkResult:
    return IgnoreEngine(root, config).filter(walk_result)
