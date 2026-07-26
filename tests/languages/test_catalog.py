from __future__ import annotations

from pathlib import Path

from rig.languages.catalog import DEFAULT_LANGUAGES, DEFAULT_REGISTRY
from rig.languages.detector import LanguageDetector


def test_default_registry_has_no_duplicate_ids() -> None:
    ids = [language.id for language in DEFAULT_LANGUAGES]
    assert len(ids) == len(set(ids))


def test_default_registry_contains_expected_languages() -> None:
    ids = {language.id for language in DEFAULT_LANGUAGES}
    assert {"go", "yaml", "markdown", "shell", "dockerfile", "python"} <= ids


def test_default_detector_identifies_common_files() -> None:
    detector = LanguageDetector(DEFAULT_REGISTRY)

    assert detector.detect(Path("main.go")).display_name == "Go"
    assert detector.detect(Path("config.yaml")).display_name == "YAML"
    assert detector.detect(Path("README.md")).display_name == "Markdown"
    assert detector.detect(Path("deploy.sh")).display_name == "Shell"
    assert detector.detect(Path("Dockerfile")).display_name == "Dockerfile"
    assert detector.detect(Path("Makefile")).display_name == "Makefile"
    assert detector.detect(Path("main.py")).display_name == "Python"


def test_default_registry_lookup_is_case_insensitive_for_extensions() -> None:
    detector = LanguageDetector(DEFAULT_REGISTRY)

    assert detector.detect(Path("main.GO")).display_name == "Go"
