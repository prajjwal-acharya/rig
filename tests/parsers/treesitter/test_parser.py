from __future__ import annotations

from rig.parsers.model import DiagnosticSeverity
from rig.parsers.treesitter.backend import TreeSitterBackend
from rig.parsers.treesitter.grammars.go import GO_GRAMMAR
from rig.parsers.treesitter.parser import TreeSitterParser
from rig.parsers.treesitter.tree import SyntaxTree
from tests.parsers.treesitter.conftest import GO_LANGUAGE, INVALID_GO_SOURCE, go_context


def _parser() -> TreeSitterParser:
    return TreeSitterParser(language=GO_LANGUAGE, grammar=GO_GRAMMAR, backend=TreeSitterBackend())


def test_parser_exposes_language_and_metadata() -> None:
    parser = _parser()

    assert parser.language == GO_LANGUAGE
    assert parser.parser_id == "tree-sitter-go"
    assert parser.parser_version == GO_GRAMMAR.version


def test_parse_valid_source_succeeds() -> None:
    parser = _parser()

    result = parser.parse(go_context())

    assert result.success is True
    assert result.parser_id == "tree-sitter-go"
    assert result.language == GO_LANGUAGE
    assert result.diagnostics == ()
    assert isinstance(result.syntax_tree, SyntaxTree)
    assert result.syntax_tree.root.type == "source_file"


def test_parse_empty_file_succeeds() -> None:
    parser = _parser()

    result = parser.parse(go_context(source=""))

    assert result.success is True
    assert isinstance(result.syntax_tree, SyntaxTree)
    assert result.syntax_tree.root.child_count == 0
    assert result.diagnostics == ()


def test_parse_invalid_syntax_does_not_raise_and_reports_diagnostic() -> None:
    parser = _parser()

    result = parser.parse(go_context(source=INVALID_GO_SOURCE))

    assert result.success is True  # parsing itself did not crash
    assert isinstance(result.syntax_tree, SyntaxTree)
    assert result.syntax_tree.has_error is True
    assert len(result.diagnostics) == 1
    assert result.diagnostics[0].severity == DiagnosticSeverity.ERROR


def test_multiple_parses_on_the_same_parser_instance() -> None:
    parser = _parser()

    results = [parser.parse(go_context()) for _ in range(10)]

    assert all(r.success for r in results)
    for r in results:
        assert isinstance(r.syntax_tree, SyntaxTree)
        assert r.syntax_tree.root.type == "source_file"
