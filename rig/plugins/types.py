from __future__ import annotations

from enum import Enum


class PluginType(str, Enum):
    LANGUAGE = "language"
    FRAMEWORK = "framework"
    INFRASTRUCTURE = "infrastructure"
    INTELLIGENCE = "intelligence"
    VISUALIZATION = "visualization"
    EXPORT = "export"
    QUERY = "query"


class PluginState(str, Enum):
    DISCOVERED = "discovered"
    LOADED = "loaded"
    VALIDATED = "validated"
    INITIALIZED = "initialized"
    REGISTERED = "registered"
    SHUTDOWN = "shutdown"
    FAILED = "failed"
