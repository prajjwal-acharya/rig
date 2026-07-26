from __future__ import annotations

from collections.abc import Iterator

from rig.types.index import TypeIndex
from rig.types.model import AliasType, InterfaceType, NamedType, StructType, Type


def iter_types(index: TypeIndex) -> Iterator[Type]:
    yield from index.types()


class TypeVisitor:
    """Base visitor over a TypeIndex. Subclass and override only the
    `visit_*` methods you care about; the rest provide default traversal.
    Future analyses (interface implementation, embedding, generic
    instantiation, field resolution, dependency analysis, impact analysis)
    should consume types through this layer rather than interpreting
    declarations directly.
    """

    def visit_index(self, index: TypeIndex) -> None:
        for type_ in index.types():
            self.visit_type(type_)

    def visit_type(self, type_: Type) -> None:
        if isinstance(type_, StructType):
            self.visit_struct(type_)
        elif isinstance(type_, InterfaceType):
            self.visit_interface(type_)
        elif isinstance(type_, AliasType):
            self.visit_alias(type_)
        elif isinstance(type_, NamedType):
            self.visit_named(type_)

    def visit_struct(self, type_: StructType) -> None:
        pass

    def visit_interface(self, type_: InterfaceType) -> None:
        pass

    def visit_alias(self, type_: AliasType) -> None:
        pass

    def visit_named(self, type_: NamedType) -> None:
        pass
