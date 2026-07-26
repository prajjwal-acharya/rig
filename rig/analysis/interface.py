from __future__ import annotations

from abc import ABC, abstractmethod

from rig.analysis.capability import Capability
from rig.analysis.context import AnalysisContext
from rig.analysis.result import AnalysisResult


class Analysis(ABC):
    """Generic contract every semantic analysis implements.

    Language-independent by design: `supported_languages` is informational
    metadata an orchestrator may use for filtering, not something this
    framework enforces itself.
    """

    @property
    @abstractmethod
    def analysis_id(self) -> str: ...

    @property
    @abstractmethod
    def display_name(self) -> str: ...

    @property
    def version(self) -> str | None:
        return None

    @property
    def supported_languages(self) -> frozenset[str]:
        # Empty means language-agnostic (applies regardless of language).
        return frozenset()

    @property
    @abstractmethod
    def required_capabilities(self) -> frozenset[Capability]: ...

    @abstractmethod
    def execute(self, context: AnalysisContext) -> AnalysisResult: ...
