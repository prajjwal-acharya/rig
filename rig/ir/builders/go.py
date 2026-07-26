from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

from rig.ir.builder import FileBuildResult, IRBuilder
from rig.ir.diagnostics import IRDiagnostic, IRDiagnosticSeverity
from rig.ir.identifiers import declaration_id, file_id
from rig.ir.model import (
    Declaration,
    File,
    FunctionDeclaration,
    ImportDeclaration,
    SourceLocation,
    TypeDeclaration,
    VariableDeclaration,
)
from rig.parsers.treesitter.tree import SyntaxNode, SyntaxTree

_LANGUAGE_ID = "go"

_TYPE_KIND_BY_NODE_TYPE = {
    "struct_type": "struct",
    "interface_type": "interface",
}


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
            # intentionally ignored - out of scope for this milestone.

        file = File(
            id=this_file_id,
            relative_path=relative_path,
            language_id=_LANGUAGE_ID,
            package_name=package_name,
            declarations=tuple(declarations),
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
