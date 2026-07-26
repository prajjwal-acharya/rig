from __future__ import annotations

import pytest

from rig.analysis.capability import Capability
from rig.analysis.context import AnalysisContext
from rig.analysis.interface import Analysis
from rig.analysis.result import AnalysisResult
from tests.analysis.conftest import FakeAnalysis, make_repository


def test_analysis_is_abstract() -> None:
    with pytest.raises(TypeError):
        Analysis()  # type: ignore[abstract]


def test_version_defaults_to_none_on_a_minimal_subclass() -> None:
    class MinimalAnalysis(Analysis):
        @property
        def analysis_id(self) -> str:
            return "minimal"

        @property
        def display_name(self) -> str:
            return "Minimal"

        @property
        def required_capabilities(self) -> frozenset[Capability]:
            return frozenset()

        def execute(self, context: AnalysisContext) -> AnalysisResult:
            raise NotImplementedError

    assert MinimalAnalysis().version is None


def test_supported_languages_defaults_to_empty_meaning_language_agnostic() -> None:
    class MinimalAnalysis(Analysis):
        @property
        def analysis_id(self) -> str:
            return "minimal"

        @property
        def display_name(self) -> str:
            return "Minimal"

        @property
        def required_capabilities(self) -> frozenset[Capability]:
            return frozenset()

        def execute(self, context: AnalysisContext) -> AnalysisResult:
            raise NotImplementedError

    assert MinimalAnalysis().supported_languages == frozenset()


def test_fake_analysis_executes_and_records_context() -> None:
    analysis = FakeAnalysis()
    context = AnalysisContext(repository=make_repository())

    result = analysis.execute(context)

    assert result.success is True
    assert analysis.executed_with is context
