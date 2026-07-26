from __future__ import annotations

import dataclasses

import pytest

from rig.types.model import AliasType, InterfaceType, NamedType, StructType, TypeKind
from tests.types.conftest import location


def _kwargs() -> dict[str, object]:
    return {
        "id": "type:1",
        "declaration_id": "declaration:1",
        "symbol_id": "symbol:1",
        "name": "Widget",
        "package": "pkg1",
        "location": location(),
    }


def test_struct_type_kind_is_fixed() -> None:
    type_ = StructType(**_kwargs())  # type: ignore[arg-type]

    assert type_.kind == TypeKind.STRUCT
    with pytest.raises(TypeError):
        StructType(**_kwargs(), kind=TypeKind.INTERFACE)  # type: ignore[arg-type, call-arg]


def test_interface_type_kind_is_fixed() -> None:
    type_ = InterfaceType(**_kwargs())  # type: ignore[arg-type]

    assert type_.kind == TypeKind.INTERFACE


def test_alias_type_kind_is_fixed() -> None:
    type_ = AliasType(**_kwargs())  # type: ignore[arg-type]

    assert type_.kind == TypeKind.ALIAS


def test_named_type_kind_is_fixed() -> None:
    type_ = NamedType(**_kwargs())  # type: ignore[arg-type]

    assert type_.kind == TypeKind.NAMED


def test_type_is_immutable() -> None:
    type_ = StructType(**_kwargs())  # type: ignore[arg-type]

    with pytest.raises(dataclasses.FrozenInstanceError):
        type_.name = "Other"  # type: ignore[misc]


def test_package_may_be_none_for_orphan_files() -> None:
    kwargs = _kwargs()
    kwargs["package"] = None
    type_ = StructType(**kwargs)  # type: ignore[arg-type]

    assert type_.package is None
