from __future__ import annotations

from pathlib import Path

from rig.languages import DEFAULT_REGISTRY
from rig.languages.model import Language
from rig.parsers.model import ParseContext


def _require_language(extension: str) -> Language:
    language = DEFAULT_REGISTRY.lookup_extension(extension)
    if language is None:
        raise RuntimeError(f"{extension!r} is missing from the default language catalog")
    return language


GO_LANGUAGE = _require_language(".go")

VALID_GO_SOURCE = "package main\n\nfunc main() {\n\tprintln(1)\n}\n"
INVALID_GO_SOURCE = "this is not valid go {{{ func"


def go_context(source: str = VALID_GO_SOURCE, path: str = "main.go") -> ParseContext:
    return ParseContext(path=Path(path), language=GO_LANGUAGE, source=source)
