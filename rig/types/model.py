from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from rig.ir.model import SourceLocation


class TypeKind(str, Enum):
    STRUCT = "struct"
    INTERFACE = "interface"
    ALIAS = "alias"
    NAMED = "named"


@dataclass(frozen=True, kw_only=True)
class Type:
    # Common base for all type kinds below - not instantiated directly,
    # construct a concrete subclass instead. Fields and methods are
    # deliberately not modeled yet - this milestone only indexes type
    # declarations, it does not describe their members.
    id: str
    declaration_id: str
    symbol_id: str
    name: str
    package: str | None
    kind: TypeKind
    location: SourceLocation


@dataclass(frozen=True, kw_only=True)
class StructType(Type):
    kind: TypeKind = field(default=TypeKind.STRUCT, init=False)


@dataclass(frozen=True, kw_only=True)
class InterfaceType(Type):
    kind: TypeKind = field(default=TypeKind.INTERFACE, init=False)


@dataclass(frozen=True, kw_only=True)
class AliasType(Type):
    kind: TypeKind = field(default=TypeKind.ALIAS, init=False)


@dataclass(frozen=True, kw_only=True)
class NamedType(Type):
    # A defined type whose underlying type is neither a struct nor an
    # interface (e.g. `type ID int`, `type Handler func()`).
    kind: TypeKind = field(default=TypeKind.NAMED, init=False)
