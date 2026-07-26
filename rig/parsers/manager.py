from __future__ import annotations

import time
from dataclasses import replace

from rig.languages.model import Language
from rig.parsers.model import Diagnostic, ParseContext, ParseResult
from rig.parsers.registry import ParserRegistry

_NO_PARSER_ID = "none"


class ParserManager:
    def __init__(self, registry: ParserRegistry) -> None:
        self._registry = registry

    def supports(self, language: Language) -> bool:
        return language in self._registry

    def parse(self, context: ParseContext) -> ParseResult:
        parser = self._registry.lookup(context.language)
        if parser is None:
            return ParseResult.failed(
                parser_id=_NO_PARSER_ID,
                language=context.language,
                diagnostics=(
                    Diagnostic(f"no parser registered for language {context.language.id!r}"),
                ),
            )

        start = time.perf_counter()
        try:
            result = parser.parse(context)
        except Exception as exc:  # noqa: BLE001 - a parser failure must not crash the manager
            elapsed = time.perf_counter() - start
            return ParseResult.failed(
                parser_id=parser.parser_id,
                language=context.language,
                diagnostics=(
                    Diagnostic(
                        f"parser {parser.parser_id!r} raised {exc.__class__.__name__}: {exc}"
                    ),
                ),
                elapsed_seconds=elapsed,
            )

        elapsed = time.perf_counter() - start
        return replace(result, elapsed_seconds=elapsed)
