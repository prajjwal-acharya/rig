from __future__ import annotations

from pathlib import Path

from rig.scanner.ignore import IgnoreEngine, filter_repository
from rig.scanner.models import IgnoreConfig
from rig.scanner.walker import walk_repository


def _write(path: Path, content: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def test_gitignore_excludes_matching_files(tmp_path: Path) -> None:
    _write(tmp_path / ".gitignore", "*.log\n")
    _write(tmp_path / "app.log", "log data")
    _write(tmp_path / "app.py", "print('hi')")

    result = filter_repository(walk_repository(tmp_path), tmp_path)

    assert Path("app.py") in [f.relative_path for f in result.included_files]
    assert Path("app.log") in [f.relative_path for f in result.excluded_files]


def test_gitignore_directory_pattern_excludes_entire_subtree(tmp_path: Path) -> None:
    _write(tmp_path / ".gitignore", "build/\n")
    _write(tmp_path / "build" / "output.bin", "binary")
    _write(tmp_path / "build" / "nested" / "deep.txt", "deep")
    _write(tmp_path / "src" / "main.py", "x = 1")

    result = filter_repository(walk_repository(tmp_path), tmp_path)

    excluded_files = {f.relative_path for f in result.excluded_files}
    excluded_dirs = {d.relative_path for d in result.excluded_directories}
    included_files = {f.relative_path for f in result.included_files}

    assert Path("build") in excluded_dirs
    assert Path("build/nested") in excluded_dirs
    assert Path("build/output.bin") in excluded_files
    assert Path("build/nested/deep.txt") in excluded_files
    assert Path("src/main.py") in included_files


def test_nested_gitignore_overrides_root_gitignore(tmp_path: Path) -> None:
    _write(tmp_path / ".gitignore", "*.log\n")
    _write(tmp_path / "logs" / ".gitignore", "!important.log\n")
    _write(tmp_path / "logs" / "important.log", "keep me")
    _write(tmp_path / "logs" / "other.log", "drop me")

    result = filter_repository(walk_repository(tmp_path), tmp_path)

    included_files = {f.relative_path for f in result.included_files}
    excluded_files = {f.relative_path for f in result.excluded_files}

    assert Path("logs/important.log") in included_files
    assert Path("logs/other.log") in excluded_files


def test_nested_gitignore_is_scoped_to_its_own_directory(tmp_path: Path) -> None:
    _write(tmp_path / "a" / ".gitignore", "secret.txt\n")
    _write(tmp_path / "a" / "secret.txt", "a secret")
    _write(tmp_path / "b" / "secret.txt", "not a secret here")

    result = filter_repository(walk_repository(tmp_path), tmp_path)

    included_files = {f.relative_path for f in result.included_files}
    excluded_files = {f.relative_path for f in result.excluded_files}

    assert Path("a/secret.txt") in excluded_files
    assert Path("b/secret.txt") in included_files


def test_configurable_extra_patterns(tmp_path: Path) -> None:
    _write(tmp_path / "data.tmp", "temp")
    _write(tmp_path / "data.keep", "keep")

    config = IgnoreConfig(use_gitignore=False, extra_patterns=("*.tmp",))
    result = filter_repository(walk_repository(tmp_path), tmp_path, config)

    included_files = {f.relative_path for f in result.included_files}
    excluded_files = {f.relative_path for f in result.excluded_files}

    assert Path("data.keep") in included_files
    assert Path("data.tmp") in excluded_files


def test_use_gitignore_false_disables_gitignore_parsing(tmp_path: Path) -> None:
    _write(tmp_path / ".gitignore", "*.log\n")
    _write(tmp_path / "app.log", "log data")

    config = IgnoreConfig(use_gitignore=False)
    result = filter_repository(walk_repository(tmp_path), tmp_path, config)

    included_files = {f.relative_path for f in result.included_files}
    assert Path("app.log") in included_files


def test_ignore_hidden_excludes_dot_directories_when_enabled(tmp_path: Path) -> None:
    _write(tmp_path / ".venv" / "lib.py", "x = 1")
    _write(tmp_path / "src" / "main.py", "x = 1")

    config = IgnoreConfig(ignore_hidden=True)
    result = filter_repository(walk_repository(tmp_path), tmp_path, config)

    excluded_files = {f.relative_path for f in result.excluded_files}
    included_files = {f.relative_path for f in result.included_files}

    assert Path(".venv/lib.py") in excluded_files
    assert Path("src/main.py") in included_files


def test_ignore_hidden_disabled_by_default(tmp_path: Path) -> None:
    _write(tmp_path / ".venv" / "lib.py", "x = 1")

    result = filter_repository(walk_repository(tmp_path), tmp_path)

    included_files = {f.relative_path for f in result.included_files}
    assert Path(".venv/lib.py") in included_files


def test_included_files_have_no_overlap_with_excluded(tmp_path: Path) -> None:
    _write(tmp_path / ".gitignore", "*.log\n")
    _write(tmp_path / "keep.py", "x = 1")
    _write(tmp_path / "drop.log", "log")

    result = filter_repository(walk_repository(tmp_path), tmp_path)

    included = {f.relative_path for f in result.included_files}
    excluded = {f.relative_path for f in result.excluded_files}
    assert included.isdisjoint(excluded)


def test_filter_is_deterministic_across_runs(tmp_path: Path) -> None:
    _write(tmp_path / ".gitignore", "*.log\n*.tmp\n")
    _write(tmp_path / "a.log", "a")
    _write(tmp_path / "b.tmp", "b")
    _write(tmp_path / "c.py", "c")

    engine = IgnoreEngine(tmp_path)
    walk_result = walk_repository(tmp_path)

    first = engine.filter(walk_result)
    second = engine.filter(walk_result)

    assert first.included_files == second.included_files
    assert first.excluded_files == second.excluded_files
    assert first.included_directories == second.included_directories
    assert first.excluded_directories == second.excluded_directories


def test_gitignore_comments_and_blank_lines_are_ignored(tmp_path: Path) -> None:
    _write(tmp_path / ".gitignore", "# comment\n\n*.log\n")
    _write(tmp_path / "app.log", "log")
    _write(tmp_path / "app.py", "x = 1")

    result = filter_repository(walk_repository(tmp_path), tmp_path)

    included_files = {f.relative_path for f in result.included_files}
    excluded_files = {f.relative_path for f in result.excluded_files}

    assert Path("app.py") in included_files
    assert Path("app.log") in excluded_files
