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


# =========================================================================
# Syntax-extracted semantic facts
#
# Beyond a file's structural declarations, a language frontend records the
# name *uses* it observed in source: identifier references, type-to-type
# references, and cross-module qualified uses. These are pre-resolution facts
# - pure syntax, carrying no symbol/type resolution - so the semantic and
# analysis layers can resolve them against the Symbol Table / Type Index
# without ever touching a concrete syntax tree. This is what lets the IR, and
# not the parser, be the canonical semantic boundary: every concept a
# downstream layer needs about "what a file refers to" lives here, expressed
# in language-neutral terms, and is populated per language by that language's
# frontend.
# =========================================================================


class ReferenceUseKind(str, Enum):
    FUNCTION = "function"
    TYPE = "type"
    VARIABLE = "variable"
    PACKAGE = "package"


@dataclass(frozen=True, kw_only=True)
class ReferenceUse:
    """One occurrence of an identifier *used* (not declared) in source, ready
    for the reference resolver to bind to a symbol. `at_repository_scope`
    marks the few uses (e.g. a package self-reference) resolved at repository
    rather than file scope."""

    identifier: str
    kind: ReferenceUseKind
    location: SourceLocation
    at_repository_scope: bool = False


@dataclass(frozen=True, kw_only=True)
class TypeUse:
    """A reference to a single named type from within a declaration, as it
    appears in source. `name` is None only for a type position that is present
    but is not a simple named type - retained so a frontend can flag it (e.g.
    an unsupported method receiver) without the analysis re-parsing."""

    name: str | None
    location: SourceLocation


@dataclass(frozen=True, kw_only=True)
class StructFieldUse:
    is_embedded: bool
    target: TypeUse


@dataclass(frozen=True, kw_only=True)
class DeclaredTypeUses:
    """The outgoing named-type references of one declared type (a struct's
    fields, or an alias's target). The declaring type is identified by
    (name, package, start_line) so the semantic layer can match it back to the
    exact declaration even when a package declares the same name twice."""

    name: str
    package: str | None
    start_line: int
    kind: str = "other"  # "struct" | "alias" | "other"
    is_generic: bool = False
    location: SourceLocation | None = None  # declaration site (for a generic-type diagnostic)
    fields: tuple[StructFieldUse, ...] = ()
    alias_target: TypeUse | None = None


@dataclass(frozen=True, kw_only=True)
class MethodTypeUses:
    """The receiver / parameter / return named-type references of one method.
    The declaring (receiver) type is resolved by (receiver name, package)."""

    receiver: TypeUse
    package: str | None
    parameters: tuple[TypeUse, ...] = ()
    returns: tuple[TypeUse, ...] = ()


class QualifiedUseKind(str, Enum):
    TYPE = "type"
    CALL = "call"


@dataclass(frozen=True, kw_only=True)
class QualifiedUse:
    """A cross-module qualified reference `qualifier.Name` (a module-qualified
    type or call). `qualifier` is matched to one of the file's imports by the
    dependency analysis."""

    qualifier: str
    kind: QualifiedUseKind
    location: SourceLocation


@dataclass(frozen=True, kw_only=True)
class UnsupportedDependencyUse:
    """A frontend-detected construct the dependency analysis cannot treat as a
    dependency source (a generic exported type, or an unrecognized call target
    shape). Carried so the analysis can report it without re-parsing."""

    reason: str  # "generic_type" | "unrecognized_call"
    name: str | None
    location: SourceLocation


@dataclass(frozen=True, kw_only=True)
class File:
    id: str
    relative_path: Path
    language_id: str
    package_name: str | None = None
    declarations: tuple[Declaration, ...] = ()
    # Syntax-extracted semantic facts (see above). Default-empty so a file
    # produced by a frontend that has not (yet) extracted them stays valid.
    reference_uses: tuple[ReferenceUse, ...] = ()
    declared_type_uses: tuple[DeclaredTypeUses, ...] = ()
    method_type_uses: tuple[MethodTypeUses, ...] = ()
    qualified_uses: tuple[QualifiedUse, ...] = ()
    unsupported_dependency_uses: tuple[UnsupportedDependencyUse, ...] = ()


@dataclass(frozen=True, kw_only=True)
class Package:
    id: str
    name: str
    file_ids: tuple[str, ...] = ()
