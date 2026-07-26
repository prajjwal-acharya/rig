from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


@dataclass(frozen=True, kw_only=True)
class SourceLocation:
    relative_path: Path
    start_line: int
    start_column: int
    end_line: int
    end_column: int
    start_byte: int | None = None
    end_byte: int | None = None


class DeclarationKind(str, Enum):
    FUNCTION = "function"
    TYPE = "type"
    VARIABLE = "variable"
    IMPORT = "import"


@dataclass(frozen=True, kw_only=True)
class Declaration:
    # Common base for all declaration kinds below - not instantiated
    # directly, construct a concrete subclass instead.
    id: str
    name: str
    kind: DeclarationKind
    location: SourceLocation


@dataclass(frozen=True, kw_only=True)
class FunctionDeclaration(Declaration):
    kind: DeclarationKind = field(default=DeclarationKind.FUNCTION, init=False)
    parameter_count: int = 0
    is_exported: bool = False


@dataclass(frozen=True, kw_only=True)
class TypeDeclaration(Declaration):
    kind: DeclarationKind = field(default=DeclarationKind.TYPE, init=False)
    underlying_kind: str = "unknown"
    is_exported: bool = False


@dataclass(frozen=True, kw_only=True)
class VariableDeclaration(Declaration):
    kind: DeclarationKind = field(default=DeclarationKind.VARIABLE, init=False)
    is_constant: bool = False
    is_exported: bool = False


@dataclass(frozen=True, kw_only=True)
class ImportDeclaration(Declaration):
    kind: DeclarationKind = field(default=DeclarationKind.IMPORT, init=False)
    import_path: str = ""
    alias: str | None = None


@dataclass(frozen=True, kw_only=True)
class File:
    id: str
    relative_path: Path
    language_id: str
    package_name: str | None = None
    declarations: tuple[Declaration, ...] = ()


@dataclass(frozen=True, kw_only=True)
class Package:
    id: str
    name: str
    file_ids: tuple[str, ...] = ()
