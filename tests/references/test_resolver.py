from __future__ import annotations

from rig.references.model import ReferenceKind, ResolvedReference, UnresolvedReference
from rig.references.resolver import GoReferenceResolver
from tests.references.conftest import build_repository_and_symbols


def _resolve(sources: dict[str, str]):
    repository, symbols, parsed_files = build_repository_and_symbols(sources)
    index = GoReferenceResolver(parsed_files).resolve(repository, symbols)
    return repository, symbols, index


def test_function_call_is_resolved() -> None:
    _, _, index = _resolve(
        {"a.go": "package p\n\nfunc helper() {}\n\nfunc Foo() {\n\thelper()\n}\n"}
    )

    resolved = [
        r
        for r in index.references()
        if isinstance(r, ResolvedReference) and r.identifier == "helper"
    ]
    assert len(resolved) == 1
    assert resolved[0].kind == ReferenceKind.FUNCTION


def test_function_call_across_files_in_same_package_is_resolved() -> None:
    _, _, index = _resolve(
        {
            "a.go": "package p\n\nfunc Foo() {\n\tBar()\n}\n",
            "b.go": "package p\n\nfunc Bar() {}\n",
        }
    )

    resolved = [
        r for r in index.references() if isinstance(r, ResolvedReference) and r.identifier == "Bar"
    ]
    assert len(resolved) == 1


def test_package_level_variable_reference_is_resolved() -> None:
    _, _, index = _resolve(
        {"a.go": "package p\n\nvar Counter int\n\nfunc Foo() int {\n\treturn Counter\n}\n"}
    )

    resolved = [
        r
        for r in index.references()
        if isinstance(r, ResolvedReference) and r.identifier == "Counter"
    ]
    assert len(resolved) == 1
    assert resolved[0].kind == ReferenceKind.VARIABLE


def test_local_variable_reference_is_unresolved() -> None:
    _, _, index = _resolve({"a.go": "package p\n\nfunc Foo() int {\n\tx := 1\n\treturn x\n}\n"})

    x_refs = [r for r in index.references() if r.identifier == "x"]
    assert x_refs
    assert all(isinstance(r, UnresolvedReference) for r in x_refs)


def test_type_reference_in_composite_literal_is_resolved() -> None:
    _, _, index = _resolve(
        {
            "a.go": (
                "package p\n\ntype Widget struct{}\n\nfunc Foo() Widget {\n\treturn Widget{}\n}\n"
            )
        }
    )

    resolved_types = [
        r
        for r in index.references()
        if isinstance(r, ResolvedReference) and r.identifier == "Widget"
    ]
    # one in the function's result type, one in the composite literal
    assert len(resolved_types) == 2
    assert all(r.kind == ReferenceKind.TYPE for r in resolved_types)


def test_type_reference_in_parameter_is_resolved() -> None:
    _, _, index = _resolve({"a.go": "package p\n\ntype Widget struct{}\n\nfunc Foo(w Widget) {}\n"})

    resolved = [
        r
        for r in index.references()
        if isinstance(r, ResolvedReference) and r.identifier == "Widget"
    ]
    assert len(resolved) == 1


def test_type_reference_in_struct_field_is_resolved() -> None:
    _, _, index = _resolve(
        {"a.go": ("package p\n\ntype Widget struct{}\n\ntype Wrapper struct {\n\tW Widget\n}\n")}
    )

    resolved = [
        r
        for r in index.references()
        if isinstance(r, ResolvedReference) and r.identifier == "Widget"
    ]
    assert len(resolved) == 1


def test_unresolved_type_reference() -> None:
    _, _, index = _resolve({"a.go": "package p\n\ntype Wrapper struct {\n\tW OtherType\n}\n"})

    unresolved = [r for r in index.references() if r.identifier == "OtherType"]
    assert len(unresolved) == 1
    assert isinstance(unresolved[0], UnresolvedReference)
    assert unresolved[0].kind == ReferenceKind.TYPE


def test_package_self_reference_is_resolved() -> None:
    _, _, index = _resolve({"a.go": "package mypkg\n"})

    resolved = [
        r
        for r in index.references()
        if isinstance(r, ResolvedReference) and r.kind == ReferenceKind.PACKAGE
    ]
    assert len(resolved) == 1
    assert resolved[0].identifier == "mypkg"


def test_selector_based_call_is_skipped_entirely() -> None:
    _, _, index = _resolve(
        {"a.go": 'package p\n\nimport "fmt"\n\nfunc Foo() {\n\tfmt.Println("hi")\n}\n'}
    )

    assert not any(r.identifier == "fmt" for r in index.references())
    assert not any(r.identifier == "Println" for r in index.references())


def test_method_call_via_selector_is_skipped() -> None:
    _, _, index = _resolve(
        {"a.go": ("package p\n\ntype Widget struct{}\n\nfunc Foo(w Widget) {\n\tw.Method()\n}\n")}
    )

    assert not any(r.identifier == "Method" for r in index.references())


def test_builtins_are_neither_resolved_nor_unresolved() -> None:
    _, _, index = _resolve(
        {"a.go": "package p\n\nfunc Foo(items []int) int {\n\treturn len(items)\n}\n"}
    )

    assert not any(r.identifier == "len" for r in index.references())


def test_duplicate_identifier_candidates_all_get_a_reference() -> None:
    _, _, index = _resolve(
        {"a.go": ("package p\n\nfunc helper() {}\n\nfunc Foo() {\n\thelper()\n\thelper()\n}\n")}
    )

    resolved = [
        r
        for r in index.references()
        if isinstance(r, ResolvedReference) and r.identifier == "helper"
    ]
    assert len(resolved) == 2
    assert resolved[0].id != resolved[1].id


def test_unresolved_identifiers_produce_diagnostics() -> None:
    _, _, index = _resolve({"a.go": "package p\n\nfunc Foo() int {\n\treturn missing\n}\n"})

    messages = [d.message for d in index.diagnostics()]
    assert any("missing" in m for m in messages)


def test_grouped_var_type_reference_is_resolved() -> None:
    _, _, index = _resolve(
        {"a.go": ("package p\n\ntype Widget struct{}\n\nvar (\n\tA Widget\n\tB Widget\n)\n")}
    )

    resolved = [
        r
        for r in index.references()
        if isinstance(r, ResolvedReference) and r.identifier == "Widget"
    ]
    assert len(resolved) == 2


def test_empty_file_produces_no_references_except_package() -> None:
    _, _, index = _resolve({"a.go": "package p\n"})

    non_package = [r for r in index.references() if r.kind != ReferenceKind.PACKAGE]
    assert non_package == []


def test_resolution_is_deterministic_across_repeated_runs() -> None:
    sources = {"a.go": "package p\n\nfunc helper() {}\n\nfunc Foo() {\n\thelper()\n}\n"}
    repository, symbols, parsed_files = build_repository_and_symbols(sources)

    first = GoReferenceResolver(parsed_files).resolve(repository, symbols)
    second = GoReferenceResolver(parsed_files).resolve(repository, symbols)

    assert [r.id for r in first.references()] == [r.id for r in second.references()]
