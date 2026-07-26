from __future__ import annotations

import dataclasses

import pytest

from rig.symbols.scope import FileScope, PackageScope, RepositoryScope, ScopeKind


def test_repository_scope_kind() -> None:
    scope = RepositoryScope(id="s1", name="repo")
    assert scope.kind == ScopeKind.REPOSITORY


def test_package_scope_kind() -> None:
    scope = PackageScope(id="s1", name="pkg1")
    assert scope.kind == ScopeKind.PACKAGE


def test_file_scope_kind() -> None:
    scope = FileScope(id="s1", name="a.go")
    assert scope.kind == ScopeKind.FILE


def test_scope_defaults() -> None:
    scope = PackageScope(id="s1", name="pkg1")
    assert scope.parent_id is None
    assert scope.symbol_ids == ()


def test_lookup_local_finds_declared_name() -> None:
    scope = PackageScope(id="s1", name="pkg1", symbol_ids=(("Foo", "sym:1"), ("Bar", "sym:2")))
    assert scope.lookup_local("Foo") == "sym:1"
    assert scope.lookup_local("Bar") == "sym:2"


def test_lookup_local_returns_none_for_missing_name() -> None:
    scope = PackageScope(id="s1", name="pkg1", symbol_ids=(("Foo", "sym:1"),))
    assert scope.lookup_local("Missing") is None


def test_names_returns_all_declared_names() -> None:
    scope = PackageScope(id="s1", name="pkg1", symbol_ids=(("Foo", "sym:1"), ("Bar", "sym:2")))
    assert scope.names() == ("Foo", "Bar")


def test_as_dict_returns_plain_dict() -> None:
    scope = PackageScope(id="s1", name="pkg1", symbol_ids=(("Foo", "sym:1"),))
    assert scope.as_dict() == {"Foo": "sym:1"}


def test_scope_is_immutable() -> None:
    scope = PackageScope(id="s1", name="pkg1")
    with pytest.raises(dataclasses.FrozenInstanceError):
        scope.name = "other"  # type: ignore[misc]


def test_scope_is_hashable() -> None:
    a = FileScope(id="s1", name="a.go", parent_id="p1", symbol_ids=(("Foo", "sym:1"),))
    b = FileScope(id="s1", name="a.go", parent_id="p1", symbol_ids=(("Foo", "sym:1"),))
    assert a == b
    assert hash(a) == hash(b)


def test_parent_id_is_preserved() -> None:
    scope = FileScope(id="s1", name="a.go", parent_id="pkg-scope-1")
    assert scope.parent_id == "pkg-scope-1"
