from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from rig.languages.model import Language


class DiagnosticSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class Diagnostic:
    message: str
    severity: DiagnosticSeverity = DiagnosticSeverity.ERROR


@dataclass(frozen=True)
class ParseContext:
    path: Path
    language: Language
    source: str
    config: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ParseResult:
    success: bool
    parser_id: str
    language: Language
    diagnostics: tuple[Diagnostic, ...] = ()
    elapsed_seconds: float = 0.0
    # Reserved for a future concrete syntax tree; intentionally untyped and
    # unpopulated until a real parser (e.g. Tree-sitter) exists.
    syntax_tree: Any | None = None

    @classmethod
    def ok(
        cls,
        *,
        parser_id: str,
        language: Language,
        diagnostics: tuple[Diagnostic, ...] = (),
        elapsed_seconds: float = 0.0,
        syntax_tree: Any | None = None,
    ) -> ParseResult:
        return cls(
            success=True,
            parser_id=parser_id,
            language=language,
            diagnostics=diagnostics,
            elapsed_seconds=elapsed_seconds,
            syntax_tree=syntax_tree,
        )

    @classmethod
    def failed(
        cls,
        *,
        parser_id: str,
        language: Language,
        diagnostics: tuple[Diagnostic, ...],
        elapsed_seconds: float = 0.0,
    ) -> ParseResult:
        return cls(
            success=False,
            parser_id=parser_id,
            language=language,
            diagnostics=diagnostics,
            elapsed_seconds=elapsed_seconds,
        )
