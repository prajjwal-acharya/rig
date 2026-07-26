from __future__ import annotations

from pathlib import Path

from rig.languages import DEFAULT_REGISTRY
from rig.languages.model import Language
from rig.languages.pipeline import LanguageAnnotatedFile
from rig.parsers.manager import ParserManager
from rig.parsers.pipeline import parse_repository_files
from rig.parsers.stubs import build_stub_registry
from rig.scanner.models import DiscoveredFile
from tests.parsers.conftest import OTHER_LANGUAGE


def _require_language(extension: str) -> Language:
    language = DEFAULT_REGISTRY.lookup_extension(extension)
    if language is None:
        raise RuntimeError(f"{extension!r} is missing from the default language catalog")
    return language


GO_LANGUAGE = _require_language(".go")
PYTHON_LANGUAGE = _require_language(".py")


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def test_parses_supported_files_end_to_end(tmp_path: Path) -> None:
    _write(tmp_path / "main.go", "package main")
    manager = ParserManager(build_stub_registry())

    annotated = [
        LanguageAnnotatedFile(
            file=DiscoveredFile(relative_path=Path("main.go")), language=GO_LANGUAGE
        )
    ]

    parsed = parse_repository_files(tmp_path, annotated, manager)

    assert len(parsed) == 1
    assert parsed[0].result.success is True
    assert parsed[0].result.parser_id == "stub-go"


def test_skips_files_with_no_registered_parser(tmp_path: Path) -> None:
    _write(tmp_path / "notes.txt", "hello")
    manager = ParserManager(build_stub_registry())

    annotated = [
        LanguageAnnotatedFile(
            file=DiscoveredFile(relative_path=Path("notes.txt")), language=OTHER_LANGUAGE
        )
    ]

    parsed = parse_repository_files(tmp_path, annotated, manager)

    assert parsed == ()


def test_handles_unreadable_file_without_raising(tmp_path: Path) -> None:
    manager = ParserManager(build_stub_registry())

    annotated = [
        LanguageAnnotatedFile(
            file=DiscoveredFile(relative_path=Path("missing.go")), language=GO_LANGUAGE
        )
    ]

    parsed = parse_repository_files(tmp_path, annotated, manager)

    assert len(parsed) == 1
    assert parsed[0].result.success is False


def test_empty_input_produces_empty_output(tmp_path: Path) -> None:
    manager = ParserManager(build_stub_registry())

    assert parse_repository_files(tmp_path, [], manager) == ()


def test_parses_multiple_languages_in_one_pass(tmp_path: Path) -> None:
    _write(tmp_path / "main.go", "package main")
    _write(tmp_path / "app.py", "print('hi')")
    manager = ParserManager(build_stub_registry())

    annotated = [
        LanguageAnnotatedFile(
            file=DiscoveredFile(relative_path=Path("main.go")), language=GO_LANGUAGE
        ),
        LanguageAnnotatedFile(
            file=DiscoveredFile(relative_path=Path("app.py")), language=PYTHON_LANGUAGE
        ),
    ]

    parsed = parse_repository_files(tmp_path, annotated, manager)

    parser_ids = {entry.result.parser_id for entry in parsed}
    assert parser_ids == {"stub-go", "stub-python"}
