from __future__ import annotations

import logging
import threading
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from rig.graph.model import Graph
from rig.ir.repository import RepositoryIR
from rig.references.index import ReferenceIndex
from rig.symbols.table import SymbolTable


class CancellationToken:
    """Placeholder: no analysis in this milestone checks this yet. Reserved
    so a future long-running analysis can poll `is_cancelled` cooperatively.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cancelled = False

    def cancel(self) -> None:
        with self._lock:
            self._cancelled = True

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled


class AnalysisLogger:
    """Placeholder: a thin, namespaced wrapper over the standard logger.
    Reserved so analyses have a shared logging surface instead of writing
    to stdout directly.
    """

    def __init__(self, name: str) -> None:
        self._logger = logging.getLogger(f"rig.analysis.{name}")

    def debug(self, message: str, *args: object) -> None:
        self._logger.debug(message, *args)

    def info(self, message: str, *args: object) -> None:
        self._logger.info(message, *args)

    def warning(self, message: str, *args: object) -> None:
        self._logger.warning(message, *args)

    def error(self, message: str, *args: object) -> None:
        self._logger.error(message, *args)


@dataclass(frozen=True, kw_only=True)
class AnalysisContext:
    """Everything an Analysis may depend on, passed explicitly - no global
    state. `symbols`/`references`/`graph` are optional: whether they are
    present is exactly what capability validation checks before dispatch.
    """

    repository: RepositoryIR
    symbols: SymbolTable | None = None
    references: ReferenceIndex | None = None
    graph: Graph | None = None
    config: Mapping[str, Any] = field(default_factory=dict)
    cancellation_token: CancellationToken | None = None
    logger: AnalysisLogger | None = None
