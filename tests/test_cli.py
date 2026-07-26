from __future__ import annotations

from pathlib import Path

import pytest

from rig.cli import main


def _write(path: Path, content: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def test_scan_reports_files_and_directories(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write(tmp_path / "src" / "main.py", "print('hi')")
    _write(tmp_path / "README.md", "# repo")

    exit_code = main(["scan", str(tmp_path)])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert f"Repository: {tmp_path.resolve()}" in output
    assert "Git Repository: No" in output
    assert "Files: 2" in output
    assert "Directories: 1" in output
    assert "Scan completed in" in output


def test_scan_detects_git_repository(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / ".git").mkdir()

    main(["scan", str(tmp_path)])
    output = capsys.readouterr().out

    assert "Git Repository: Yes" in output


def test_scan_lists_top_level_ignored_entries(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write(tmp_path / ".gitignore", "*.log\nbuild/\n")
    _write(tmp_path / "app.log", "log")
    _write(tmp_path / "build" / "nested" / "output.bin", "binary")
    _write(tmp_path / "keep.py", "x = 1")

    main(["scan", str(tmp_path)])
    output = capsys.readouterr().out

    ignored_section = output.split("Ignored:")[1].split("Languages:")[0]
    assert "app.log" in ignored_section
    assert "build/" in ignored_section
    assert "build/nested" not in ignored_section
    assert "keep.py" not in ignored_section


def test_scan_shows_none_when_nothing_ignored(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write(tmp_path / "plain.py", "x = 1")

    main(["scan", str(tmp_path)])
    output = capsys.readouterr().out

    ignored_section = output.split("Ignored:")[1].split("Languages:")[0]
    assert "(None)" in ignored_section


def test_scan_shows_none_for_languages_and_plugins_when_empty(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["scan", str(tmp_path)])
    output = capsys.readouterr().out

    assert "Languages:\n  (None)" in output
    assert "Plugins:\n  (None)" in output


def test_scan_reports_language_statistics(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write(tmp_path / "main.py", "print('hi')")
    _write(tmp_path / "other.py", "print('bye')")
    _write(tmp_path / "README.md", "# repo")
    _write(tmp_path / "LICENSE", "license text")

    main(["scan", str(tmp_path)])
    output = capsys.readouterr().out

    languages_section = output.split("Languages:")[1].split("Plugins:")[0]
    assert "Python" in languages_section
    assert "Markdown" in languages_section
    assert "Unknown" in languages_section
    python_line_index = languages_section.index("Python")
    markdown_line_index = languages_section.index("Markdown")
    assert python_line_index < markdown_line_index  # Python (2) before Markdown (1)


def test_scan_verbose_shows_per_file_metadata(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write(tmp_path / "notes.txt", "hello world")

    main(["scan", str(tmp_path), "--verbose"])
    output = capsys.readouterr().out

    assert "notes.txt" in output
    assert "Size:" in output
    assert "SHA256:" in output
    assert "Modified:" in output
    assert "Hidden: No" in output
    assert "Language: Text" in output


def test_scan_without_verbose_omits_per_file_metadata(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write(tmp_path / "notes.txt", "hello world")

    main(["scan", str(tmp_path)])
    output = capsys.readouterr().out

    assert "SHA256:" not in output


def test_scan_missing_path_reports_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    missing = tmp_path / "does-not-exist"

    exit_code = main(["scan", str(missing)])
    output = capsys.readouterr()

    assert exit_code == 1
    assert "error:" in output.err


def test_scan_file_path_reports_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    file_path = tmp_path / "file.txt"
    file_path.write_text("data")

    exit_code = main(["scan", str(file_path)])
    output = capsys.readouterr()

    assert exit_code == 1
    assert "error:" in output.err


def test_scan_defaults_to_current_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _write(tmp_path / "file.txt", "data")
    monkeypatch.chdir(tmp_path)

    exit_code = main(["scan"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert f"Repository: {tmp_path.resolve()}" in output
