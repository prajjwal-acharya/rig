from __future__ import annotations

import time
from collections.abc import Sequence
from dataclasses import replace
from datetime import datetime, timezone

from rig.analysis.capability import Capability
from rig.analysis.context import AnalysisContext
from rig.analysis.diagnostics import AnalysisDiagnostic, AnalysisDiagnosticSeverity
from rig.analysis.interface import Analysis
from rig.analysis.registry import AnalysisRegistry
from rig.analysis.result import AnalysisResult

_CAPABILITY_FIELDS: dict[Capability, str] = {
    Capability.IR: "repository",
    Capability.SYMBOL_TABLE: "symbols",
    Capability.REFERENCE_INDEX: "references",
    Capability.GRAPH: "graph",
    Capability.IMPORT_GRAPH: "graph",
}


def _missing_capabilities(analysis: Analysis, context: AnalysisContext) -> tuple[Capability, ...]:
    missing = [
        capability
        for capability in analysis.required_capabilities
        if getattr(context, _CAPABILITY_FIELDS[capability]) is None
    ]
    return tuple(sorted(missing, key=lambda capability: capability.value))


class AnalysisManager:
    """Orchestrates Analysis execution: validates capabilities, times
    execution, and isolates failures - one analysis failing never stops
    the others or crashes the manager. Sequential only; parallel execution
    is explicitly out of scope for this milestone.
    """

    def __init__(self, registry: AnalysisRegistry) -> None:
        self.registry = registry

    def execute_one(self, analysis_id: str, context: AnalysisContext) -> AnalysisResult:
        analysis = self.registry.lookup(analysis_id)
        if analysis is None:
            return AnalysisResult.failed(
                analysis_id=analysis_id,
                repository_id=context.repository.id,
                diagnostics=(
                    AnalysisDiagnostic(
                        message=f"no analysis registered with id {analysis_id!r}",
                        category="missing-analysis",
                        severity=AnalysisDiagnosticSeverity.ERROR,
                    ),
                ),
            )
        return self._run(analysis, context)

    def execute_all(
        self,
        context: AnalysisContext,
        analysis_ids: Sequence[str] | None = None,
    ) -> tuple[AnalysisResult, ...]:
        ids = (
            list(analysis_ids)
            if analysis_ids is not None
            else [analysis.analysis_id for analysis in self.registry.analyses()]
        )
        return tuple(self.execute_one(analysis_id, context) for analysis_id in ids)

    def _run(self, analysis: Analysis, context: AnalysisContext) -> AnalysisResult:
        missing = _missing_capabilities(analysis, context)
        if missing:
            diagnostics = tuple(
                AnalysisDiagnostic(
                    message=f"missing required capability: {capability.value}",
                    category="missing-capability",
                    severity=AnalysisDiagnosticSeverity.ERROR,
                )
                for capability in missing
            )
            return AnalysisResult.failed(
                analysis_id=analysis.analysis_id,
                repository_id=context.repository.id,
                diagnostics=diagnostics,
            )

        started_at = datetime.now(timezone.utc)
        start = time.perf_counter()
        try:
            result = analysis.execute(context)
        except Exception as exc:  # noqa: BLE001 - one analysis must never crash the manager
            duration = time.perf_counter() - start
            completed_at = datetime.now(timezone.utc)
            failure = AnalysisResult.failed(
                analysis_id=analysis.analysis_id,
                repository_id=context.repository.id,
                diagnostics=(
                    AnalysisDiagnostic(
                        message=(
                            f"analysis {analysis.analysis_id!r} raised "
                            f"{exc.__class__.__name__}: {exc}"
                        ),
                        category="analysis-failure",
                        severity=AnalysisDiagnosticSeverity.ERROR,
                    ),
                ),
            )
            return replace(
                failure,
                analysis_version=analysis.version,
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration,
            )

        duration = time.perf_counter() - start
        completed_at = datetime.now(timezone.utc)
        # The manager, not the analysis, owns identity/timing/version fields
        # on the returned result - an analysis only needs to report success,
        # diagnostics, artifacts, and metadata.
        return replace(
            result,
            analysis_id=analysis.analysis_id,
            repository_id=context.repository.id,
            analysis_version=analysis.version,
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=duration,
        )
