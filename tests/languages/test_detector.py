from __future__ import annotations

from pathlib import Path

from rig.languages.detector import LanguageDetector
from rig.languages.model import UNKNOWN_LANGUAGE, Language
from rig.languages.registry import LanguageRegistry

PYTHON = Language(id="python", display_name="Python", extensions=frozenset({"py"}))
JAVASCRIPT = Language(id="javascript", display_name="JavaScript", extensions=frozenset({"js"}))
DOCKERFILE = Language(
    id="dockerfile",
    display_name="Dockerfile",
    extensions=frozenset({"dockerfile"}),
    filenames=frozenset({"Dockerfile"}),
)
MAKEFILE = Language(id="makefile", display_name="Makefile", filenames=frozenset({"Makefile"}))
GZIP_ARCHIVE = Language(id="gzip", display_name="Gzip", extensions=frozenset({"gz"}))


def _detector() -> LanguageDetector:
    registry = LanguageRegistry([PYTHON, JAVASCRIPT, DOCKERFILE, MAKEFILE])
    return LanguageDetector(registry)


def test_detects_by_extension() -> None:
    assert _detector().detect(Path("main.py")) == PYTHON


def test_detects_by_extension_in_nested_path() -> None:
    assert _detector().detect(Path("src/pkg/app.js")) == JAVASCRIPT


def test_detects_by_exact_filename() -> None:
    assert _detector().detect(Path("Dockerfile")) == DOCKERFILE


def test_detects_by_exact_filename_in_nested_path() -> None:
    assert _detector().detect(Path("build/Makefile")) == MAKEFILE


def test_filename_match_takes_priority_over_extension() -> None:
    # "Dockerfile" has no extension of its own, but this proves filename
    # lookup happens before any extension-based fallback is even attempted.
    assert _detector().detect(Path("Dockerfile")) == DOCKERFILE


def test_unregistered_extension_is_unknown() -> None:
    assert _detector().detect(Path("data.xyz")) == UNKNOWN_LANGUAGE


def test_file_without_extension_is_unknown() -> None:
    assert _detector().detect(Path("LICENSE")) == UNKNOWN_LANGUAGE


def test_hidden_file_without_recognized_extension_is_unknown() -> None:
    assert _detector().detect(Path(".gitignore")) == UNKNOWN_LANGUAGE


def test_hidden_file_with_recognized_extension_is_detected() -> None:
    assert _detector().detect(Path(".config.py")) == PYTHON


def test_uppercase_extension_is_detected() -> None:
    assert _detector().detect(Path("MAIN.PY")) == PYTHON


def test_mixed_case_extension_is_detected() -> None:
    assert _detector().detect(Path("Main.Py")) == PYTHON


def test_multiple_dots_uses_final_extension() -> None:
    registry = LanguageRegistry([JAVASCRIPT])
    detector = LanguageDetector(registry)

    assert detector.detect(Path("app.min.js")) == JAVASCRIPT


def test_multiple_dots_with_unregistered_final_extension_is_unknown() -> None:
    registry = LanguageRegistry([GZIP_ARCHIVE])
    detector = LanguageDetector(registry)

    # "archive.tar.gz" - only the final suffix (".gz") is considered.
    assert detector.detect(Path("archive.tar.gz")) == GZIP_ARCHIVE
    assert detector.detect(Path("archive.tar.unknownext")) == UNKNOWN_LANGUAGE


def test_empty_string_path_is_unknown() -> None:
    assert _detector().detect(Path("")) == UNKNOWN_LANGUAGE


def test_empty_string_input_is_unknown() -> None:
    assert _detector().detect("") == UNKNOWN_LANGUAGE


def test_accepts_plain_string_path() -> None:
    assert _detector().detect("main.py") == PYTHON


def test_directory_like_trailing_slash_path_is_unknown() -> None:
    assert _detector().detect(Path("src/pkg/")) == UNKNOWN_LANGUAGE


def test_detection_never_touches_filesystem(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist.py"
    assert not missing.exists()

    assert _detector().detect(missing) == PYTHON
