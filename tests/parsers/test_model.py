from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from rig.parsers.model import Diagnostic, DiagnosticSeverity, ParseContext, ParseResult
from tests.parsers.conftest import FAKE_LANGUAGE


def test_parse_context_is_immutable() -> None:
    context = ParseContext(path=Path("main.fake"), language=FAKE_LANGUAGE, source="content")

    with pytest.raises(dataclasses.FrozenInstanceError):
        context.source = "other"  # type: ignore[misc]


def test_parse_context_defaults_to_empty_config() -> None:
    context = ParseContext(path=Path("main.fake"), language=FAKE_LANGUAGE, source="content")

    assert context.config == {}


def test_parse_context_accepts_explicit_config() -> None:
    context = ParseContext(
        path=Path("main.fake"),
        language=FAKE_LANGUAGE,
        source="content",
        config={"strict": True},
    )

    assert context.config == {"strict": True}


def test_parse_result_is_immutable() -> None:
    result = ParseResult.ok(parser_id="fake-parser", language=FAKE_LANGUAGE)

    with pytest.raises(dataclasses.FrozenInstanceError):
        result.success = False  # type: ignore[misc]


def test_parse_result_ok_factory() -> None:
    result = ParseResult.ok(parser_id="fake-parser", language=FAKE_LANGUAGE)

    assert result.success is True
    assert result.parser_id == "fake-parser"
    assert result.language == FAKE_LANGUAGE
    assert result.diagnostics == ()
    assert result.syntax_tree is None


def test_parse_result_failed_factory_requires_diagnostics() -> None:
    diagnostic = Diagnostic("something went wrong")
    result = ParseResult.failed(
        parser_id="fake-parser", language=FAKE_LANGUAGE, diagnostics=(diagnostic,)
    )

    assert result.success is False
    assert result.diagnostics == (diagnostic,)


def test_diagnostic_defaults_to_error_severity() -> None:
    diagnostic = Diagnostic("oops")

    assert diagnostic.severity == DiagnosticSeverity.ERROR


def test_diagnostic_accepts_explicit_severity() -> None:
    diagnostic = Diagnostic("heads up", severity=DiagnosticSeverity.WARNING)

    assert diagnostic.severity == DiagnosticSeverity.WARNING


def test_parse_result_syntax_tree_is_none_by_default() -> None:
    result = ParseResult.ok(parser_id="fake-parser", language=FAKE_LANGUAGE)

    assert result.syntax_tree is None
