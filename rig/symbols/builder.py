from __future__ import annotations

from collections import Counter

from rig.ir.model import (
    Declaration,
    File,
    FunctionDeclaration,
    ImportDeclaration,
    Package,
    TypeDeclaration,
    VariableDeclaration,
)
from rig.ir.repository import RepositoryIR
from rig.symbols.diagnostics import SymbolDiagnostic, SymbolDiagnosticSeverity
from rig.symbols.identifiers import (
    file_scope_id,
    package_scope_id,
    package_symbol_id,
    repository_scope_id,
    symbol_id,
)
from rig.symbols.model import (
    ConstantSymbol,
    FunctionSymbol,
    PackageSymbol,
    Symbol,
    TypeSymbol,
    VariableSymbol,
)
from rig.symbols.scope import FileScope, PackageScope, RepositoryScope
from rig.symbols.table import SymbolTable


def _build_symbol(sid: str, declaration: Declaration) -> Symbol:
    if isinstance(declaration, FunctionDeclaration):
        return FunctionSymbol(
            id=sid,
            name=declaration.name,
            declaration_id=declaration.id,
            is_exported=declaration.is_exported,
            parameter_count=declaration.parameter_count,
        )
    if isinstance(declaration, TypeDeclaration):
        return TypeSymbol(
            id=sid,
            name=declaration.name,
            declaration_id=declaration.id,
            is_exported=declaration.is_exported,
            underlying_kind=declaration.underlying_kind,
        )
    if isinstance(declaration, VariableDeclaration):
        symbol_cls = ConstantSymbol if declaration.is_constant else VariableSymbol
        return symbol_cls(
            id=sid,
            name=declaration.name,
            declaration_id=declaration.id,
            is_exported=declaration.is_exported,
        )
    raise TypeError(f"unsupported declaration type: {type(declaration).__name__}")


def _index_file(
    table: SymbolTable,
    file: File,
    *,
    scope_id: str,
    occurrence_counts: Counter[tuple[str, str]],
    package_name: str | None,
    emit_duplicate_diagnostics: bool,
) -> dict[str, str]:
    file_symbols: dict[str, str] = {}

    for declaration in file.declarations:
        if isinstance(declaration, ImportDeclaration):
            continue  # imports are out of scope for symbol resolution here

        key = (declaration.kind.value, declaration.name)
        occurrence = occurrence_counts[key]
        occurrence_counts[key] += 1

        if occurrence > 0 and emit_duplicate_diagnostics:
            table.add_diagnostic(
                SymbolDiagnostic(
                    message=(
                        f"duplicate {declaration.kind.value} symbol "
                        f"{declaration.name!r} in package {package_name!r}"
                    ),
                    severity=SymbolDiagnosticSeverity.WARNING,
                )
            )

        sid = symbol_id(scope_id, declaration.kind.value, declaration.name, occurrence)
        table.add_symbol(_build_symbol(sid, declaration))
        file_symbols[declaration.name] = sid

    return file_symbols


class GoSymbolTableBuilder:
    """Builds a SymbolTable from a RepositoryIR.

    Named for consistency with this project's per-language builder
    convention (GoIRBuilder, GoTreeSitterParser, ...), but contains no
    Go-specific logic: RepositoryIR's declaration model is already
    language-independent, so nothing here would need to change to index a
    repository produced by a future non-Go IR builder.
    """

    def build(self, repository: RepositoryIR) -> SymbolTable:
        table = SymbolTable()
        files_by_id = {file.id: file for file in repository.files}
        repo_scope_id = repository_scope_id(repository.id)
        repository_symbols: dict[str, str] = {}

        for package in sorted(repository.packages, key=lambda p: p.name):
            self._index_package(table, repository, package, files_by_id, repo_scope_id)
            repository_symbols[package.name] = package_symbol_id(repository.id, package.name)

        packaged_file_ids = {
            file_id for package in repository.packages for file_id in package.file_ids
        }
        orphan_files = [f for f in repository.files if f.id not in packaged_file_ids]
        if orphan_files:
            # One shared counter across every orphan file: they all share the
            # repository scope's namespace, so occurrence disambiguation must
            # be shared too - otherwise two orphan files independently
            # declaring the same name would compute identical symbol ids.
            orphan_occurrence_counts: Counter[tuple[str, str]] = Counter()
            for file in orphan_files:
                self._index_orphan_file(
                    table, repository, file, repo_scope_id, orphan_occurrence_counts
                )

        table.add_scope(
            RepositoryScope(
                id=repo_scope_id,
                name=repository.root.name,
                parent_id=None,
                symbol_ids=tuple(sorted(repository_symbols.items())),
            )
        )

        return table

    @staticmethod
    def _index_package(
        table: SymbolTable,
        repository: RepositoryIR,
        package: Package,
        files_by_id: dict[str, File],
        repo_scope_id: str,
    ) -> None:
        pkg_scope_id = package_scope_id(repository.id, package.name)

        table.add_symbol(
            PackageSymbol(
                id=package_symbol_id(repository.id, package.name),
                name=package.name,
                declaration_id=package.id,
                file_ids=package.file_ids,
            )
        )

        package_symbols: dict[str, str] = {}
        occurrence_counts: Counter[tuple[str, str]] = Counter()

        for file_id in package.file_ids:
            file = files_by_id[file_id]
            file_symbols = _index_file(
                table,
                file,
                scope_id=pkg_scope_id,
                occurrence_counts=occurrence_counts,
                package_name=package.name,
                emit_duplicate_diagnostics=True,
            )
            table.add_scope(
                FileScope(
                    id=file_scope_id(repository.id, file.relative_path),
                    name=file.relative_path.as_posix(),
                    parent_id=pkg_scope_id,
                    symbol_ids=tuple(sorted(file_symbols.items())),
                )
            )
            package_symbols.update(file_symbols)

        table.add_scope(
            PackageScope(
                id=pkg_scope_id,
                name=package.name,
                parent_id=repo_scope_id,
                symbol_ids=tuple(sorted(package_symbols.items())),
            )
        )

    @staticmethod
    def _index_orphan_file(
        table: SymbolTable,
        repository: RepositoryIR,
        file: File,
        repo_scope_id: str,
        occurrence_counts: Counter[tuple[str, str]],
    ) -> None:
        file_symbols = _index_file(
            table,
            file,
            scope_id=repo_scope_id,
            occurrence_counts=occurrence_counts,
            package_name=None,
            emit_duplicate_diagnostics=False,
        )
        table.add_scope(
            FileScope(
                id=file_scope_id(repository.id, file.relative_path),
                name=file.relative_path.as_posix(),
                parent_id=repo_scope_id,
                symbol_ids=tuple(sorted(file_symbols.items())),
            )
        )
