from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from rig.languages.model import Language
from rig.languages.pipeline import LanguageAnnotatedFile
from rig.parsers.manager import ParserManager
from rig.parsers.model import Diagnostic, ParseContext, ParseResult
from rig.scanner.models import DiscoveredFile


@dataclass(frozen=True)
class ParsedFile:
    file: DiscoveredFile
    language: Language
    result: ParseResult


def parse_repository_files(
    root: Path,
    annotated_files: Sequence[LanguageAnnotatedFile],
    manager: ParserManager,
) -> tuple[ParsedFile, ...]:
    parsed: list[ParsedFile] = []

    for entry in annotated_files:
        if not manager.supports(entry.language):
            continue

        absolute_path = root / entry.file.relative_path
        try:
            source = absolute_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            result = ParseResult.failed(
                parser_id="none",
                language=entry.language,
                diagnostics=(Diagnostic(f"failed to read {absolute_path}: {exc}"),),
            )
            parsed.append(ParsedFile(file=entry.file, language=entry.language, result=result))
            continue

        context = ParseContext(path=absolute_path, language=entry.language, source=source)
        result = manager.parse(context)
        parsed.append(ParsedFile(file=entry.file, language=entry.language, result=result))

    return tuple(parsed)
