from __future__ import annotations

from collections import Counter

from rig.ir.model import TypeDeclaration
from rig.ir.repository import RepositoryIR
from rig.symbols.model import TypeSymbol
from rig.symbols.table import SymbolTable
from rig.types.diagnostics import TypeDiagnostic, TypeDiagnosticSeverity
from rig.types.identifiers import type_id
from rig.types.index import TypeIndex
from rig.types.model import AliasType, InterfaceType, NamedType, StructType, Type


def _build_type(declaration: TypeDeclaration, *, package: str | None, symbol_id: str) -> Type:
    tid = type_id(declaration.id)
    if declaration.underlying_kind == "struct":
        return StructType(
            id=tid,
            declaration_id=declaration.id,
            symbol_id=symbol_id,
            name=declaration.name,
            package=package,
            location=declaration.location,
        )
    if declaration.underlying_kind == "interface":
        return InterfaceType(
            id=tid,
            declaration_id=declaration.id,
            symbol_id=symbol_id,
            name=declaration.name,
            package=package,
            location=declaration.location,
        )
    if declaration.underlying_kind == "alias":
        return AliasType(
            id=tid,
            declaration_id=declaration.id,
            symbol_id=symbol_id,
            name=declaration.name,
            package=package,
            location=declaration.location,
        )
    return NamedType(
        id=tid,
        declaration_id=declaration.id,
        symbol_id=symbol_id,
        name=declaration.name,
        package=package,
        location=declaration.location,
    )


class GoTypeBuilder:
    """Builds a TypeIndex from a RepositoryIR + SymbolTable.

    Named for consistency with this project's per-language builder
    convention (GoIRBuilder, GoSymbolTableBuilder, ...), but contains no
    Go-specific logic: RepositoryIR's TypeDeclaration model is already
    language-independent, so nothing here would need to change to index a
    repository produced by a future non-Go IR builder.
    """

    def build(self, repository: RepositoryIR, symbols: SymbolTable) -> TypeIndex:
        index = TypeIndex()
        symbol_id_by_declaration_id = {
            symbol.declaration_id: symbol.id
            for symbol in symbols.symbols()
            if isinstance(symbol, TypeSymbol)
        }

        # One Counter per package name (files are already sorted by
        # relative_path, so occurrence order - and therefore which
        # occurrence gets flagged as the duplicate - is deterministic).
        # `None` (orphan files with no resolvable package) shares a bucket
        # too, but never gets diagnosed - there is no real package scope to
        # call it a duplicate "in".
        occurrence_counts: dict[str | None, Counter[str]] = {}

        for file in repository.files:
            counts = occurrence_counts.setdefault(file.package_name, Counter())
            for declaration in file.declarations:
                if not isinstance(declaration, TypeDeclaration):
                    continue

                occurrence = counts[declaration.name]
                counts[declaration.name] += 1
                if occurrence > 0 and file.package_name is not None:
                    index.add_diagnostic(
                        TypeDiagnostic(
                            message=(
                                f"duplicate type {declaration.name!r} in "
                                f"package {file.package_name!r}"
                            ),
                            severity=TypeDiagnosticSeverity.WARNING,
                            location=declaration.location,
                        )
                    )

                symbol_id = symbol_id_by_declaration_id.get(declaration.id)
                if symbol_id is None:
                    # Defensive: every TypeDeclaration should have a
                    # matching TypeSymbol when `symbols` was built from this
                    # same `repository`. Skip rather than guess if not.
                    continue

                index.add_type(
                    _build_type(declaration, package=file.package_name, symbol_id=symbol_id)
                )

        return index
