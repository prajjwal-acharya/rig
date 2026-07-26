from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from rig.ir.builder import DuplicateIRBuilderError, FileBuildResult, IRBuilder, IRBuilderRegistry
from rig.ir.model import File


class FakeBuilder(IRBuilder):
    def __init__(self, language_id: str = "fake") -> None:
        self._language_id = language_id

    @property
    def language_id(self) -> str:
        return self._language_id

    def build_file(self, repository_id: str, relative_path: Path, tree: Any) -> FileBuildResult:
        file = File(id="f1", relative_path=relative_path, language_id=self._language_id)
        return FileBuildResult(file=file)


def test_register_and_lookup() -> None:
    registry = IRBuilderRegistry()
    builder = FakeBuilder()

    registry.register(builder)

    assert registry.lookup("fake") is builder


def test_lookup_unregistered_language_returns_none() -> None:
    registry = IRBuilderRegistry()

    assert registry.lookup("python") is None


def test_duplicate_registration_raises() -> None:
    registry = IRBuilderRegistry()
    registry.register(FakeBuilder())

    with pytest.raises(DuplicateIRBuilderError):
        registry.register(FakeBuilder())


def test_constructor_accepts_initial_builders() -> None:
    builder = FakeBuilder()

    registry = IRBuilderRegistry([builder])

    assert registry.lookup("fake") is builder
    assert len(registry) == 1


def test_builders_enumerates_all_registered() -> None:
    a = FakeBuilder(language_id="a")
    b = FakeBuilder(language_id="b")
    registry = IRBuilderRegistry([a, b])

    assert set(registry.builders()) == {a, b}


def test_contains_reflects_registered_languages() -> None:
    registry = IRBuilderRegistry([FakeBuilder()])

    assert "fake" in registry
    assert "other" not in registry


def test_file_build_result_diagnostics_default_to_empty() -> None:
    file = File(id="f1", relative_path=Path("main.fake"), language_id="fake")

    result = FileBuildResult(file=file)

    assert result.diagnostics == ()
