from __future__ import annotations

from pathlib import Path

from rig.languages.detector import LanguageDetector
from rig.languages.model import UNKNOWN_LANGUAGE, Language
from rig.languages.pipeline import detect_repository_languages
from rig.languages.registry import LanguageRegistry
from rig.scanner.models import DiscoveredFile

PYTHON = Language(id="python", display_name="Python", extensions=frozenset({"py"}))
MARKDOWN = Language(id="markdown", display_name="Markdown", extensions=frozenset({"md"}))


def _detector() -> LanguageDetector:
    return LanguageDetector(LanguageRegistry([PYTHON, MARKDOWN]))


def test_annotates_every_discovered_file() -> None:
    files = [
        DiscoveredFile(relative_path=Path("main.py")),
        DiscoveredFile(relative_path=Path("README.md")),
        DiscoveredFile(relative_path=Path("LICENSE")),
    ]

    report = detect_repository_languages(files, _detector())

    languages = {entry.file.relative_path: entry.language for entry in report.files}
    assert languages[Path("main.py")] == PYTHON
    assert languages[Path("README.md")] == MARKDOWN
    assert languages[Path("LICENSE")] == UNKNOWN_LANGUAGE


def test_preserves_the_original_discovered_file_reference() -> None:
    file = DiscoveredFile(relative_path=Path("main.py"))

    report = detect_repository_languages([file], _detector())

    assert report.files[0].file is file


def test_statistics_reflect_annotated_files() -> None:
    files = [
        DiscoveredFile(relative_path=Path("a.py")),
        DiscoveredFile(relative_path=Path("b.py")),
        DiscoveredFile(relative_path=Path("c.md")),
    ]

    report = detect_repository_languages(files, _detector())

    counts = {entry.language: entry.count for entry in report.statistics}
    assert counts[PYTHON] == 2
    assert counts[MARKDOWN] == 1


def test_empty_file_list_produces_empty_report() -> None:
    report = detect_repository_languages([], _detector())

    assert report.files == ()
    assert report.statistics == ()


def test_uses_default_registry_when_no_detector_given() -> None:
    files = [DiscoveredFile(relative_path=Path("main.py"))]

    report = detect_repository_languages(files)

    assert report.files[0].language.display_name == "Python"
