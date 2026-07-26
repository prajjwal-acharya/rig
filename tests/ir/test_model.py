from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from rig.ir.model import (
    DeclarationKind,
    File,
    FunctionDeclaration,
    ImportDeclaration,
    Package,
    SourceLocation,
    TypeDeclaration,
    VariableDeclaration,
)


def _location() -> SourceLocation:
    return SourceLocation(
        relative_path=Path("main.go"),
        start_line=0,
        start_column=0,
        end_line=0,
        end_column=10,
    )


def test_function_declaration_kind_is_set_automatically() -> None:
    declaration = FunctionDeclaration(id="d1", name="Foo", location=_location())

    assert declaration.kind == DeclarationKind.FUNCTION


def test_type_declaration_kind_is_set_automatically() -> None:
    declaration = TypeDeclaration(id="d1", name="Widget", location=_location())

    assert declaration.kind == DeclarationKind.TYPE


def test_variable_declaration_kind_is_set_automatically() -> None:
    declaration = VariableDeclaration(id="d1", name="x", location=_location())

    assert declaration.kind == DeclarationKind.VARIABLE


def test_import_declaration_kind_is_set_automatically() -> None:
    declaration = ImportDeclaration(id="d1", name="fmt", location=_location())

    assert declaration.kind == DeclarationKind.IMPORT


def test_declaration_kind_cannot_be_overridden_at_construction() -> None:
    with pytest.raises(TypeError):
        FunctionDeclaration(  # type: ignore[call-arg]
            id="d1", name="Foo", kind=DeclarationKind.TYPE, location=_location()
        )


def test_declarations_are_immutable() -> None:
    declaration = FunctionDeclaration(id="d1", name="Foo", location=_location())

    with pytest.raises(dataclasses.FrozenInstanceError):
        declaration.name = "Bar"  # type: ignore[misc]


def test_function_declaration_defaults() -> None:
    declaration = FunctionDeclaration(id="d1", name="Foo", location=_location())

    assert declaration.parameter_count == 0
    assert declaration.is_exported is False


def test_variable_declaration_defaults() -> None:
    declaration = VariableDeclaration(id="d1", name="x", location=_location())

    assert declaration.is_constant is False
    assert declaration.is_exported is False


def test_import_declaration_defaults() -> None:
    declaration = ImportDeclaration(id="d1", name="fmt", location=_location())

    assert declaration.import_path == ""
    assert declaration.alias is None


def test_file_declarations_default_to_empty() -> None:
    file = File(id="f1", relative_path=Path("main.go"), language_id="go")

    assert file.declarations == ()
    assert file.package_name is None


def test_file_is_immutable() -> None:
    file = File(id="f1", relative_path=Path("main.go"), language_id="go")

    with pytest.raises(dataclasses.FrozenInstanceError):
        file.language_id = "python"  # type: ignore[misc]


def test_package_defaults() -> None:
    package = Package(id="p1", name="mypkg")

    assert package.file_ids == ()


def test_source_location_holds_optional_byte_range() -> None:
    location = SourceLocation(
        relative_path=Path("main.go"),
        start_line=1,
        start_column=0,
        end_line=1,
        end_column=5,
    )

    assert location.start_byte is None
    assert location.end_byte is None
