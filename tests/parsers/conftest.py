from __future__ import annotations

from rig.languages.model import Language
from rig.parsers.interface import Parser
from rig.parsers.model import ParseContext, ParseResult

FAKE_LANGUAGE = Language(id="fake", display_name="Fake", extensions=frozenset({"fake"}))
OTHER_LANGUAGE = Language(id="other", display_name="Other", extensions=frozenset({"other"}))


class FakeParser(Parser):
    def __init__(self, language: Language = FAKE_LANGUAGE, parser_id: str = "fake-parser") -> None:
        self._language = language
        self._parser_id = parser_id
        self.calls: list[ParseContext] = []

    @property
    def language(self) -> Language:
        return self._language

    @property
    def parser_id(self) -> str:
        return self._parser_id

    def parse(self, context: ParseContext) -> ParseResult:
        self.calls.append(context)
        return ParseResult.ok(parser_id=self.parser_id, language=self.language)


class FailingParser(Parser):
    def __init__(self, language: Language = FAKE_LANGUAGE) -> None:
        self._language = language

    @property
    def language(self) -> Language:
        return self._language

    @property
    def parser_id(self) -> str:
        return "failing-parser"

    def parse(self, context: ParseContext) -> ParseResult:
        raise RuntimeError("boom during parse")
