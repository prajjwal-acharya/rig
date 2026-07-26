from __future__ import annotations

from dataclasses import dataclass, field


def _normalize_extension(extension: str) -> str:
    normalized = extension if extension.startswith(".") else f".{extension}"
    return normalized.lower()


@dataclass(frozen=True)
class Language:
    id: str
    display_name: str
    extensions: frozenset[str] = field(default_factory=frozenset)
    filenames: frozenset[str] = field(default_factory=frozenset)
    parser_id: str | None = None

    def __post_init__(self) -> None:
        normalized_extensions = frozenset(_normalize_extension(ext) for ext in self.extensions)
        object.__setattr__(self, "extensions", normalized_extensions)
        object.__setattr__(self, "filenames", frozenset(self.filenames))


UNKNOWN_LANGUAGE = Language(id="unknown", display_name="Unknown")
