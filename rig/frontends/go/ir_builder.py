from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

from rig.frontends.go.predeclared import GO_BUILTIN_TYPES, GO_PREDECLARED_IDENTIFIERS
from rig.ir.builder import FileBuildResult, IRBuilder
from rig.ir.diagnostics import IRDiagnostic, IRDiagnosticSeverity
from rig.ir.identifiers import declaration_id, file_id
from rig.ir.model import (
    Declaration,
    DeclaredTypeUses,
    File,
    FunctionDeclaration,
    ImportDeclaration,
    MethodTypeUses,
    QualifiedUse,
    QualifiedUseKind,
    ReferenceUse,
    ReferenceUseKind,
    SourceLocation,
    StructFieldUse,
    TypeDeclaration,
    TypeUse,
    UnsupportedDependencyUse,
    VariableDeclaration,
)
from rig.parsers.treesitter.tree import SyntaxNode, SyntaxTree

# This module is the Go language *frontend*: it is the single place, outside
# the parser package itself, that is allowed to depend on Tree-sitter. It
# consumes a Go syntax tree and produces a language-neutral IR File - both the
# structural declarations and the syntax-extracted semantic facts (reference
# uses, type uses, qualified uses) that the semantic and analysis layers
# resolve. Everything Go-specific (grammar node names, predeclared identifiers,
# the capitalized-means-exported rule) is confined here.

_LANGUAGE_ID = "go"

_TYPE_KIND_BY_NODE_TYPE = {
    "struct_type": "struct",
    "interface_type": "interface",
}


# --- shared syntax helpers ---------------------------------------------------


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


def _text(node: SyntaxNode | None) -> str:
    return node.text.decode("utf-8", errors="replace") if node is not None else ""


def _is_exported(name: str) -> bool:
    return bool(name) and name[0].isupper()


def _string_literal_content(node: SyntaxNode) -> str:
    text = _text(node)
    if len(text) >= 2 and text[0] in '"`' and text[-1] == text[0]:
        return text[1:-1]
    return text


def _iter_specs(
    node: SyntaxNode, spec_types: tuple[str, ...], list_type: str | None = None
) -> list[SyntaxNode]:
    # Go's grammar is inconsistent about grouped declarations: `var (...)`
    # wraps specs in a `var_spec_list`, while `const (...)`/`type (...)` put
    # specs directly under the declaration node. This handles both shapes.
    specs: list[SyntaxNode] = []
    for child in node.named_children():
        if child.type in spec_types:
            specs.append(child)
        elif list_type is not None and child.type == list_type:
            specs.extend(c for c in child.named_children() if c.type in spec_types)
    return specs


def _unwrap_named_type(node: SyntaxNode) -> SyntaxNode | None:
    # Only a bare name, or a single pointer indirection to one, is treated as
    # a directly identifiable named type. Qualified names, slices, maps,
    # arrays, channels, function types, and generic instantiations are not.
    if node.type == "type_identifier":
        return node
    if node.type == "pointer_type":
        inner = next(iter(node.named_children()), None)
        if inner is not None and inner.type == "type_identifier":
            return inner
        return None
    return None


def _unwrap_qualified_type(node: SyntaxNode) -> SyntaxNode | None:
    if node.type == "qualified_type":
        return node
    if node.type == "pointer_type":
        inner = next(iter(node.named_children()), None)
        if inner is not None and inner.type == "qualified_type":
            return inner
    return None


class GoIRBuilder(IRBuilder):
    @property
    def language_id(self) -> str:
        return _LANGUAGE_ID

    def build_file(self, repository_id: str, relative_path: Path, tree: Any) -> FileBuildResult:
        syntax_tree: SyntaxTree = tree
        root = syntax_tree.root
        this_file_id = file_id(repository_id, relative_path)

        package_name: str | None = None
        declarations: list[Declaration] = []
        diagnostics: list[IRDiagnostic] = []
        occurrence_counts: Counter[tuple[str, str]] = Counter()

        def next_id(kind: str, name: str) -> str:
            key = (kind, name)
            occurrence = occurrence_counts[key]
            occurrence_counts[key] += 1
            return declaration_id(this_file_id, kind, name, occurrence)

        for child in root.named_children():
            if child.type == "package_clause":
                package_name = self._extract_package_name(child)

            elif child.type == "import_declaration":
                declarations.extend(
                    self._extract_imports(child, relative_path, next_id, diagnostics)
                )

            elif child.type == "function_declaration":
                declaration = self._extract_function(child, relative_path, next_id)
                if declaration is not None:
                    declarations.append(declaration)
                else:
                    diagnostics.append(
                        IRDiagnostic(
                            message="function declaration missing a name",
                            severity=IRDiagnosticSeverity.WARNING,
                            location=_location(relative_path, child),
                        )
                    )

            elif child.type == "type_declaration":
                declarations.extend(self._extract_types(child, relative_path, next_id))

            elif child.type in ("var_declaration", "const_declaration"):
                declarations.extend(
                    self._extract_variables(
                        child,
                        relative_path,
                        next_id,
                        is_constant=child.type == "const_declaration",
                    )
                )

            # method_declaration, comments, and everything else are
            # intentionally ignored as structural declarations - out of scope
            # for this milestone (their type uses are still extracted below).

        reference_uses = _extract_reference_uses(root, relative_path, package_name)
        declared_type_uses, method_type_uses = _extract_type_uses(root, relative_path, package_name)
        qualified_uses, unsupported_dependency_uses = _extract_dependency_uses(root, relative_path)

        file = File(
            id=this_file_id,
            relative_path=relative_path,
            language_id=_LANGUAGE_ID,
            package_name=package_name,
            declarations=tuple(declarations),
            reference_uses=reference_uses,
            declared_type_uses=declared_type_uses,
            method_type_uses=method_type_uses,
            qualified_uses=qualified_uses,
            unsupported_dependency_uses=unsupported_dependency_uses,
        )
        return FileBuildResult(file=file, diagnostics=tuple(diagnostics))

    @staticmethod
    def _extract_package_name(node: SyntaxNode) -> str | None:
        for child in node.named_children():
            if child.type == "package_identifier":
                return _text(child)
        return None

    @staticmethod
    def _extract_imports(
        node: SyntaxNode,
        relative_path: Path,
        next_id: Callable[[str, str], str],
        diagnostics: list[IRDiagnostic],
    ) -> list[ImportDeclaration]:
        results: list[ImportDeclaration] = []
        for spec in _iter_specs(node, ("import_spec",), "import_spec_list"):
            path_node = spec.child_by_field_name("path")
            if path_node is None:
                diagnostics.append(
                    IRDiagnostic(
                        message="import spec missing a path",
                        severity=IRDiagnosticSeverity.WARNING,
                        location=_location(relative_path, spec),
                    )
                )
                continue

            import_path = _string_literal_content(path_node)
            alias_node = spec.child_by_field_name("name")
            alias = _text(alias_node) if alias_node is not None else None
            name = alias if alias is not None else import_path.rsplit("/", 1)[-1]

            results.append(
                ImportDeclaration(
                    id=next_id("import", name),
                    name=name,
                    location=_location(relative_path, spec),
                    import_path=import_path,
                    alias=alias,
                )
            )
        return results

    @staticmethod
    def _extract_function(
        node: SyntaxNode, relative_path: Path, next_id: Callable[[str, str], str]
    ) -> FunctionDeclaration | None:
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return None

        name = _text(name_node)
        parameters_node = node.child_by_field_name("parameters")
        parameter_count = (
            sum(
                1
                for c in parameters_node.named_children()
                if c.type in ("parameter_declaration", "variadic_parameter_declaration")
            )
            if parameters_node is not None
            else 0
        )

        return FunctionDeclaration(
            id=next_id("function", name),
            name=name,
            location=_location(relative_path, node),
            parameter_count=parameter_count,
            is_exported=_is_exported(name),
        )

    @staticmethod
    def _extract_types(
        node: SyntaxNode, relative_path: Path, next_id: Callable[[str, str], str]
    ) -> list[TypeDeclaration]:
        results: list[TypeDeclaration] = []
        for spec in _iter_specs(node, ("type_spec", "type_alias")):
            name_node = spec.child_by_field_name("name")
            if name_node is None:
                continue

            name = _text(name_node)
            if spec.type == "type_alias":
                underlying_kind = "alias"
            else:
                type_node = spec.child_by_field_name("type")
                underlying_kind = (
                    _TYPE_KIND_BY_NODE_TYPE.get(type_node.type, "other")
                    if type_node is not None
                    else "unknown"
                )

            results.append(
                TypeDeclaration(
                    id=next_id("type", name),
                    name=name,
                    location=_location(relative_path, spec),
                    underlying_kind=underlying_kind,
                    is_exported=_is_exported(name),
                )
            )
        return results

    @staticmethod
    def _extract_variables(
        node: SyntaxNode,
        relative_path: Path,
        next_id: Callable[[str, str], str],
        *,
        is_constant: bool,
    ) -> list[VariableDeclaration]:
        spec_type = "const_spec" if is_constant else "var_spec"
        list_type = None if is_constant else "var_spec_list"

        results: list[VariableDeclaration] = []
        for spec in _iter_specs(node, (spec_type,), list_type):
            for name_node in spec.children_by_field_name("name"):
                name = _text(name_node)
                results.append(
                    VariableDeclaration(
                        id=next_id("variable", name),
                        name=name,
                        location=_location(relative_path, spec),
                        is_constant=is_constant,
                        is_exported=_is_exported(name),
                    )
                )
        return results


# --- reference-use extraction -----------------------------------------------
#
# Relocated verbatim (in traversal shape) from the former GoReferenceResolver,
# but emitting language-neutral ReferenceUse facts rather than resolving them.
# Resolution against the Symbol Table now happens in the neutral references
# layer, which never sees a syntax tree.


def _extract_reference_uses(
    root: SyntaxNode, relative_path: Path, package_name: str | None
) -> tuple[ReferenceUse, ...]:
    uses: list[ReferenceUse] = []

    def emit(
        kind: ReferenceUseKind, node: SyntaxNode, *, at_repository_scope: bool = False
    ) -> None:
        identifier = node.text.decode("utf-8", errors="replace")
        if identifier in GO_PREDECLARED_IDENTIFIERS:
            return
        uses.append(
            ReferenceUse(
                identifier=identifier,
                kind=kind,
                location=_location(relative_path, node),
                at_repository_scope=at_repository_scope,
            )
        )

    def emit_file(kind: ReferenceUseKind, node: SyntaxNode) -> None:
        emit(kind, node)

    for child in root.named_children():
        if child.type == "package_clause":
            name_node = next(
                (c for c in child.named_children() if c.type == "package_identifier"), None
            )
            if name_node is not None:
                emit(ReferenceUseKind.PACKAGE, name_node, at_repository_scope=True)

        elif child.type == "function_declaration":
            parameters = child.child_by_field_name("parameters")
            if parameters is not None:
                _walk_reference_uses(parameters, emit_file)
            result = child.child_by_field_name("result")
            if result is not None:
                _walk_reference_uses(result, emit_file)
            body = child.child_by_field_name("body")
            if body is not None:
                _walk_reference_uses(body, emit_file)

        elif child.type == "type_declaration":
            for spec in child.named_children():
                if spec.type in ("type_alias", "type_spec"):
                    underlying = spec.child_by_field_name("type")
                    if underlying is not None:
                        _walk_reference_uses(underlying, emit_file)

        elif child.type in ("var_declaration", "const_declaration"):
            for spec in _iter_specs(child, ("var_spec", "const_spec"), "var_spec_list"):
                type_node = spec.child_by_field_name("type")
                if type_node is not None:
                    _walk_reference_uses(type_node, emit_file)
                value_node = spec.child_by_field_name("value")
                if value_node is not None:
                    _walk_reference_uses(value_node, emit_file)

        # import_declaration and method_declaration are intentionally skipped -
        # imports and method resolution are out of scope.

    return tuple(uses)


def _walk_reference_uses(
    node: SyntaxNode, emit: Callable[[ReferenceUseKind, SyntaxNode], None]
) -> None:
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
                emit(ReferenceUseKind.FUNCTION, function_node)
            arguments = current.child_by_field_name("arguments")
            if arguments is not None:
                stack.append(arguments)
            continue

        if node_type == "type_identifier":
            emit(ReferenceUseKind.TYPE, current)
            continue

        if node_type == "identifier":
            emit(ReferenceUseKind.VARIABLE, current)
            continue

        stack.extend(current.named_children())


# --- type-use extraction -----------------------------------------------------
#
# Relocated (in traversal shape) from the former TypeRelationshipAnalysis,
# emitting language-neutral DeclaredTypeUses / MethodTypeUses facts. Builtin
# type names are filtered here so the neutral type-relationship analysis never
# needs Go's builtin list; name resolution against the Type Index stays there.


def _named_type_use(relative_path: Path, type_node: SyntaxNode) -> TypeUse | None:
    named = _unwrap_named_type(type_node)
    if named is None:
        return None
    name = _text(named)
    if name in GO_BUILTIN_TYPES:
        return None
    return TypeUse(name=name, location=_location(relative_path, named))


def _extract_type_uses(
    root: SyntaxNode, relative_path: Path, package_name: str | None
) -> tuple[tuple[DeclaredTypeUses, ...], tuple[MethodTypeUses, ...]]:
    declared: list[DeclaredTypeUses] = []
    methods: list[MethodTypeUses] = []

    for child in root.named_children():
        if child.type == "type_declaration":
            declared.extend(_extract_declared_type_uses(child, relative_path, package_name))
        elif child.type == "method_declaration":
            method = _extract_method_type_uses(child, relative_path, package_name)
            if method is not None:
                methods.append(method)

    return tuple(declared), tuple(methods)


def _extract_declared_type_uses(
    type_declaration: SyntaxNode, relative_path: Path, package_name: str | None
) -> list[DeclaredTypeUses]:
    results: list[DeclaredTypeUses] = []
    for spec in type_declaration.named_children():
        if spec.type == "type_spec":
            name_node = spec.child_by_field_name("name")
            underlying = spec.child_by_field_name("type")
            if name_node is None or underlying is None:
                continue

            if spec.child_by_field_name("type_parameters") is not None:
                results.append(
                    DeclaredTypeUses(
                        name=_text(name_node),
                        package=package_name,
                        start_line=spec.start_point.row,
                        is_generic=True,
                        location=_location(relative_path, spec),
                    )
                )
                continue

            if underlying.type == "struct_type":
                results.append(
                    DeclaredTypeUses(
                        name=_text(name_node),
                        package=package_name,
                        start_line=spec.start_point.row,
                        kind="struct",
                        fields=_extract_struct_field_uses(underlying, relative_path),
                    )
                )

        elif spec.type == "type_alias":
            name_node = spec.child_by_field_name("name")
            if name_node is None:
                continue
            underlying = spec.child_by_field_name("type")
            alias_target = (
                _named_type_use(relative_path, underlying) if underlying is not None else None
            )
            results.append(
                DeclaredTypeUses(
                    name=_text(name_node),
                    package=package_name,
                    start_line=spec.start_point.row,
                    kind="alias",
                    alias_target=alias_target,
                )
            )

    return results


def _extract_struct_field_uses(
    struct_type: SyntaxNode, relative_path: Path
) -> tuple[StructFieldUse, ...]:
    field_list = next(
        (c for c in struct_type.named_children() if c.type == "field_declaration_list"), None
    )
    if field_list is None:
        return ()

    fields: list[StructFieldUse] = []
    for field_decl in field_list.named_children():
        if field_decl.type != "field_declaration":
            continue
        type_node = field_decl.child_by_field_name("type")
        if type_node is None:
            continue
        target = _named_type_use(relative_path, type_node)
        if target is None:
            continue
        is_embedded = field_decl.child_by_field_name("name") is None
        fields.append(StructFieldUse(is_embedded=is_embedded, target=target))
    return tuple(fields)


def _extract_method_type_uses(
    method: SyntaxNode, relative_path: Path, package_name: str | None
) -> MethodTypeUses | None:
    receiver = method.child_by_field_name("receiver")
    if receiver is None:
        return None
    receiver_decl = next(iter(receiver.named_children()), None)
    if receiver_decl is None:
        return None
    receiver_type_node = receiver_decl.child_by_field_name("type")
    if receiver_type_node is None:
        return None

    named = _unwrap_named_type(receiver_type_node)
    if named is None:
        # Preserve the "method receiver is not a simple named type" diagnostic:
        # emit a method whose receiver name is unresolved.
        return MethodTypeUses(
            receiver=TypeUse(name=None, location=_location(relative_path, receiver_type_node)),
            package=package_name,
        )
    if _text(named) in GO_BUILTIN_TYPES:
        # A method on a builtin cannot name a repository type; the former
        # analysis silently skipped it (resolve returned None, no diagnostic).
        return None

    receiver_use = TypeUse(name=_text(named), location=_location(relative_path, named))

    parameters: list[TypeUse] = []
    parameters_node = method.child_by_field_name("parameters")
    if parameters_node is not None:
        for parameter in parameters_node.named_children():
            if parameter.type != "parameter_declaration":
                continue
            type_node = parameter.child_by_field_name("type")
            if type_node is None:
                continue
            target = _named_type_use(relative_path, type_node)
            if target is not None:
                parameters.append(target)

    returns: list[TypeUse] = []
    result = method.child_by_field_name("result")
    if result is not None:
        result_nodes = (
            [
                c.child_by_field_name("type")
                for c in result.named_children()
                if c.type == "parameter_declaration"
            ]
            if result.type == "parameter_list"
            else [result]
        )
        for type_node in result_nodes:
            if type_node is None:
                continue
            target = _named_type_use(relative_path, type_node)
            if target is not None:
                returns.append(target)

    return MethodTypeUses(
        receiver=receiver_use,
        package=package_name,
        parameters=tuple(parameters),
        returns=tuple(returns),
    )


# --- dependency-use extraction ----------------------------------------------
#
# Relocated (in traversal shape) from the former DependencyAnalysis. Emits
# language-neutral QualifiedUse facts (module-qualified type/call references)
# plus markers for unsupported dependency sources. Qualifier -> import ->
# package resolution stays in the neutral dependency analysis, which reads the
# IR's ImportDeclaration objects rather than a syntax tree.


def _extract_dependency_uses(
    root: SyntaxNode, relative_path: Path
) -> tuple[tuple[QualifiedUse, ...], tuple[UnsupportedDependencyUse, ...]]:
    qualified: list[QualifiedUse] = []
    unsupported: list[UnsupportedDependencyUse] = []

    # Cross-package type usage: only exported type declarations count as a
    # dependency source, mirroring the former analysis.
    for child in root.named_children():
        if child.type == "type_declaration":
            _extract_type_dependency_uses(child, relative_path, qualified, unsupported)

    # Cross-package calls: a full-tree walk for `pkg.Func(...)` selector calls.
    stack: list[SyntaxNode] = [root]
    while stack:
        current = stack.pop()
        if current.type == "call_expression":
            function_node = current.child_by_field_name("function")
            if function_node is not None:
                if function_node.type == "selector_expression":
                    operand = function_node.child_by_field_name("operand")
                    if operand is not None and operand.type == "identifier":
                        qualified.append(
                            QualifiedUse(
                                qualifier=_text(operand),
                                kind=QualifiedUseKind.CALL,
                                location=_location(relative_path, current),
                            )
                        )
                elif function_node.type != "identifier":
                    unsupported.append(
                        UnsupportedDependencyUse(
                            reason="unrecognized_call",
                            name=None,
                            location=_location(relative_path, current),
                        )
                    )
        stack.extend(current.named_children())

    return tuple(qualified), tuple(unsupported)


def _extract_type_dependency_uses(
    type_declaration: SyntaxNode,
    relative_path: Path,
    qualified: list[QualifiedUse],
    unsupported: list[UnsupportedDependencyUse],
) -> None:
    for spec in type_declaration.named_children():
        if spec.type == "type_spec":
            name_node = spec.child_by_field_name("name")
            underlying = spec.child_by_field_name("type")
            if name_node is None or underlying is None:
                continue

            if spec.child_by_field_name("type_parameters") is not None:
                unsupported.append(
                    UnsupportedDependencyUse(
                        reason="generic_type",
                        name=_text(name_node),
                        location=_location(relative_path, spec),
                    )
                )
                continue

            if not _is_exported(_text(name_node)):
                continue

            if underlying.type == "struct_type":
                _extract_struct_field_dependency_uses(underlying, relative_path, qualified)
            else:
                _append_qualified_type_use(underlying, relative_path, qualified)

        elif spec.type == "type_alias":
            name_node = spec.child_by_field_name("name")
            underlying = spec.child_by_field_name("type")
            if name_node is None or underlying is None:
                continue
            if not _is_exported(_text(name_node)):
                continue
            _append_qualified_type_use(underlying, relative_path, qualified)


def _extract_struct_field_dependency_uses(
    struct_type: SyntaxNode, relative_path: Path, qualified: list[QualifiedUse]
) -> None:
    field_list = next(
        (c for c in struct_type.named_children() if c.type == "field_declaration_list"), None
    )
    if field_list is None:
        return
    for field_declaration in field_list.named_children():
        if field_declaration.type != "field_declaration":
            continue
        type_node = field_declaration.child_by_field_name("type")
        if type_node is None:
            continue
        _append_qualified_type_use(type_node, relative_path, qualified)


def _append_qualified_type_use(
    type_node: SyntaxNode, relative_path: Path, qualified: list[QualifiedUse]
) -> None:
    qualified_type = _unwrap_qualified_type(type_node)
    if qualified_type is None:
        return
    package_node = qualified_type.child_by_field_name("package")
    if package_node is None:
        return
    qualified.append(
        QualifiedUse(
            qualifier=_text(package_node),
            kind=QualifiedUseKind.TYPE,
            location=_location(relative_path, qualified_type),
        )
    )
