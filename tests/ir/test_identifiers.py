from __future__ import annotations

from pathlib import Path

from rig.ir.identifiers import declaration_id, file_id, package_id, repository_id


def test_repository_id_is_deterministic() -> None:
    root = Path("/repos/example")

    assert repository_id(root) == repository_id(root)


def test_repository_id_differs_for_different_roots() -> None:
    assert repository_id(Path("/repos/a")) != repository_id(Path("/repos/b"))


def test_file_id_is_deterministic() -> None:
    repo_id = repository_id(Path("/repos/example"))
    relative_path = Path("pkg/main.go")

    assert file_id(repo_id, relative_path) == file_id(repo_id, relative_path)


def test_file_id_differs_for_different_paths() -> None:
    repo_id = repository_id(Path("/repos/example"))

    assert file_id(repo_id, Path("a.go")) != file_id(repo_id, Path("b.go"))


def test_file_id_differs_across_repositories() -> None:
    relative_path = Path("main.go")
    repo_a = repository_id(Path("/repos/a"))
    repo_b = repository_id(Path("/repos/b"))

    assert file_id(repo_a, relative_path) != file_id(repo_b, relative_path)


def test_package_id_is_deterministic_and_scoped_to_repository() -> None:
    repo_id = repository_id(Path("/repos/example"))

    assert package_id(repo_id, "mypkg") == package_id(repo_id, "mypkg")
    assert package_id(repo_id, "mypkg") != package_id(repo_id, "otherpkg")


def test_declaration_id_is_deterministic() -> None:
    fid = file_id(repository_id(Path("/repos/example")), Path("main.go"))

    assert declaration_id(fid, "function", "Foo") == declaration_id(fid, "function", "Foo")


def test_declaration_id_differs_by_kind() -> None:
    fid = file_id(repository_id(Path("/repos/example")), Path("main.go"))

    assert declaration_id(fid, "function", "Foo") != declaration_id(fid, "type", "Foo")


def test_declaration_id_occurrence_disambiguates_duplicates() -> None:
    fid = file_id(repository_id(Path("/repos/example")), Path("main.go"))

    first = declaration_id(fid, "function", "Foo", occurrence=0)
    second = declaration_id(fid, "function", "Foo", occurrence=1)

    assert first != second


def test_ids_never_use_raw_memory_addresses() -> None:
    # A loose but meaningful sanity check: ids are short deterministic
    # digests, not e.g. str(id(obj))-style memory addresses.
    root = Path("/repos/example")
    assert repository_id(root) == repository_id(Path("/repos/example"))
