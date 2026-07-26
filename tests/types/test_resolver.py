from __future__ import annotations

from rig.types.index import TypeIndex
from rig.types.model import StructType
from rig.types.resolver import TypeResolver
from tests.types.conftest import location


def _struct(name: str, package: str | None, tid: str) -> StructType:
    return StructType(
        id=tid,
        declaration_id=f"declaration:{tid}",
        symbol_id=f"symbol:{tid}",
        name=name,
        package=package,
        location=location(),
    )


def test_resolve_in_package_finds_the_matching_type() -> None:
    index = TypeIndex()
    index.add_type(_struct("Point", "pkg1", "type:1"))
    index.add_type(_struct("Point", "pkg2", "type:2"))
    resolver = TypeResolver(index)

    result = resolver.resolve_in_package("pkg2", "Point")

    assert result is not None
    assert result.package == "pkg2"


def test_resolve_in_package_returns_none_when_absent() -> None:
    index = TypeIndex()
    resolver = TypeResolver(index)

    assert resolver.resolve_in_package("pkg1", "Missing") is None


def test_resolve_in_repository_returns_the_lowest_id_match_deterministically() -> None:
    index = TypeIndex()
    index.add_type(_struct("Point", "pkg2", "type:2"))
    index.add_type(_struct("Point", "pkg1", "type:1"))
    resolver = TypeResolver(index)

    result = resolver.resolve_in_repository("Point")

    assert result is not None
    assert result.id == "type:1"


def test_resolve_in_repository_returns_none_when_absent() -> None:
    index = TypeIndex()
    resolver = TypeResolver(index)

    assert resolver.resolve_in_repository("Missing") is None


def test_resolve_in_repository_is_unambiguous_for_a_single_match() -> None:
    index = TypeIndex()
    index.add_type(_struct("Point", "pkg1", "type:1"))
    resolver = TypeResolver(index)

    result = resolver.resolve_in_repository("Point")

    assert result is not None
    assert result.package == "pkg1"
