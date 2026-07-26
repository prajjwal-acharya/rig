from __future__ import annotations

from rig.types.index import TypeIndex
from rig.types.model import AliasType, InterfaceType, NamedType, StructType, Type
from rig.types.visitor import TypeVisitor, iter_types
from tests.types.conftest import location


def _all_kinds() -> list[Type]:
    common: dict[str, object] = {"package": "pkg1", "location": location()}
    return [
        StructType(id="type:1", declaration_id="d:1", symbol_id="s:1", name="Point", **common),  # type: ignore[arg-type]
        InterfaceType(id="type:2", declaration_id="d:2", symbol_id="s:2", name="Shape", **common),  # type: ignore[arg-type]
        AliasType(id="type:3", declaration_id="d:3", symbol_id="s:3", name="ID", **common),  # type: ignore[arg-type]
        NamedType(id="type:4", declaration_id="d:4", symbol_id="s:4", name="Celsius", **common),  # type: ignore[arg-type]
    ]


class _RecordingVisitor(TypeVisitor):
    def __init__(self) -> None:
        self.structs: list[str] = []
        self.interfaces: list[str] = []
        self.aliases: list[str] = []
        self.named: list[str] = []

    def visit_struct(self, type_: StructType) -> None:
        self.structs.append(type_.name)

    def visit_interface(self, type_: InterfaceType) -> None:
        self.interfaces.append(type_.name)

    def visit_alias(self, type_: AliasType) -> None:
        self.aliases.append(type_.name)

    def visit_named(self, type_: NamedType) -> None:
        self.named.append(type_.name)


def test_visit_index_dispatches_to_the_matching_kind() -> None:
    index = TypeIndex()
    for type_ in _all_kinds():
        index.add_type(type_)
    visitor = _RecordingVisitor()

    visitor.visit_index(index)

    assert visitor.structs == ["Point"]
    assert visitor.interfaces == ["Shape"]
    assert visitor.aliases == ["ID"]
    assert visitor.named == ["Celsius"]


def test_default_visitor_methods_are_no_ops() -> None:
    visitor = TypeVisitor()

    for type_ in _all_kinds():
        visitor.visit_type(type_)  # must not raise


def test_iter_types_yields_index_contents() -> None:
    index = TypeIndex()
    types = _all_kinds()
    for type_ in types:
        index.add_type(type_)

    assert list(iter_types(index)) == list(index.types())
