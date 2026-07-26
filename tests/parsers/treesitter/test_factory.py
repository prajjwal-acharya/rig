from __future__ import annotations

import tree_sitter_go
from tree_sitter import Language as TSLanguage

from rig.parsers.treesitter.factory import build_default_registry, build_treesitter_parsers
from rig.parsers.treesitter.grammar import Grammar, GrammarRegistry
from rig.parsers.treesitter.parser import TreeSitterParser
from tests.parsers.treesitter.conftest import GO_LANGUAGE


def test_build_treesitter_parsers_produces_a_go_parser() -> None:
    parsers = build_treesitter_parsers()

    assert len(parsers) == 1
    assert parsers[0].language == GO_LANGUAGE
    assert parsers[0].parser_id == "tree-sitter-go"
    assert isinstance(parsers[0], TreeSitterParser)


def test_build_treesitter_parsers_skips_grammars_with_no_matching_language() -> None:
    fake_grammar = Grammar(
        language_id="not-a-real-language",
        ts_language=TSLanguage(tree_sitter_go.language()),
        parser_id="fake",
    )
    registry = GrammarRegistry([fake_grammar])

    parsers = build_treesitter_parsers(grammar_registry=registry)

    assert parsers == ()


def test_build_treesitter_parsers_shares_one_backend_across_grammars() -> None:
    parsers = build_treesitter_parsers()

    # only one grammar is registered today, but this documents the intent:
    # every TreeSitterParser built by this call shares a single backend.
    assert all(p._backend is parsers[0]._backend for p in parsers)


def test_build_default_registry_replaces_go_stub_with_real_parser() -> None:
    registry = build_default_registry()

    go_parser = registry.lookup(GO_LANGUAGE)

    assert go_parser is not None
    assert isinstance(go_parser, TreeSitterParser)
    assert go_parser.parser_id == "tree-sitter-go"


def test_build_default_registry_still_includes_python_stub() -> None:
    from rig.languages import DEFAULT_REGISTRY

    python_language = DEFAULT_REGISTRY.lookup_extension(".py")
    assert python_language is not None

    registry = build_default_registry()
    python_parser = registry.lookup(python_language)

    assert python_parser is not None
    assert python_parser.parser_id == "stub-python"
