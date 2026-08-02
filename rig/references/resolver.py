from __future__ import annotations

from abc import ABC, abstractmethod

from rig.ir.model import File, ReferenceUse
from rig.ir.repository import RepositoryIR
from rig.references.diagnostics import ReferenceDiagnostic, ReferenceDiagnosticSeverity
from rig.references.identifiers import reference_id
from rig.references.index import ReferenceIndex
from rig.references.model import ReferenceKind, ResolvedReference, UnresolvedReference
from rig.symbols.identifiers import file_scope_id, repository_scope_id
from rig.symbols.model import (
    ConstantSymbol,
    FunctionSymbol,
    PackageSymbol,
    TypeSymbol,
    VariableSymbol,
)
from rig.symbols.resolver import SymbolResolver
from rig.symbols.table import SymbolTable


class ReferenceResolver(ABC):
    """Generic contract: consume RepositoryIR + SymbolTable, produce a
    ReferenceIndex. No concrete resolver logic belongs here."""

    @abstractmethod
    def resolve(self, repository: RepositoryIR, symbols: SymbolTable) -> ReferenceIndex: ...


_KIND_BY_SYMBOL_TYPE: dict[type, ReferenceKind] = {
    FunctionSymbol: ReferenceKind.FUNCTION,
    TypeSymbol: ReferenceKind.TYPE,
    VariableSymbol: ReferenceKind.VARIABLE,
    ConstantSymbol: ReferenceKind.CONSTANT,
    PackageSymbol: ReferenceKind.PACKAGE,
}


def _symbol_kind_hint(symbol_type: type) -> ReferenceKind | None:
    return _KIND_BY_SYMBOL_TYPE.get(symbol_type)


class IRReferenceResolver(ReferenceResolver):
    """Resolves the IR's `ReferenceUse` facts against the Symbol Table.

    Language-neutral: it consumes only `RepositoryIR` (the reference uses a
    frontend already extracted) and a `SymbolTable`, and never touches a syntax
    tree. All Go-specific syntax handling and predeclared-identifier filtering
    happened in the Go frontend that produced the IR, so nothing here would
    change for a future non-Go frontend.
    """

    def resolve(self, repository: RepositoryIR, symbols: SymbolTable) -> ReferenceIndex:
        index = ReferenceIndex()
        symbol_resolver = SymbolResolver(symbols)
        repo_scope_id = repository_scope_id(repository.id)

        for file in repository.files:
            file_scope = file_scope_id(repository.id, file.relative_path)
            for use in file.reference_uses:
                scope_id = repo_scope_id if use.at_repository_scope else file_scope
                self._emit_reference(file, scope_id, use, symbol_resolver, index)

        return index

    @staticmethod
    def _emit_reference(
        file: File,
        scope_id: str,
        use: ReferenceUse,
        symbol_resolver: SymbolResolver,
        index: ReferenceIndex,
    ) -> None:
        identifier = use.identifier
        location = use.location
        kind = ReferenceKind(use.kind.value)
        rid = reference_id(file.id, kind.value, location.start_byte or 0, location.end_byte or 0)

        symbol = symbol_resolver.resolve(scope_id, identifier)
        if symbol is not None:
            resolved_kind = _symbol_kind_hint(type(symbol)) or kind
            index.add_reference(
                ResolvedReference(
                    id=rid,
                    identifier=identifier,
                    kind=resolved_kind,
                    file_id=file.id,
                    location=location,
                    symbol_id=symbol.id,
                )
            )
            return

        index.add_reference(
            UnresolvedReference(
                id=rid, identifier=identifier, kind=kind, file_id=file.id, location=location
            )
        )
        index.add_diagnostic(
            ReferenceDiagnostic(
                message=f"unresolved {kind.value} reference to {identifier!r}",
                severity=ReferenceDiagnosticSeverity.WARNING,
                location=location,
            )
        )


# Backwards-compatible alias. The reference resolver is now language-neutral
# (it consumes IR reference-use facts, not Go syntax), so this name is retained
# only for API stability; prefer `IRReferenceResolver`.
GoReferenceResolver = IRReferenceResolver
