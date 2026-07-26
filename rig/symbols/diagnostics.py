from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SymbolDiagnosticSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True, kw_only=True)
class SymbolDiagnostic:
    message: str
    severity: SymbolDiagnosticSeverity = SymbolDiagnosticSeverity.WARNING
