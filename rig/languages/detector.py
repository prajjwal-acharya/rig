from __future__ import annotations

from pathlib import Path

from rig.languages.model import UNKNOWN_LANGUAGE, Language
from rig.languages.registry import LanguageRegistry


class LanguageDetector:
    def __init__(self, registry: LanguageRegistry) -> None:
        self._registry = registry

    def detect(self, path: Path | str) -> Language:
        candidate = path if isinstance(path, Path) else Path(path)
        name = candidate.name
        if not name:
            return UNKNOWN_LANGUAGE

        by_filename = self._registry.lookup_filename(name)
        if by_filename is not None:
            return by_filename

        suffix = candidate.suffix
        if suffix:
            by_extension = self._registry.lookup_extension(suffix.lower())
            if by_extension is not None:
                return by_extension

        return UNKNOWN_LANGUAGE
