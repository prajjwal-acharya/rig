from rig.symbols.builder import GoSymbolTableBuilder
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
    SymbolKind,
    TypeSymbol,
    VariableSymbol,
)
from rig.symbols.resolver import SymbolResolver
from rig.symbols.scope import FileScope, PackageScope, RepositoryScope, Scope, ScopeKind
from rig.symbols.table import DuplicateScopeError, DuplicateSymbolError, SymbolTable
from rig.symbols.visitor import SymbolVisitor, iter_scopes, iter_symbols

__all__ = [
    "ConstantSymbol",
    "DuplicateScopeError",
    "DuplicateSymbolError",
    "FileScope",
    "FunctionSymbol",
    "GoSymbolTableBuilder",
    "PackageScope",
    "PackageSymbol",
    "RepositoryScope",
    "Scope",
    "ScopeKind",
    "Symbol",
    "SymbolDiagnostic",
    "SymbolDiagnosticSeverity",
    "SymbolKind",
    "SymbolResolver",
    "SymbolTable",
    "SymbolVisitor",
    "TypeSymbol",
    "VariableSymbol",
    "file_scope_id",
    "iter_scopes",
    "iter_symbols",
    "package_scope_id",
    "package_symbol_id",
    "repository_scope_id",
    "symbol_id",
]
