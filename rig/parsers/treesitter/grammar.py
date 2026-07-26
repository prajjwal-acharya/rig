from __future__ import annotations

import threading
from collections.abc import Iterable
from dataclasses import dataclass, field

from tree_sitter import Language as TSLanguage

from rig.parsers.treesitter.errors import DuplicateGrammarError


@dataclass(frozen=True)
class Grammar:
    language_id: str
    # Excluded from equality/hash: identity of the underlying C-backed
    # object is not a meaningful part of a grammar's value.
    ts_language: TSLanguage = field(compare=False)
    parser_id: str
    version: str | None = None


class GrammarRegistry:
    def __init__(self, grammars: Iterable[Grammar] = ()) -> None:
        self._lock = threading.Lock()
        self._by_language_id: dict[str, Grammar] = {}
        for grammar in grammars:
            self.register(grammar)

    def register(self, grammar: Grammar) -> None:
        with self._lock:
            existing = self._by_language_id.get(grammar.language_id)
            if existing is not None:
                raise DuplicateGrammarError(
                    f"a grammar is already registered for language {grammar.language_id!r}: "
                    f"{existing.parser_id!r} (attempted to register {grammar.parser_id!r})"
                )
            self._by_language_id[grammar.language_id] = grammar

    def lookup(self, language_id: str) -> Grammar | None:
        return self._by_language_id.get(language_id)

    def grammars(self) -> tuple[Grammar, ...]:
        return tuple(self._by_language_id.values())

    def __len__(self) -> int:
        return len(self._by_language_id)

    def __contains__(self, language_id: str) -> bool:
        return language_id in self._by_language_id
