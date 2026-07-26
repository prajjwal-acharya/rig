from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from importlib import metadata
from typing import Protocol

from rig.plugins.interface import Plugin
from rig.plugins.manifest import PluginManifest


@dataclass(frozen=True)
class PluginDescriptor:
    manifest: PluginManifest
    factory: Callable[[], Plugin]

    @classmethod
    def from_plugin_class(cls, plugin_class: type[Plugin]) -> PluginDescriptor:
        return cls(manifest=plugin_class.manifest, factory=plugin_class)


class PluginSource(Protocol):
    def discover(self) -> Iterable[PluginDescriptor]: ...


class StaticPluginSource:
    def __init__(self, descriptors: Iterable[PluginDescriptor]) -> None:
        self._descriptors = list(descriptors)

    def discover(self) -> list[PluginDescriptor]:
        return list(self._descriptors)


class EntryPointPluginSource:
    # Discovery and load are fused for entry points: Python packaging only
    # exposes a plugin's manifest by importing it, so entry_point.load()
    # doubles as both steps here (a known limitation, not unique to RIG).
    def __init__(self, group: str = "rig.plugins") -> None:
        self._group = group

    def discover(self) -> list[PluginDescriptor]:
        descriptors: list[PluginDescriptor] = []
        for entry_point in metadata.entry_points(group=self._group):
            try:
                plugin_class = entry_point.load()
            except Exception:  # noqa: BLE001, S112 - a broken entry point must not block others
                continue
            descriptors.append(PluginDescriptor.from_plugin_class(plugin_class))
        return descriptors
