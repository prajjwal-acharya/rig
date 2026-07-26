from __future__ import annotations

from rig.languages import DEFAULT_REGISTRY
from rig.languages.model import Language
from rig.parsers.interface import Parser
from rig.parsers.model import ParseContext, ParseResult
from rig.parsers.registry import ParserRegistry


def _require_language(extension: str) -> Language:
    language = DEFAULT_REGISTRY.lookup_extension(extension)
    if language is None:
        raise RuntimeError(f"{extension!r} is missing from the default language catalog")
    return language


_GO_LANGUAGE = _require_language(".go")
_PYTHON_LANGUAGE = _require_language(".py")


class GoParserStub(Parser):
    @property
    def language(self) -> Language:
        return _GO_LANGUAGE

    @property
    def parser_id(self) -> str:
        return "stub-go"

    @property
    def parser_version(self) -> str | None:
        return "0.1.0"

    def parse(self, context: ParseContext) -> ParseResult:
        return ParseResult.ok(parser_id=self.parser_id, language=self.language)


class PythonParserStub(Parser):
    @property
    def language(self) -> Language:
        return _PYTHON_LANGUAGE

    @property
    def parser_id(self) -> str:
        return "stub-python"

    @property
    def parser_version(self) -> str | None:
        return "0.1.0"

    def parse(self, context: ParseContext) -> ParseResult:
        return ParseResult.ok(parser_id=self.parser_id, language=self.language)


def build_stub_registry() -> ParserRegistry:
    return ParserRegistry([GoParserStub(), PythonParserStub()])
