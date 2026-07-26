from __future__ import annotations

from rig.parsers.treesitter.backend import TreeSitterBackend
from rig.parsers.treesitter.grammars.go import GO_GRAMMAR
from rig.parsers.treesitter.traversal import (
    iter_children,
    iter_descendants,
    iter_named_children,
    iter_named_descendants,
    iter_preorder,
)
from tests.parsers.treesitter.conftest import VALID_GO_SOURCE


def _root():
    backend = TreeSitterBackend()
    tree = backend.parse(GO_GRAMMAR, VALID_GO_SOURCE.encode("utf-8"))
    return tree.root


def test_iter_preorder_includes_the_node_itself_first() -> None:
    root = _root()

    nodes = list(iter_preorder(root))

    assert nodes[0] == root
    assert len(nodes) > 1


def test_iter_preorder_visits_parent_before_children() -> None:
    root = _root()

    nodes = list(iter_preorder(root))
    types = [n.type for n in nodes]

    assert types[0] == "source_file"
    assert "function_declaration" in types
    function_index = types.index("function_declaration")
    block_index = types.index("block")
    assert function_index < block_index


def test_iter_children_yields_direct_children_only() -> None:
    root = _root()

    children = list(iter_children(root))

    assert len(children) == root.child_count
    assert all(child != root for child in children)


def test_iter_named_children_yields_only_named_direct_children() -> None:
    root = _root()

    named = list(iter_named_children(root))

    assert all(child.is_named for child in named)
    assert len(named) == root.named_child_count


def test_iter_descendants_excludes_the_node_itself() -> None:
    root = _root()

    descendants = list(iter_descendants(root))

    assert root not in descendants
    assert len(descendants) == len(list(iter_preorder(root))) - 1


def test_iter_named_descendants_only_yields_named_nodes() -> None:
    root = _root()

    named_descendants = list(iter_named_descendants(root))

    assert all(node.is_named for node in named_descendants)
    assert "function_declaration" in {n.type for n in named_descendants}


def test_traversal_on_empty_tree_yields_only_root() -> None:
    backend = TreeSitterBackend()
    tree = backend.parse(GO_GRAMMAR, b"")

    nodes = list(iter_preorder(tree.root))
    descendants = list(iter_descendants(tree.root))

    assert nodes == [tree.root]
    assert descendants == []
