from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from pathlib import Path

from rig.ir.model import File, SourceLocation
from rig.ir.repository import RepositoryIR
from rig.parsers.pipeline import ParsedFile
from rig.parsers.treesitter.tree import SyntaxNode, SyntaxTree
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


# Go's predeclared identifiers (builtin functions/types/constants). These are
# never repository declarations, so they are skipped entirely - neither
# resolved nor reported as unresolved, to avoid flooding diagnostics with
# expected, harmless usages of ordinary language builtins.
_GO_PREDECLARED = frozenset(
    {
        "any",
        "bool",
        "byte",
        "complex64",
        "complex128",
        "error",
        "float32",
        "float64",
        "int",
        "int8",
        "int16",
        "int32",
        "int64",
        "rune",
        "string",
        "uint",
        "uint8",
        "uint16",
        "uint32",
        "uint64",
        "uintptr",
        "true",
        "false",
        "iota",
        "nil",
        "append",
        "cap",
        "close",
        "complex",
        "copy",
        "delete",
        "imag",
        "len",
        "make",
        "new",
        "panic",
        "print",
        "println",
        "real",
        "recover",
        "min",
        "max",
        "clear",
    }
)

_KIND_BY_SYMBOL_TYPE: dict[type, ReferenceKind] = {
    FunctionSymbol: ReferenceKind.FUNCTION,
    TypeSymbol: ReferenceKind.TYPE,
    VariableSymbol: ReferenceKind.VARIABLE,
    ConstantSymbol: ReferenceKind.CONSTANT,
    PackageSymbol: ReferenceKind.PACKAGE,
}


def _symbol_kind_hint(symbol_type: type) -> ReferenceKind | None:
    return _KIND_BY_SYMBOL_TYPE.get(symbol_type)


class GoReferenceResolver(ReferenceResolver):
    """Resolves identifier/call/type references within Go source.

    Requires the parsed syntax trees (not just RepositoryIR) because
    function bodies and declaration type annotations are intentionally
    absent from the IR - Tree-sitter access is confined entirely to this
    class and never leaks into the generic ReferenceResolver contract,
    ReferenceIndex, or reference model.
    """

    def __init__(self, parsed_files: Sequence[ParsedFile]) -> None:
        self._trees_by_path: dict[Path, SyntaxTree] = {
            parsed.file.relative_path: parsed.result.syntax_tree
            for parsed in parsed_files
            if parsed.result.success and parsed.result.syntax_tree is not None
        }

    def resolve(self, repository: RepositoryIR, symbols: SymbolTable) -> ReferenceIndex:
        index = ReferenceIndex()
        symbol_resolver = SymbolResolver(symbols)

        for file in repository.files:
            tree = self._trees_by_path.get(file.relative_path)
            if tree is None:
                continue
            self._resolve_file(repository, file, tree, symbol_resolver, index)

        return index

    def _resolve_file(
        self,
        repository: RepositoryIR,
        file: File,
        tree: SyntaxTree,
        symbol_resolver: SymbolResolver,
        index: ReferenceIndex,
    ) -> None:
        scope_id = file_scope_id(repository.id, file.relative_path)
        root = tree.root

        def emit(kind: ReferenceKind, node: SyntaxNode) -> None:
            self._emit_reference(file, scope_id, kind, node, symbol_resolver, index)

        for child in root.named_children():
            if child.type == "package_clause":
                name_node = next(
                    (c for c in child.named_children() if c.type == "package_identifier"), None
                )
                if name_node is not None:
                    self._emit_reference(
                        file,
                        repository_scope_id(repository.id),
                        ReferenceKind.PACKAGE,
                        name_node,
                        symbol_resolver,
                        index,
                    )

            elif child.type == "function_declaration":
                parameters = child.child_by_field_name("parameters")
                if parameters is not None:
                    self._walk(parameters, emit)
                result = child.child_by_field_name("result")
                if result is not None:
                    self._walk(result, emit)
                body = child.child_by_field_name("body")
                if body is not None:
                    self._walk(body, emit)

            elif child.type == "type_declaration":
                for spec in child.named_children():
                    if spec.type in ("type_alias", "type_spec"):
                        underlying = spec.child_by_field_name("type")
                        if underlying is not None:
                            self._walk(underlying, emit)

            elif child.type in ("var_declaration", "const_declaration"):
                for spec in _iter_specs(child, ("var_spec", "const_spec"), "var_spec_list"):
                    type_node = spec.child_by_field_name("type")
                    if type_node is not None:
                        self._walk(type_node, emit)
                    value_node = spec.child_by_field_name("value")
                    if value_node is not None:
                        self._walk(value_node, emit)

            # import_declaration and method_declaration are intentionally
            # skipped - imports and method resolution are out of scope.

    def _walk(self, node: SyntaxNode, emit: Callable[[ReferenceKind, SyntaxNode], None]) -> None:
        stack: list[SyntaxNode] = [node]
        while stack:
            current = stack.pop()
            node_type = current.type

            if node_type == "selector_expression":
                # No import or method resolution: qualified access (pkg.Foo,
                # x.Method, x.Field) is entirely out of scope this milestone.
                continue

            if node_type == "short_var_declaration":
                right = current.child_by_field_name("right")
                if right is not None:
                    stack.append(right)
                continue  # skip "left" - these are new local bindings

            if node_type in ("var_spec", "const_spec"):
                name_nodes = set(current.children_by_field_name("name"))
                for child in current.named_children():
                    if child not in name_nodes:
                        stack.append(child)
                continue

            if node_type == "call_expression":
                function_node = current.child_by_field_name("function")
                if function_node is not None and function_node.type == "identifier":
                    emit(ReferenceKind.FUNCTION, function_node)
                arguments = current.child_by_field_name("arguments")
                if arguments is not None:
                    stack.append(arguments)
                continue

            if node_type == "type_identifier":
                emit(ReferenceKind.TYPE, current)
                continue

            if node_type == "identifier":
                emit(ReferenceKind.VARIABLE, current)
                continue

            stack.extend(current.named_children())

    def _emit_reference(
        self,
        file: File,
        scope_id: str,
        kind: ReferenceKind,
        node: SyntaxNode,
        symbol_resolver: SymbolResolver,
        index: ReferenceIndex,
    ) -> None:
        identifier = node.text.decode("utf-8", errors="replace")
        if identifier in _GO_PREDECLARED:
            return

        location = _location(file.relative_path, node)
        rid = reference_id(file.id, kind.value, node.start_byte, node.end_byte)

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


def _location(relative_path: Path, node: SyntaxNode) -> SourceLocation:
    return SourceLocation(
        relative_path=relative_path,
        start_line=node.start_point.row,
        start_column=node.start_point.column,
        end_line=node.end_point.row,
        end_column=node.end_point.column,
        start_byte=node.start_byte,
        end_byte=node.end_byte,
    )


def _iter_specs(
    node: SyntaxNode, spec_types: tuple[str, ...], list_type: str | None = None
) -> list[SyntaxNode]:
    specs: list[SyntaxNode] = []
    for child in node.named_children():
        if child.type in spec_types:
            specs.append(child)
        elif list_type is not None and child.type == list_type:
            specs.extend(c for c in child.named_children() if c.type in spec_types)
    return specs
