from __future__ import annotations

from rig.parsers.treesitter.backend import TreeSitterBackend
from rig.parsers.treesitter.grammars.go import GO_GRAMMAR
from rig.parsers.treesitter.tree import Point, SyntaxNode, SyntaxTree
from tests.parsers.treesitter.conftest import VALID_GO_SOURCE


def _tree_root() -> tuple[SyntaxTree, SyntaxNode]:
    backend = TreeSitterBackend()
    tree = backend.parse(GO_GRAMMAR, VALID_GO_SOURCE.encode("utf-8"))
    return tree, tree.root


def test_root_node_type_and_flags() -> None:
    _, root = _tree_root()

    assert root.type == "source_file"
    assert root.is_named is True
    assert root.is_error is False
    assert root.is_missing is False


def test_root_byte_and_point_ranges() -> None:
    _, root = _tree_root()

    assert root.start_byte == 0
    assert root.end_byte == len(VALID_GO_SOURCE.encode("utf-8"))
    assert root.start_point == Point(row=0, column=0)


def test_text_matches_source() -> None:
    _, root = _tree_root()

    assert root.text == VALID_GO_SOURCE.encode("utf-8")


def test_children_and_named_children() -> None:
    _, root = _tree_root()

    children = root.children()
    named = root.named_children()

    assert len(children) == root.child_count
    assert len(named) == root.named_child_count
    assert all(child.is_named for child in named)
    assert {child.type for child in named} == {"package_clause", "function_declaration"}


def test_node_equality_is_based_on_underlying_node_identity() -> None:
    _, root = _tree_root()
    root_again = root.children()[0]  # a distinct SyntaxNode wrapper for a distinct node

    same_child_a = root.children()[0]
    same_child_b = root.children()[0]

    assert same_child_a == same_child_b  # two wrappers, same underlying node
    assert hash(same_child_a) == hash(same_child_b)
    assert root != root_again  # genuinely different nodes


def test_tree_has_error_is_false_for_valid_source() -> None:
    tree, _ = _tree_root()

    assert tree.has_error is False


def test_syntax_tree_root_is_wrapped_not_raw() -> None:
    tree, root = _tree_root()

    assert isinstance(tree.root, SyntaxNode)
    assert isinstance(root, SyntaxNode)
