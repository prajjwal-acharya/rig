from __future__ import annotations

from pathlib import Path

from rig.ir.builders.go import GoIRBuilder
from rig.ir.identifiers import repository_id
from rig.ir.model import (
    FunctionDeclaration,
    ImportDeclaration,
    TypeDeclaration,
    VariableDeclaration,
)
from tests.ir.conftest import go_tree

REPO_ID = repository_id(Path("/repos/example"))


def _build(source: str, relative_path: str = "main.go"):
    builder = GoIRBuilder()
    return builder.build_file(REPO_ID, Path(relative_path), go_tree(source))


def test_language_id_is_go() -> None:
    assert GoIRBuilder().language_id == "go"


def test_extracts_package_name() -> None:
    result = _build("package mypkg\n")

    assert result.file.package_name == "mypkg"


def test_extracts_plain_import() -> None:
    result = _build('package p\n\nimport "fmt"\n')

    imports = [d for d in result.file.declarations if isinstance(d, ImportDeclaration)]
    assert len(imports) == 1
    assert imports[0].import_path == "fmt"
    assert imports[0].name == "fmt"
    assert imports[0].alias is None


def test_extracts_aliased_import() -> None:
    result = _build('package p\n\nimport f "fmt"\n')

    imports = [d for d in result.file.declarations if isinstance(d, ImportDeclaration)]
    assert imports[0].alias == "f"
    assert imports[0].name == "f"
    assert imports[0].import_path == "fmt"


def test_extracts_blank_import() -> None:
    result = _build('package p\n\nimport _ "net/http/pprof"\n')

    imports = [d for d in result.file.declarations if isinstance(d, ImportDeclaration)]
    assert imports[0].alias == "_"
    assert imports[0].import_path == "net/http/pprof"


def test_extracts_grouped_imports() -> None:
    source = 'package p\n\nimport (\n\t"fmt"\n\t"os"\n)\n'
    result = _build(source)

    imports = [d for d in result.file.declarations if isinstance(d, ImportDeclaration)]
    assert {i.import_path for i in imports} == {"fmt", "os"}


def test_import_name_defaults_to_last_path_segment() -> None:
    result = _build('package p\n\nimport "k8s.io/client-go/kubernetes"\n')

    imports = [d for d in result.file.declarations if isinstance(d, ImportDeclaration)]
    assert imports[0].name == "kubernetes"


def test_extracts_exported_function_with_parameters() -> None:
    result = _build("package p\n\nfunc DoSomething(a int, b string) error {\n\treturn nil\n}\n")

    functions = [d for d in result.file.declarations if isinstance(d, FunctionDeclaration)]
    assert len(functions) == 1
    assert functions[0].name == "DoSomething"
    assert functions[0].is_exported is True
    assert functions[0].parameter_count == 2


def test_extracts_unexported_function_with_no_parameters() -> None:
    result = _build("package p\n\nfunc helper() {}\n")

    functions = [d for d in result.file.declarations if isinstance(d, FunctionDeclaration)]
    assert functions[0].name == "helper"
    assert functions[0].is_exported is False
    assert functions[0].parameter_count == 0


def test_method_declarations_are_skipped() -> None:
    result = _build("package p\n\nfunc (w *Widget) Method() {}\n")

    functions = [d for d in result.file.declarations if isinstance(d, FunctionDeclaration)]
    assert functions == []


def test_extracts_struct_type_declaration() -> None:
    result = _build("package p\n\ntype Widget struct {\n\tName string\n}\n")

    types = [d for d in result.file.declarations if isinstance(d, TypeDeclaration)]
    assert types[0].name == "Widget"
    assert types[0].underlying_kind == "struct"
    assert types[0].is_exported is True


def test_extracts_interface_type_declaration() -> None:
    result = _build("package p\n\ntype Reader interface {\n\tRead() error\n}\n")

    types = [d for d in result.file.declarations if isinstance(d, TypeDeclaration)]
    assert types[0].name == "Reader"
    assert types[0].underlying_kind == "interface"


def test_extracts_type_alias() -> None:
    result = _build("package p\n\ntype Alias = string\n")

    types = [d for d in result.file.declarations if isinstance(d, TypeDeclaration)]
    assert types[0].name == "Alias"
    assert types[0].underlying_kind == "alias"


def test_extracts_defined_type_that_is_not_struct_or_interface() -> None:
    result = _build("package p\n\ntype UserID int\n")

    types = [d for d in result.file.declarations if isinstance(d, TypeDeclaration)]
    assert types[0].name == "UserID"
    assert types[0].underlying_kind == "other"


def test_extracts_grouped_type_declarations() -> None:
    source = "package p\n\ntype (\n\tFoo struct{}\n\tBar = int\n)\n"
    result = _build(source)

    types = [d for d in result.file.declarations if isinstance(d, TypeDeclaration)]
    assert {t.name for t in types} == {"Foo", "Bar"}


def test_unexported_type_is_not_exported() -> None:
    result = _build("package p\n\ntype widget struct{}\n")

    types = [d for d in result.file.declarations if isinstance(d, TypeDeclaration)]
    assert types[0].is_exported is False


def test_extracts_single_variable_declaration() -> None:
    result = _build("package p\n\nvar GlobalCounter int\n")

    variables = [d for d in result.file.declarations if isinstance(d, VariableDeclaration)]
    assert variables[0].name == "GlobalCounter"
    assert variables[0].is_constant is False
    assert variables[0].is_exported is True


def test_extracts_multiple_names_from_one_var_spec() -> None:
    result = _build("package p\n\nvar x, y = 1, 2\n")

    variables = [d for d in result.file.declarations if isinstance(d, VariableDeclaration)]
    assert {v.name for v in variables} == {"x", "y"}
    assert all(not v.is_constant for v in variables)


def test_extracts_grouped_variable_declarations() -> None:
    source = "package p\n\nvar (\n\tx int\n\ty string\n)\n"
    result = _build(source)

    variables = [d for d in result.file.declarations if isinstance(d, VariableDeclaration)]
    assert {v.name for v in variables} == {"x", "y"}


def test_extracts_single_constant() -> None:
    result = _build("package p\n\nconst MaxRetries = 3\n")

    variables = [d for d in result.file.declarations if isinstance(d, VariableDeclaration)]
    assert variables[0].name == "MaxRetries"
    assert variables[0].is_constant is True
    assert variables[0].is_exported is True


def test_extracts_grouped_constants() -> None:
    source = "package p\n\nconst (\n\tA = iota\n\tB\n)\n"
    result = _build(source)

    variables = [d for d in result.file.declarations if isinstance(d, VariableDeclaration)]
    assert {v.name for v in variables} == {"A", "B"}
    assert all(v.is_constant for v in variables)


def test_source_locations_are_populated() -> None:
    result = _build("package p\n\nfunc Foo() {}\n")

    functions = [d for d in result.file.declarations if isinstance(d, FunctionDeclaration)]
    location = functions[0].location
    assert location.relative_path == Path("main.go")
    assert location.start_line == 2
    assert location.start_byte is not None
    assert location.end_byte is not None
    assert location.end_byte > location.start_byte


def test_declaration_ids_are_deterministic_across_identical_builds() -> None:
    source = "package p\n\nfunc Foo() {}\n"

    first = _build(source)
    second = _build(source)

    first_ids = [d.id for d in first.file.declarations]
    second_ids = [d.id for d in second.file.declarations]
    assert first_ids == second_ids


def test_duplicate_names_in_one_file_get_distinct_ids() -> None:
    result = _build("package p\n\nfunc Foo() {}\n\nfunc Foo() {}\n")

    functions = [d for d in result.file.declarations if isinstance(d, FunctionDeclaration)]
    assert len(functions) == 2
    assert functions[0].id != functions[1].id


def test_empty_file_produces_no_declarations_and_no_crash() -> None:
    result = _build("")

    assert result.file.package_name is None
    assert result.file.declarations == ()
    assert result.diagnostics == ()


def test_malformed_syntax_tree_does_not_raise() -> None:
    result = _build("this is not valid go {{{ func")

    assert result.file.declarations == ()


def test_file_id_reflects_relative_path() -> None:
    from rig.ir.identifiers import file_id

    result = _build("package p\n", relative_path="pkg/main.go")

    assert result.file.id == file_id(REPO_ID, Path("pkg/main.go"))


def test_language_id_on_file_is_go() -> None:
    result = _build("package p\n")

    assert result.file.language_id == "go"
