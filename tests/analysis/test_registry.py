from __future__ import annotations

import pytest

from rig.analysis.registry import AnalysisRegistry, DuplicateAnalysisError
from tests.analysis.conftest import FakeAnalysis


def test_register_and_lookup() -> None:
    registry = AnalysisRegistry()
    analysis = FakeAnalysis()

    registry.register(analysis)

    assert registry.lookup("fake") is analysis


def test_lookup_unregistered_returns_none() -> None:
    registry = AnalysisRegistry()

    assert registry.lookup("missing") is None


def test_duplicate_registration_raises() -> None:
    registry = AnalysisRegistry()
    registry.register(FakeAnalysis())

    with pytest.raises(DuplicateAnalysisError):
        registry.register(FakeAnalysis())


def test_constructor_accepts_initial_analyses() -> None:
    analysis = FakeAnalysis()

    registry = AnalysisRegistry([analysis])

    assert registry.lookup("fake") is analysis
    assert len(registry) == 1


def test_unregister_removes_analysis() -> None:
    registry = AnalysisRegistry()
    registry.register(FakeAnalysis())

    registry.unregister("fake")

    assert registry.lookup("fake") is None
    assert "fake" not in registry


def test_unregister_missing_id_is_a_no_op() -> None:
    registry = AnalysisRegistry()

    registry.unregister("does-not-exist")  # must not raise

    assert len(registry) == 0


def test_analyses_are_enumerated_in_deterministic_id_order() -> None:
    registry = AnalysisRegistry([FakeAnalysis("zeta"), FakeAnalysis("alpha"), FakeAnalysis("mid")])

    assert [a.analysis_id for a in registry.analyses()] == ["alpha", "mid", "zeta"]


def test_contains_and_len() -> None:
    registry = AnalysisRegistry([FakeAnalysis("a")])

    assert "a" in registry
    assert "b" not in registry
    assert len(registry) == 1


def test_empty_registry() -> None:
    registry = AnalysisRegistry()

    assert len(registry) == 0
    assert registry.analyses() == ()
