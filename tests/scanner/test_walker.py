from __future__ import annotations

from pathlib import Path

from rig.scanner.models import DiscoveredDirectory, DiscoveredFile
from rig.scanner.walker import walk_repository


def test_walk_empty_directory(tmp_path: Path) -> None:
    result = walk_repository(tmp_path)

    assert result.files == []
    assert result.directories == []


def test_walk_preserves_empty_subdirectories(tmp_path: Path) -> None:
    (tmp_path / "empty").mkdir()

    result = walk_repository(tmp_path)

    assert result.directories == [DiscoveredDirectory(Path("empty"))]
    assert result.files == []


def test_walk_nested_directories_and_files(tmp_path: Path) -> None:
    (tmp_path / "a" / "b").mkdir(parents=True)
    (tmp_path / "a" / "file_a.txt").write_text("a")
    (tmp_path / "a" / "b" / "file_b.txt").write_text("b")
    (tmp_path / "top.txt").write_text("top")

    result = walk_repository(tmp_path)

    assert result.directories == [
        DiscoveredDirectory(Path("a")),
        DiscoveredDirectory(Path("a/b")),
    ]
    assert result.files == [
        DiscoveredFile(Path("a/b/file_b.txt")),
        DiscoveredFile(Path("a/file_a.txt")),
        DiscoveredFile(Path("top.txt")),
    ]


def test_walk_produces_relative_paths(tmp_path: Path) -> None:
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "nested.txt").write_text("data")

    result = walk_repository(tmp_path)

    for directory in result.directories:
        assert not directory.relative_path.is_absolute()
    for file in result.files:
        assert not file.relative_path.is_absolute()


def test_walk_is_deterministic_regardless_of_creation_order(tmp_path: Path) -> None:
    (tmp_path / "zeta.txt").write_text("z")
    (tmp_path / "alpha.txt").write_text("a")
    (tmp_path / "mid").mkdir()
    (tmp_path / "mid" / "beta.txt").write_text("b")

    first = walk_repository(tmp_path)
    second = walk_repository(tmp_path)

    assert first.files == second.files
    assert first.directories == second.directories
    assert first.files == [
        DiscoveredFile(Path("alpha.txt")),
        DiscoveredFile(Path("mid/beta.txt")),
        DiscoveredFile(Path("zeta.txt")),
    ]


def test_walk_does_not_follow_symlinked_directories(tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    (real / "inside.txt").write_text("data")
    (tmp_path / "link").symlink_to(real)

    result = walk_repository(tmp_path)

    assert DiscoveredDirectory(Path("link")) in result.directories
    assert DiscoveredFile(Path("link/inside.txt")) not in result.files
    assert result.files == [DiscoveredFile(Path("real/inside.txt"))]


def test_walk_large_flat_directory_scales(tmp_path: Path) -> None:
    for i in range(500):
        (tmp_path / f"file_{i:04d}.txt").write_text(str(i))

    result = walk_repository(tmp_path)

    assert len(result.files) == 500
    assert result.files == sorted(result.files, key=lambda f: f.relative_path.as_posix())
