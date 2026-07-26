from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from rig.languages.catalog import DEFAULT_REGISTRY
from rig.languages.detector import LanguageDetector
from rig.languages.model import Language
from rig.languages.statistics import LanguageCount, aggregate_language_counts
from rig.scanner.models import DiscoveredFile


@dataclass(frozen=True)
class LanguageAnnotatedFile:
    file: DiscoveredFile
    language: Language


@dataclass(frozen=True)
class RepositoryLanguageReport:
    files: tuple[LanguageAnnotatedFile, ...]
    statistics: tuple[LanguageCount, ...]


def detect_repository_languages(
    files: Sequence[DiscoveredFile],
    detector: LanguageDetector | None = None,
) -> RepositoryLanguageReport:
    detector = detector or LanguageDetector(DEFAULT_REGISTRY)

    annotated = tuple(
        LanguageAnnotatedFile(file=file, language=detector.detect(file.relative_path))
        for file in files
    )
    statistics = aggregate_language_counts(entry.language for entry in annotated)

    return RepositoryLanguageReport(files=annotated, statistics=statistics)
