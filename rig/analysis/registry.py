from __future__ import annotations

import threading
from collections.abc import Iterable

from rig.analysis.interface import Analysis


class DuplicateAnalysisError(ValueError):
    pass


class AnalysisRegistry:
    def __init__(self, analyses: Iterable[Analysis] = ()) -> None:
        self._lock = threading.Lock()
        self._by_id: dict[str, Analysis] = {}
        for analysis in analyses:
            self.register(analysis)

    def register(self, analysis: Analysis) -> None:
        with self._lock:
            existing = self._by_id.get(analysis.analysis_id)
            if existing is not None:
                raise DuplicateAnalysisError(
                    f"an analysis is already registered with id {analysis.analysis_id!r}"
                )
            self._by_id[analysis.analysis_id] = analysis

    def unregister(self, analysis_id: str) -> None:
        with self._lock:
            self._by_id.pop(analysis_id, None)

    def lookup(self, analysis_id: str) -> Analysis | None:
        return self._by_id.get(analysis_id)

    def analyses(self) -> tuple[Analysis, ...]:
        # Sorted by id regardless of registration order - determinism is an
        # explicit requirement for this registry, not just a side effect of
        # insertion order.
        return tuple(sorted(self._by_id.values(), key=lambda analysis: analysis.analysis_id))

    def __len__(self) -> int:
        return len(self._by_id)

    def __contains__(self, analysis_id: str) -> bool:
        return analysis_id in self._by_id
