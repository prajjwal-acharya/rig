from __future__ import annotations

from pathlib import Path

from rig.scanner.repository import scan_repository


def test_scan_git_repository(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('hi')")
    (tmp_path / "README.md").write_text("# repo")

    snapshot = scan_repository(tmp_path)

    assert snapshot.root == tmp_path.resolve()
    assert snapshot.git.is_git_repository is True
    assert {d.relative_path for d in snapshot.directories} == {
        Path(".git"),
        Path("src"),
    }
    assert {f.relative_path for f in snapshot.files} == {
        Path("README.md"),
        Path("src/main.py"),
    }


def test_scan_non_git_repository(tmp_path: Path) -> None:
    (tmp_path / "data.txt").write_text("data")

    snapshot = scan_repository(tmp_path)

    assert snapshot.git.is_git_repository is False
    assert {f.relative_path for f in snapshot.files} == {Path("data.txt")}


def test_scan_resolves_root_from_nested_path(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    nested = tmp_path / "src" / "pkg"
    nested.mkdir(parents=True)
    (nested / "module.py").write_text("x = 1")

    snapshot = scan_repository(nested)

    assert snapshot.root == tmp_path.resolve()
    assert {f.relative_path for f in snapshot.files} == {Path("src/pkg/module.py")}


def test_scan_statistics_reflect_discovered_entries(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('hi')")
    (tmp_path / "README.md").write_text("# repo")

    snapshot = scan_repository(tmp_path)

    assert snapshot.statistics.files == 2
    assert snapshot.statistics.directories == 2
    assert snapshot.statistics.is_git_repository is True


def test_scan_statistics_for_empty_non_git_repository(tmp_path: Path) -> None:
    snapshot = scan_repository(tmp_path)

    assert snapshot.statistics.files == 0
    assert snapshot.statistics.directories == 0
    assert snapshot.statistics.is_git_repository is False


def test_scan_metadata_slot_defaults_to_none(tmp_path: Path) -> None:
    snapshot = scan_repository(tmp_path)

    assert snapshot.metadata is None


def test_scan_populates_file_and_directory_metadata(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('hi')")

    snapshot = scan_repository(tmp_path)

    file_entry = next(f for f in snapshot.files if f.relative_path == Path("src/main.py"))
    directory_entry = next(d for d in snapshot.directories if d.relative_path == Path("src"))

    assert file_entry.metadata is not None
    assert file_entry.metadata.checksum_sha256 is not None
    assert directory_entry.metadata is not None


def test_scan_respects_gitignore(tmp_path: Path) -> None:
    (tmp_path / ".gitignore").write_text("*.log\n")
    (tmp_path / "app.log").write_text("log data")
    (tmp_path / "app.py").write_text("x = 1")

    snapshot = scan_repository(tmp_path)

    relative_paths = {f.relative_path for f in snapshot.files}
    assert Path("app.py") in relative_paths
    assert Path("app.log") not in relative_paths
