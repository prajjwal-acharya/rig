from __future__ import annotations

import pytest

from rig.languages.model import Language
from rig.languages.registry import DuplicateLanguageMappingError, LanguageRegistry


def test_lookup_extension_returns_registered_language() -> None:
    python = Language(id="python", display_name="Python", extensions=frozenset({"py"}))
    registry = LanguageRegistry([python])

    assert registry.lookup_extension(".py") is python


def test_lookup_extension_returns_none_for_unregistered_extension() -> None:
    registry = LanguageRegistry([])

    assert registry.lookup_extension(".py") is None


def test_lookup_filename_returns_registered_language() -> None:
    dockerfile = Language(
        id="dockerfile", display_name="Dockerfile", filenames=frozenset({"Dockerfile"})
    )
    registry = LanguageRegistry([dockerfile])

    assert registry.lookup_filename("Dockerfile") is dockerfile


def test_lookup_filename_returns_none_for_unregistered_filename() -> None:
    registry = LanguageRegistry([])

    assert registry.lookup_filename("Dockerfile") is None


def test_duplicate_extension_across_languages_raises() -> None:
    a = Language(id="a", display_name="A", extensions=frozenset({"foo"}))
    b = Language(id="b", display_name="B", extensions=frozenset({"foo"}))

    with pytest.raises(DuplicateLanguageMappingError):
        LanguageRegistry([a, b])


def test_duplicate_filename_across_languages_raises() -> None:
    a = Language(id="a", display_name="A", filenames=frozenset({"Foo"}))
    b = Language(id="b", display_name="B", filenames=frozenset({"Foo"}))

    with pytest.raises(DuplicateLanguageMappingError):
        LanguageRegistry([a, b])


def test_languages_returns_all_registered_languages() -> None:
    a = Language(id="a", display_name="A", extensions=frozenset({"a"}))
    b = Language(id="b", display_name="B", extensions=frozenset({"b"}))
    registry = LanguageRegistry([a, b])

    assert set(registry.languages()) == {a, b}
    assert len(registry) == 2


def test_registry_internal_maps_are_not_externally_mutable() -> None:
    python = Language(id="python", display_name="Python", extensions=frozenset({"py"}))
    registry = LanguageRegistry([python])

    with pytest.raises(TypeError):
        registry._by_extension[".rb"] = python  # type: ignore[index]
