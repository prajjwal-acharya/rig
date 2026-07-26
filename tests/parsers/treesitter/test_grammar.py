from __future__ import annotations

import pytest
import tree_sitter_go
from tree_sitter import Language as TSLanguage

from rig.parsers.treesitter.errors import DuplicateGrammarError
from rig.parsers.treesitter.grammar import Grammar, GrammarRegistry

_GO_TS_LANGUAGE = TSLanguage(tree_sitter_go.language())


def _grammar(language_id: str = "go", parser_id: str = "tree-sitter-go") -> Grammar:
    return Grammar(
        language_id=language_id, ts_language=_GO_TS_LANGUAGE, parser_id=parser_id, version="1.0.0"
    )


def test_register_and_lookup() -> None:
    registry = GrammarRegistry()
    grammar = _grammar()

    registry.register(grammar)

    assert registry.lookup("go") is grammar


def test_lookup_unregistered_language_returns_none() -> None:
    registry = GrammarRegistry()

    assert registry.lookup("python") is None


def test_duplicate_registration_raises() -> None:
    registry = GrammarRegistry()
    registry.register(_grammar())

    with pytest.raises(DuplicateGrammarError):
        registry.register(_grammar())


def test_constructor_accepts_initial_grammars() -> None:
    grammar = _grammar()

    registry = GrammarRegistry([grammar])

    assert registry.lookup("go") is grammar
    assert len(registry) == 1


def test_constructor_rejects_duplicates_immediately() -> None:
    with pytest.raises(DuplicateGrammarError):
        GrammarRegistry([_grammar(), _grammar()])


def test_grammars_enumerates_all_registered() -> None:
    go = _grammar(language_id="go", parser_id="a")
    other = _grammar(language_id="other", parser_id="b")
    registry = GrammarRegistry([go, other])

    assert set(registry.grammars()) == {go, other}


def test_contains_reflects_registered_languages() -> None:
    registry = GrammarRegistry([_grammar()])

    assert "go" in registry
    assert "python" not in registry


def test_grammar_equality_ignores_ts_language_identity() -> None:
    other_ts_language = TSLanguage(tree_sitter_go.language())
    a = Grammar(language_id="go", ts_language=_GO_TS_LANGUAGE, parser_id="tree-sitter-go")
    b = Grammar(language_id="go", ts_language=other_ts_language, parser_id="tree-sitter-go")

    assert a == b
    assert hash(a) == hash(b)


def test_grammar_version_defaults_to_none() -> None:
    grammar = Grammar(language_id="go", ts_language=_GO_TS_LANGUAGE, parser_id="tree-sitter-go")

    assert grammar.version is None
