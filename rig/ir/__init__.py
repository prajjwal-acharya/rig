from rig.ir.builder import DuplicateIRBuilderError, FileBuildResult, IRBuilder, IRBuilderRegistry
from rig.ir.diagnostics import IRDiagnostic, IRDiagnosticSeverity
from rig.ir.identifiers import declaration_id, file_id, package_id, repository_id
from rig.ir.model import (
    Declaration,
    DeclarationKind,
    File,
    FunctionDeclaration,
    ImportDeclaration,
    Package,
    SourceLocation,
    TypeDeclaration,
    VariableDeclaration,
)
from rig.ir.repository import RepositoryIR, RepositoryIRBuilder, build_repository_ir
from rig.ir.visitor import IRVisitor, iter_declarations, iter_files

__all__ = [
    "Declaration",
    "DeclarationKind",
    "DuplicateIRBuilderError",
    "File",
    "FileBuildResult",
    "FunctionDeclaration",
    "IRBuilder",
    "IRBuilderRegistry",
    "IRDiagnostic",
    "IRDiagnosticSeverity",
    "IRVisitor",
    "ImportDeclaration",
    "Package",
    "RepositoryIR",
    "RepositoryIRBuilder",
    "SourceLocation",
    "TypeDeclaration",
    "VariableDeclaration",
    "build_repository_ir",
    "declaration_id",
    "file_id",
    "iter_declarations",
    "iter_files",
    "package_id",
    "repository_id",
]
