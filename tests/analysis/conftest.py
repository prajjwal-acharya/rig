from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from rig.analysis.capability import Capability
from rig.analysis.context import AnalysisContext
from rig.analysis.interface import Analysis
from rig.analysis.result import AnalysisResult
from rig.ir.repository import RepositoryIR

REPO_ROOT = Path("/repos/example")


def make_repository() -> RepositoryIR:
    return RepositoryIR(id="repo:1", root=REPO_ROOT)


class FakeAnalysis(Analysis):
    def __init__(
        self,
        analysis_id: str = "fake",
        *,
        required_capabilities: frozenset[Capability] = frozenset(),
        version: str | None = "1.0.0",
        artifacts: Mapping[str, Any] | None = None,
    ) -> None:
        self._analysis_id = analysis_id
        self._required_capabilities = required_capabilities
        self._version = version
        self._artifacts = artifacts or {}
        self.executed_with: AnalysisContext | None = None

    @property
    def analysis_id(self) -> str:
        return self._analysis_id

    @property
    def display_name(self) -> str:
        return f"Fake Analysis ({self._analysis_id})"

    @property
    def version(self) -> str | None:
        return self._version

    @property
    def required_capabilities(self) -> frozenset[Capability]:
        return self._required_capabilities

    def execute(self, context: AnalysisContext) -> AnalysisResult:
        self.executed_with = context
        return AnalysisResult.ok(
            analysis_id="ignored-by-manager",
            repository_id="ignored-by-manager",
            artifacts=self._artifacts,
        )


class FailingAnalysis(Analysis):
    def __init__(self, analysis_id: str = "failing") -> None:
        self._analysis_id = analysis_id

    @property
    def analysis_id(self) -> str:
        return self._analysis_id

    @property
    def display_name(self) -> str:
        return "Failing Analysis"

    @property
    def required_capabilities(self) -> frozenset[Capability]:
        return frozenset()

    def execute(self, context: AnalysisContext) -> AnalysisResult:
        raise RuntimeError("boom during execute")
