from __future__ import annotations

import pytest

from rig.graph.builder import GraphBuilder
from rig.graph.model import Graph
from rig.graph.registry import DuplicateGraphBuilderError, GraphBuilderRegistry
from rig.ir.repository import RepositoryIR


class FakeGraphBuilder(GraphBuilder):
    def __init__(self, builder_id: str = "fake") -> None:
        self._builder_id = builder_id

    @property
    def builder_id(self) -> str:
        return self._builder_id

    def build(self, repository: RepositoryIR) -> Graph:
        return Graph()


def test_register_and_lookup() -> None:
    registry = GraphBuilderRegistry()
    builder = FakeGraphBuilder()

    registry.register(builder)

    assert registry.lookup("fake") is builder


def test_lookup_unregistered_builder_returns_none() -> None:
    registry = GraphBuilderRegistry()

    assert registry.lookup("missing") is None


def test_duplicate_registration_raises() -> None:
    registry = GraphBuilderRegistry()
    registry.register(FakeGraphBuilder())

    with pytest.raises(DuplicateGraphBuilderError):
        registry.register(FakeGraphBuilder())


def test_constructor_accepts_initial_builders() -> None:
    builder = FakeGraphBuilder()

    registry = GraphBuilderRegistry([builder])

    assert registry.lookup("fake") is builder
    assert len(registry) == 1


def test_builders_enumerates_all_registered() -> None:
    a = FakeGraphBuilder(builder_id="a")
    b = FakeGraphBuilder(builder_id="b")
    registry = GraphBuilderRegistry([a, b])

    assert set(registry.builders()) == {a, b}


def test_contains_reflects_registered_builders() -> None:
    registry = GraphBuilderRegistry([FakeGraphBuilder()])

    assert "fake" in registry
    assert "other" not in registry
