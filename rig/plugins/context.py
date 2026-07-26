from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from rig.scanner.models import RepositorySnapshot

TRACE_LEVEL = 5
logging.addLevelName(TRACE_LEVEL, "TRACE")


class PluginLogger:
    def __init__(self, name: str) -> None:
        self._logger = logging.getLogger(f"rig.plugins.{name}")

    def trace(self, message: str, *args: object) -> None:
        self._logger.log(TRACE_LEVEL, message, *args)

    def debug(self, message: str, *args: object) -> None:
        self._logger.debug(message, *args)

    def info(self, message: str, *args: object) -> None:
        self._logger.info(message, *args)

    def warning(self, message: str, *args: object) -> None:
        self._logger.warning(message, *args)

    def error(self, message: str, *args: object) -> None:
        self._logger.error(message, *args)


class PluginCache:
    def __init__(self) -> None:
        self._store: dict[str, Any] = {}

    def get(self, key: str, default: Any | None = None) -> Any | None:
        return self._store.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._store[key] = value

    def clear(self) -> None:
        self._store.clear()


@dataclass(frozen=True)
class PluginContext:
    snapshot: RepositorySnapshot | None
    config: Mapping[str, Any]
    logger: PluginLogger
    cache: PluginCache
    extensions: Mapping[str, Any] = field(default_factory=dict)
