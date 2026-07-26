from __future__ import annotations

import dataclasses

import pytest

from rig.analysis.diagnostics import AnalysisDiagnostic
from rig.analysis.result import AnalysisResult


def test_ok_factory_defaults() -> None:
    result = AnalysisResult.ok(analysis_id="a1", repository_id="r1")

    assert result.success is True
    assert result.diagnostics == ()
    assert dict(result.artifacts) == {}
    assert dict(result.metadata) == {}


def test_ok_factory_with_artifacts() -> None:
    result = AnalysisResult.ok(analysis_id="a1", repository_id="r1", artifacts={"count": 42})

    assert result.artifacts["count"] == 42


def test_failed_factory_requires_diagnostics() -> None:
    diagnostic = AnalysisDiagnostic(message="oops", category="general")
    result = AnalysisResult.failed(analysis_id="a1", repository_id="r1", diagnostics=(diagnostic,))

    assert result.success is False
    assert result.diagnostics == (diagnostic,)


def test_result_is_immutable() -> None:
    result = AnalysisResult.ok(analysis_id="a1", repository_id="r1")

    with pytest.raises(dataclasses.FrozenInstanceError):
        result.success = False  # type: ignore[misc]


def test_artifacts_mapping_cannot_be_mutated_after_construction() -> None:
    result = AnalysisResult.ok(analysis_id="a1", repository_id="r1", artifacts={"count": 1})

    with pytest.raises(TypeError):
        result.artifacts["count"] = 2  # type: ignore[index]


def test_metadata_mapping_cannot_be_mutated_after_construction() -> None:
    result = AnalysisResult(analysis_id="a1", repository_id="r1", metadata={"files_analyzed": 3})

    with pytest.raises(TypeError):
        result.metadata["files_analyzed"] = 4  # type: ignore[index]


def test_default_timing_fields_are_zero_or_none() -> None:
    result = AnalysisResult.ok(analysis_id="a1", repository_id="r1")

    assert result.started_at is None
    assert result.completed_at is None
    assert result.duration_seconds == 0.0


def test_replace_still_produces_immutable_mappings() -> None:
    result = AnalysisResult.ok(analysis_id="a1", repository_id="r1", artifacts={"x": 1})

    replaced = dataclasses.replace(result, duration_seconds=1.5)

    assert replaced.artifacts["x"] == 1
    with pytest.raises(TypeError):
        replaced.artifacts["x"] = 2  # type: ignore[index]
