from __future__ import annotations

import hashlib
import os
import stat
from datetime import datetime, timezone
from pathlib import Path

import pytest

from rig.scanner.metadata import MetadataCollector
from rig.scanner.models import DiscoveredDirectory, DiscoveredFile


def test_collects_size_and_extension_for_text_file(tmp_path: Path) -> None:
    (tmp_path / "notes.txt").write_text("hello world")

    file = MetadataCollector(tmp_path).collect_file(DiscoveredFile(Path("notes.txt")))

    assert file.metadata is not None
    assert file.metadata.size_bytes == len(b"hello world")
    assert file.metadata.extension == ".txt"
    assert file.metadata.absolute_path == tmp_path / "notes.txt"
    assert file.metadata.is_hidden is False


def test_collects_metadata_for_empty_file(tmp_path: Path) -> None:
    (tmp_path / "empty.txt").touch()

    file = MetadataCollector(tmp_path).collect_file(DiscoveredFile(Path("empty.txt")))

    assert file.metadata is not None
    assert file.metadata.size_bytes == 0
    assert file.metadata.checksum_sha256 == hashlib.sha256(b"").hexdigest()


def test_collects_metadata_for_binary_file(tmp_path: Path) -> None:
    payload = bytes(range(256)) * 4
    (tmp_path / "data.bin").write_bytes(payload)

    file = MetadataCollector(tmp_path).collect_file(DiscoveredFile(Path("data.bin")))

    assert file.metadata is not None
    assert file.metadata.size_bytes == len(payload)
    assert file.metadata.checksum_sha256 == hashlib.sha256(payload).hexdigest()
    assert file.metadata.extension == ".bin"


def test_collects_metadata_for_large_file(tmp_path: Path) -> None:
    payload = b"x" * (3 * 1024 * 1024 + 17)  # exceeds the streaming chunk size
    (tmp_path / "large.dat").write_bytes(payload)

    file = MetadataCollector(tmp_path).collect_file(DiscoveredFile(Path("large.dat")))

    assert file.metadata is not None
    assert file.metadata.size_bytes == len(payload)
    assert file.metadata.checksum_sha256 == hashlib.sha256(payload).hexdigest()


def test_checksum_is_deterministic_across_calls(tmp_path: Path) -> None:
    (tmp_path / "repeat.txt").write_text("deterministic content")

    collector = MetadataCollector(tmp_path)
    first = collector.collect_file(DiscoveredFile(Path("repeat.txt")))
    second = collector.collect_file(DiscoveredFile(Path("repeat.txt")))

    assert first.metadata is not None
    assert second.metadata is not None
    assert first.metadata.checksum_sha256 == second.metadata.checksum_sha256


def test_checksum_differs_for_different_content(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("content a")
    (tmp_path / "b.txt").write_text("content b")

    collector = MetadataCollector(tmp_path)
    a = collector.collect_file(DiscoveredFile(Path("a.txt")))
    b = collector.collect_file(DiscoveredFile(Path("b.txt")))

    assert a.metadata is not None
    assert b.metadata is not None
    assert a.metadata.checksum_sha256 != b.metadata.checksum_sha256


@pytest.mark.skipif(os.name == "nt", reason="POSIX executable bits")
def test_detects_executable_file(tmp_path: Path) -> None:
    script = tmp_path / "run.sh"
    script.write_text("#!/bin/sh\necho hi\n")
    script.chmod(script.stat().st_mode | stat.S_IXUSR)

    file = MetadataCollector(tmp_path).collect_file(DiscoveredFile(Path("run.sh")))

    assert file.metadata is not None
    assert file.metadata.is_executable is True


def test_non_executable_file_is_not_flagged(tmp_path: Path) -> None:
    (tmp_path / "plain.txt").write_text("data")

    file = MetadataCollector(tmp_path).collect_file(DiscoveredFile(Path("plain.txt")))

    assert file.metadata is not None
    assert file.metadata.is_executable is False


@pytest.mark.skipif(os.name == "nt", reason="symlinks require elevated privileges on Windows")
def test_detects_symlink_and_skips_checksum(tmp_path: Path) -> None:
    target = tmp_path / "target.txt"
    target.write_text("target content")
    link = tmp_path / "link.txt"
    link.symlink_to(target)

    file = MetadataCollector(tmp_path).collect_file(DiscoveredFile(Path("link.txt")))

    assert file.metadata is not None
    assert file.metadata.is_symlink is True
    assert file.metadata.checksum_sha256 is None
    assert file.metadata.is_executable is False


@pytest.mark.skipif(os.name == "nt", reason="symlinks require elevated privileges on Windows")
def test_broken_symlink_does_not_raise(tmp_path: Path) -> None:
    link = tmp_path / "dangling.txt"
    link.symlink_to(tmp_path / "does-not-exist.txt")

    file = MetadataCollector(tmp_path).collect_file(DiscoveredFile(Path("dangling.txt")))

    assert file.metadata is not None
    assert file.metadata.is_symlink is True
    assert file.metadata.checksum_sha256 is None


def test_detects_hidden_file(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("SECRET=1")

    file = MetadataCollector(tmp_path).collect_file(DiscoveredFile(Path(".env")))

    assert file.metadata is not None
    assert file.metadata.is_hidden is True


def test_extension_is_empty_for_extensionless_file(tmp_path: Path) -> None:
    (tmp_path / "Makefile").write_text("all:\n\techo hi\n")

    file = MetadataCollector(tmp_path).collect_file(DiscoveredFile(Path("Makefile")))

    assert file.metadata is not None
    assert file.metadata.extension == ""


def test_modified_at_reflects_last_write(tmp_path: Path) -> None:
    target = tmp_path / "touched.txt"
    target.write_text("v1")
    timestamp = 1_700_000_000
    os.utime(target, (timestamp, timestamp))

    file = MetadataCollector(tmp_path).collect_file(DiscoveredFile(Path("touched.txt")))

    assert file.metadata is not None
    assert file.metadata.modified_at == datetime.fromtimestamp(timestamp, tz=timezone.utc)


def test_created_at_is_datetime_or_none_depending_on_platform(tmp_path: Path) -> None:
    (tmp_path / "new.txt").write_text("data")

    file = MetadataCollector(tmp_path).collect_file(DiscoveredFile(Path("new.txt")))

    assert file.metadata is not None
    assert file.metadata.created_at is None or isinstance(file.metadata.created_at, datetime)


def test_directory_metadata_has_no_file_only_fields(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()

    directory = MetadataCollector(tmp_path).collect_directory(DiscoveredDirectory(Path("src")))

    assert directory.metadata is not None
    assert directory.metadata.absolute_path == tmp_path / "src"
    assert directory.metadata.is_symlink is False
    assert directory.metadata.is_hidden is False
    assert not hasattr(directory.metadata, "checksum_sha256")


def test_hidden_directory_is_flagged(tmp_path: Path) -> None:
    (tmp_path / ".config").mkdir()

    directory = MetadataCollector(tmp_path).collect_directory(DiscoveredDirectory(Path(".config")))

    assert directory.metadata is not None
    assert directory.metadata.is_hidden is True
