from __future__ import annotations

import dataclasses

import pytest

from rig.languages.model import UNKNOWN_LANGUAGE, Language


def test_extensions_are_normalized_with_leading_dot_and_lowercased() -> None:
    language = Language(id="python", display_name="Python", extensions=frozenset({"PY", ".Pyw"}))

    assert language.extensions == frozenset({".py", ".pyw"})


def test_filenames_are_stored_as_frozenset() -> None:
    language = Language(id="make", display_name="Makefile", filenames=frozenset({"Makefile"}))

    assert language.filenames == frozenset({"Makefile"})
    assert isinstance(language.filenames, frozenset)


def test_language_is_immutable() -> None:
    language = Language(id="python", display_name="Python", extensions=frozenset({"py"}))

    with pytest.raises(dataclasses.FrozenInstanceError):
        language.display_name = "Something else"  # type: ignore[misc]


def test_language_is_hashable_and_usable_as_dict_key() -> None:
    language = Language(id="python", display_name="Python", extensions=frozenset({"py"}))

    counts = {language: 1}
    assert counts[language] == 1


def test_equal_languages_compare_equal() -> None:
    a = Language(id="python", display_name="Python", extensions=frozenset({"py"}))
    b = Language(id="python", display_name="Python", extensions=frozenset({"py"}))

    assert a == b
    assert hash(a) == hash(b)


def test_unknown_language_has_no_extensions_or_filenames() -> None:
    assert UNKNOWN_LANGUAGE.id == "unknown"
    assert UNKNOWN_LANGUAGE.extensions == frozenset()
    assert UNKNOWN_LANGUAGE.filenames == frozenset()


def test_parser_id_defaults_to_none() -> None:
    language = Language(id="python", display_name="Python")

    assert language.parser_id is None
