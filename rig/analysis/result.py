from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from typing import Any

from rig.analysis.diagnostics import AnalysisDiagnostic


@dataclass(frozen=True, kw_only=True)
class AnalysisResult:
    analysis_id: str
    repository_id: str
    analysis_version: str | None = None
    success: bool = True
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_seconds: float = 0.0
    diagnostics: tuple[AnalysisDiagnostic, ...] = ()
    artifacts: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "artifacts", MappingProxyType(dict(self.artifacts)))
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    @classmethod
    def ok(
        cls,
        *,
        analysis_id: str,
        repository_id: str,
        diagnostics: tuple[AnalysisDiagnostic, ...] = (),
        artifacts: Mapping[str, Any] = MappingProxyType({}),
        metadata: Mapping[str, Any] = MappingProxyType({}),
    ) -> AnalysisResult:
        return cls(
            analysis_id=analysis_id,
            repository_id=repository_id,
            success=True,
            diagnostics=diagnostics,
            artifacts=artifacts,
            metadata=metadata,
        )

    @classmethod
    def failed(
        cls,
        *,
        analysis_id: str,
        repository_id: str,
        diagnostics: tuple[AnalysisDiagnostic, ...],
        metadata: Mapping[str, Any] = MappingProxyType({}),
    ) -> AnalysisResult:
        return cls(
            analysis_id=analysis_id,
            repository_id=repository_id,
            success=False,
            diagnostics=diagnostics,
            metadata=metadata,
        )
