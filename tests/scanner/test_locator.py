from __future__ import annotations

from pathlib import Path

import pytest

from rig.scanner.errors import RepositoryPathNotADirectoryError, RepositoryPathNotFoundError
from rig.scanner.locator import locate_repository


def test_locate_non_git_directory(tmp_path: Path) -> None:
    location = locate_repository(tmp_path)

    assert location.root == tmp_path.resolve()
    assert location.git.is_git_repository is False
    assert location.git.git_dir is None


def test_locate_git_directory(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()

    location = locate_repository(tmp_path)

    assert location.root == tmp_path.resolve()
    assert location.git.is_git_repository is True
    assert location.git.git_dir == tmp_path.resolve() / ".git"


def test_locate_from_nested_subdirectory_finds_repo_root(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    nested = tmp_path / "src" / "pkg"
    nested.mkdir(parents=True)

    location = locate_repository(nested)

    assert location.root == tmp_path.resolve()
    assert location.requested_path == nested.resolve()
    assert location.git.is_git_repository is True


def test_locate_detects_worktree_style_git_file(tmp_path: Path) -> None:
    git_file = tmp_path / ".git"
    git_file.write_text("gitdir: /some/other/path\n")

    location = locate_repository(tmp_path)

    assert location.git.is_git_repository is True
    assert location.git.git_dir == git_file.resolve()


def test_locate_resolves_relative_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "repo").mkdir()
    monkeypatch.chdir(tmp_path)

    location = locate_repository("repo")

    assert location.root == (tmp_path / "repo").resolve()


def test_locate_resolves_symlinks(tmp_path: Path) -> None:
    real_dir = tmp_path / "real"
    real_dir.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real_dir)

    location = locate_repository(link)

    assert location.root == real_dir.resolve()
    assert location.requested_path == real_dir.resolve()


def test_locate_missing_path_raises(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"

    with pytest.raises(RepositoryPathNotFoundError):
        locate_repository(missing)


def test_locate_file_path_raises(tmp_path: Path) -> None:
    file_path = tmp_path / "file.txt"
    file_path.write_text("not a directory")

    with pytest.raises(RepositoryPathNotADirectoryError):
        locate_repository(file_path)
