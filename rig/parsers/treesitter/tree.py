from __future__ import annotations

from dataclasses import dataclass

from tree_sitter import Node as TSNode
from tree_sitter import Tree as TSTree


@dataclass(frozen=True)
class Point:
    row: int
    column: int


class SyntaxNode:
    __slots__ = ("_node",)

    def __init__(self, node: TSNode) -> None:
        self._node = node

    @property
    def type(self) -> str:
        return self._node.type

    @property
    def is_named(self) -> bool:
        return self._node.is_named

    @property
    def is_error(self) -> bool:
        return self._node.is_error

    @property
    def is_missing(self) -> bool:
        return self._node.is_missing

    @property
    def start_byte(self) -> int:
        return self._node.start_byte

    @property
    def end_byte(self) -> int:
        return self._node.end_byte

    @property
    def start_point(self) -> Point:
        point = self._node.start_point
        return Point(row=point.row, column=point.column)

    @property
    def end_point(self) -> Point:
        point = self._node.end_point
        return Point(row=point.row, column=point.column)

    @property
    def text(self) -> bytes:
        return self._node.text or b""

    @property
    def child_count(self) -> int:
        return self._node.child_count

    @property
    def named_child_count(self) -> int:
        return self._node.named_child_count

    def children(self) -> tuple[SyntaxNode, ...]:
        return tuple(SyntaxNode(child) for child in self._node.children)

    def named_children(self) -> tuple[SyntaxNode, ...]:
        return tuple(SyntaxNode(child) for child in self._node.named_children)

    def child_by_field_name(self, name: str) -> SyntaxNode | None:
        child = self._node.child_by_field_name(name)
        return None if child is None else SyntaxNode(child)

    def children_by_field_name(self, name: str) -> tuple[SyntaxNode, ...]:
        return tuple(SyntaxNode(child) for child in self._node.children_by_field_name(name))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SyntaxNode):
            return NotImplemented
        return self._node.id == other._node.id

    def __hash__(self) -> int:
        return hash(self._node.id)

    def __repr__(self) -> str:
        return f"SyntaxNode(type={self.type!r})"


class SyntaxTree:
    __slots__ = ("_tree",)

    def __init__(self, tree: TSTree) -> None:
        self._tree = tree

    @property
    def root(self) -> SyntaxNode:
        return SyntaxNode(self._tree.root_node)

    @property
    def has_error(self) -> bool:
        return self._tree.root_node.has_error
