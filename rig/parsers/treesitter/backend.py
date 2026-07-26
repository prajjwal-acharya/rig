from __future__ import annotations

import threading

from tree_sitter import Parser as TSParser

from rig.parsers.treesitter.grammar import Grammar
from rig.parsers.treesitter.tree import SyntaxTree


class TreeSitterBackend:
    """Owns Tree-sitter parser lifecycle: one `tree_sitter.Parser` per grammar,
    reused across every `parse()` call rather than rebuilt per file.

    `tree_sitter.Parser` instances are not safe to invoke concurrently from
    multiple threads, so reuse is scoped per-thread (via `threading.local`)
    rather than guarded by a single lock - this keeps genuinely concurrent
    parsing of the same language lock-free across threads.
    """

    def __init__(self) -> None:
        self._local = threading.local()

    def _parser_for(self, grammar: Grammar) -> TSParser:
        cache: dict[str, TSParser] | None = getattr(self._local, "parsers", None)
        if cache is None:
            cache = {}
            self._local.parsers = cache

        parser = cache.get(grammar.parser_id)
        if parser is None:
            parser = TSParser(grammar.ts_language)
            cache[grammar.parser_id] = parser
        return parser

    def parse(self, grammar: Grammar, source: bytes) -> SyntaxTree:
        parser = self._parser_for(grammar)
        tree = parser.parse(source)
        return SyntaxTree(tree)
