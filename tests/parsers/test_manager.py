from __future__ import annotations

from pathlib import Path

from rig.languages.model import Language
from rig.parsers.manager import ParserManager
from rig.parsers.model import ParseContext
from rig.parsers.registry import ParserRegistry
from tests.parsers.conftest import FAKE_LANGUAGE, OTHER_LANGUAGE, FailingParser, FakeParser


def _context(language: Language = FAKE_LANGUAGE, source: str = "content") -> ParseContext:
    return ParseContext(path=Path("main.fake"), language=language, source=source)


def test_dispatches_to_registered_parser() -> None:
    parser = FakeParser()
    manager = ParserManager(ParserRegistry([parser]))

    result = manager.parse(_context())

    assert result.success is True
    assert result.parser_id == "fake-parser"
    assert len(parser.calls) == 1
    assert parser.calls[0].source == "content"


def test_unsupported_language_returns_failed_result_without_raising() -> None:
    manager = ParserManager(ParserRegistry())

    result = manager.parse(_context(language=OTHER_LANGUAGE))

    assert result.success is False
    assert result.diagnostics
    assert "no parser registered" in result.diagnostics[0].message


def test_parser_exception_is_isolated_and_reported_as_failure() -> None:
    manager = ParserManager(ParserRegistry([FailingParser()]))

    result = manager.parse(_context())

    assert result.success is False
    assert "boom during parse" in result.diagnostics[0].message
    assert result.parser_id == "failing-parser"


def test_elapsed_seconds_is_populated_on_success() -> None:
    manager = ParserManager(ParserRegistry([FakeParser()]))

    result = manager.parse(_context())

    assert result.elapsed_seconds >= 0.0


def test_elapsed_seconds_is_populated_on_parser_failure() -> None:
    manager = ParserManager(ParserRegistry([FailingParser()]))

    result = manager.parse(_context())

    assert result.elapsed_seconds >= 0.0


def test_supports_reflects_registry_contents() -> None:
    manager = ParserManager(ParserRegistry([FakeParser()]))

    assert manager.supports(FAKE_LANGUAGE) is True
    assert manager.supports(OTHER_LANGUAGE) is False


def test_manager_is_testable_without_any_real_parser() -> None:
    # An empty registry is a perfectly valid manager configuration -
    # dispatch degrades to explicit failure results, never an exception.
    manager = ParserManager(ParserRegistry())

    result = manager.parse(_context())

    assert result.success is False
