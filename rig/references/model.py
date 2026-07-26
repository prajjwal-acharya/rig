from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from rig.ir.model import SourceLocation


class ReferenceKind(str, Enum):
    TYPE = "type"
    FUNCTION = "function"
    VARIABLE = "variable"
    CONSTANT = "constant"
    PACKAGE = "package"


@dataclass(frozen=True, kw_only=True)
class Reference:
    # Common base for the two concrete outcomes below - not instantiated
    # directly, construct ResolvedReference or UnresolvedReference instead.
    id: str
    identifier: str
    kind: ReferenceKind
    file_id: str
    location: SourceLocation


@dataclass(frozen=True, kw_only=True)
class ResolvedReference(Reference):
    symbol_id: str


@dataclass(frozen=True, kw_only=True)
class UnresolvedReference(Reference):
    reason: str = "no matching declaration in scope"
