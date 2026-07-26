from __future__ import annotations

from rig.languages import DEFAULT_REGISTRY as DEFAULT_LANGUAGE_REGISTRY
from rig.languages.model import Language
from rig.parsers.interface import Parser
from rig.parsers.registry import ParserRegistry
from rig.parsers.stubs import PythonParserStub
from rig.parsers.treesitter.backend import TreeSitterBackend
from rig.parsers.treesitter.catalog import DEFAULT_GRAMMAR_REGISTRY
from rig.parsers.treesitter.grammar import Grammar, GrammarRegistry
from rig.parsers.treesitter.parser import TreeSitterParser


def _language_for(grammar: Grammar) -> Language | None:
    for language in DEFAULT_LANGUAGE_REGISTRY.languages():
        if language.id == grammar.language_id:
            return language
    return None


def build_treesitter_parsers(
    grammar_registry: GrammarRegistry | None = None,
    backend: TreeSitterBackend | None = None,
) -> tuple[TreeSitterParser, ...]:
    """Build one TreeSitterParser per registered grammar with a matching
    `rig.languages` entry. Adding a new grammar to the catalog is enough for
    it to show up here - nothing here is Go-specific or language-specific.
    """
    grammar_registry = grammar_registry or DEFAULT_GRAMMAR_REGISTRY
    backend = backend or TreeSitterBackend()

    parsers: list[TreeSitterParser] = []
    for grammar in grammar_registry.grammars():
        language = _language_for(grammar)
        if language is None:
            continue
        parsers.append(TreeSitterParser(language=language, grammar=grammar, backend=backend))

    return tuple(parsers)


def build_default_registry() -> ParserRegistry:
    """A ready-to-use registry: real Tree-sitter parsers for every grammar in
    the default catalog, plus stub parsers for languages without one yet.
    """
    parsers: list[Parser] = list(build_treesitter_parsers())
    covered_language_ids = {parser.language.id for parser in parsers}

    if "python" not in covered_language_ids:
        parsers.append(PythonParserStub())

    return ParserRegistry(parsers)
