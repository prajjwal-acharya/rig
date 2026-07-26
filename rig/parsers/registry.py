from __future__ import annotations

import threading
from collections.abc import Iterable

from rig.languages.model import Language
from rig.parsers.errors import DuplicateParserError
from rig.parsers.interface import Parser


class ParserRegistry:
    def __init__(self, parsers: Iterable[Parser] = ()) -> None:
        self._lock = threading.Lock()
        self._by_language: dict[Language, Parser] = {}
        for parser in parsers:
            self.register(parser)

    def register(self, parser: Parser) -> None:
        with self._lock:
            existing = self._by_language.get(parser.language)
            if existing is not None:
                raise DuplicateParserError(
                    f"a parser is already registered for language {parser.language.id!r}: "
                    f"{existing.parser_id!r} (attempted to register {parser.parser_id!r})"
                )
            self._by_language[parser.language] = parser

    def lookup(self, language: Language) -> Parser | None:
        return self._by_language.get(language)

    def parsers(self) -> tuple[Parser, ...]:
        return tuple(self._by_language.values())

    def __len__(self) -> int:
        return len(self._by_language)

    def __contains__(self, language: Language) -> bool:
        return language in self._by_language
