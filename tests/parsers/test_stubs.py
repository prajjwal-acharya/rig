from __future__ import annotations

from pathlib import Path

from rig.languages import DEFAULT_REGISTRY
from rig.parsers.manager import ParserManager
from rig.parsers.model import ParseContext
from rig.parsers.stubs import GoParserStub, PythonParserStub, build_stub_registry


def test_go_stub_reports_go_language() -> None:
    stub = GoParserStub()

    assert stub.language == DEFAULT_REGISTRY.lookup_extension(".go")
    assert stub.parser_id == "stub-go"
    assert stub.parser_version == "0.1.0"


def test_python_stub_reports_python_language() -> None:
    stub = PythonParserStub()

    assert stub.language == DEFAULT_REGISTRY.lookup_extension(".py")
    assert stub.parser_id == "stub-python"


def test_go_stub_parse_succeeds_with_no_syntax_tree() -> None:
    stub = GoParserStub()
    context = ParseContext(path=Path("main.go"), language=stub.language, source="package main")

    result = stub.parse(context)

    assert result.success is True
    assert result.parser_id == "stub-go"
    assert result.syntax_tree is None
    assert result.diagnostics == ()


def test_python_stub_parse_succeeds_with_no_syntax_tree() -> None:
    stub = PythonParserStub()
    context = ParseContext(path=Path("main.py"), language=stub.language, source="print('hi')")

    result = stub.parse(context)

    assert result.success is True
    assert result.parser_id == "stub-python"
    assert result.syntax_tree is None


def test_build_stub_registry_registers_both_stubs() -> None:
    registry = build_stub_registry()

    go_language = DEFAULT_REGISTRY.lookup_extension(".go")
    python_language = DEFAULT_REGISTRY.lookup_extension(".py")
    assert go_language is not None
    assert python_language is not None

    assert registry.lookup(go_language) is not None
    assert registry.lookup(python_language) is not None
    assert len(registry) == 2


def test_stub_registry_dispatches_end_to_end_via_manager() -> None:
    registry = build_stub_registry()
    manager = ParserManager(registry)
    go_language = DEFAULT_REGISTRY.lookup_extension(".go")
    assert go_language is not None

    context = ParseContext(path=Path("main.go"), language=go_language, source="package main")
    result = manager.parse(context)

    assert result.success is True
    assert result.parser_id == "stub-go"
