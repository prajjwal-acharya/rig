from __future__ import annotations

from rig.languages.model import Language
from rig.parsers.interface import Parser
from rig.parsers.model import Diagnostic, DiagnosticSeverity, ParseContext, ParseResult
from rig.parsers.treesitter.backend import TreeSitterBackend
from rig.parsers.treesitter.grammar import Grammar


class TreeSitterParser(Parser):
    """Generic Tree-sitter-backed parser. Bound to exactly one language and
    grammar at construction time; contains no language-specific logic itself.
    """

    def __init__(self, language: Language, grammar: Grammar, backend: TreeSitterBackend) -> None:
        self._language = language
        self._grammar = grammar
        self._backend = backend

    @property
    def language(self) -> Language:
        return self._language

    @property
    def parser_id(self) -> str:
        return self._grammar.parser_id

    @property
    def parser_version(self) -> str | None:
        return self._grammar.version

    def parse(self, context: ParseContext) -> ParseResult:
        source_bytes = context.source.encode("utf-8")
        tree = self._backend.parse(self._grammar, source_bytes)

        diagnostics: tuple[Diagnostic, ...] = ()
        if tree.has_error:
            diagnostics = (
                Diagnostic(
                    "source contains one or more syntax errors",
                    severity=DiagnosticSeverity.ERROR,
                ),
            )

        return ParseResult.ok(
            parser_id=self.parser_id,
            language=self.language,
            diagnostics=diagnostics,
            syntax_tree=tree,
        )
