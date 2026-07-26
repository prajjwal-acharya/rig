from __future__ import annotations

from rig.parsers.treesitter.catalog import DEFAULT_GRAMMAR_REGISTRY
from rig.parsers.treesitter.grammars.go import GO_GRAMMAR


def test_go_grammar_has_expected_identity() -> None:
    assert GO_GRAMMAR.language_id == "go"
    assert GO_GRAMMAR.parser_id == "tree-sitter-go"


def test_go_grammar_is_registered_in_default_catalog() -> None:
    assert DEFAULT_GRAMMAR_REGISTRY.lookup("go") is GO_GRAMMAR


def test_go_grammar_version_is_a_string_or_none() -> None:
    assert GO_GRAMMAR.version is None or isinstance(GO_GRAMMAR.version, str)
