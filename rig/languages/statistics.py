from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass

from rig.languages.model import Language


@dataclass(frozen=True)
class LanguageCount:
    language: Language
    count: int


def aggregate_language_counts(languages: Iterable[Language]) -> tuple[LanguageCount, ...]:
    counts = Counter(languages)
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0].display_name))
    return tuple(LanguageCount(language=language, count=count) for language, count in ordered)
