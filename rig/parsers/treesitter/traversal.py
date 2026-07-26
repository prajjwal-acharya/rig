from __future__ import annotations

from collections.abc import Iterator

from rig.parsers.treesitter.tree import SyntaxNode


def iter_preorder(node: SyntaxNode) -> Iterator[SyntaxNode]:
    """Yield `node` itself, then its descendants, parent before children."""
    stack: list[SyntaxNode] = [node]
    while stack:
        current = stack.pop()
        yield current
        stack.extend(reversed(current.children()))


def iter_children(node: SyntaxNode) -> Iterator[SyntaxNode]:
    yield from node.children()


def iter_named_children(node: SyntaxNode) -> Iterator[SyntaxNode]:
    yield from node.named_children()


def iter_descendants(node: SyntaxNode) -> Iterator[SyntaxNode]:
    for descendant in iter_preorder(node):
        if descendant != node:
            yield descendant


def iter_named_descendants(node: SyntaxNode) -> Iterator[SyntaxNode]:
    for descendant in iter_descendants(node):
        if descendant.is_named:
            yield descendant
