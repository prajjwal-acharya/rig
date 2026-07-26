from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from rig.plugins.capability import Capability
from rig.plugins.errors import DuplicatePluginError, PluginNotFoundError
from rig.plugins.interface import Plugin
from rig.plugins.manifest import PluginManifest
from rig.plugins.types import PluginState, PluginType


@dataclass
class RegisteredPlugin:
    manifest: PluginManifest
    plugin: Plugin
    capabilities: tuple[Capability, ...]
    state: PluginState = PluginState.REGISTERED


class PluginRegistry:
    def __init__(self) -> None:
        self._plugins: dict[str, RegisteredPlugin] = {}

    def register(
        self,
        manifest: PluginManifest,
        plugin: Plugin,
        capabilities: Sequence[Capability] = (),
    ) -> RegisteredPlugin:
        if manifest.name in self._plugins:
            raise DuplicatePluginError(f"plugin already registered: {manifest.name!r}")

        entry = RegisteredPlugin(
            manifest=manifest,
            plugin=plugin,
            capabilities=tuple(capabilities),
        )
        self._plugins[manifest.name] = entry
        return entry

    def get(self, name: str) -> RegisteredPlugin:
        try:
            return self._plugins[name]
        except KeyError as exc:
            raise PluginNotFoundError(f"no such plugin: {name!r}") from exc

    def list_plugins(self, plugin_type: PluginType | None = None) -> list[RegisteredPlugin]:
        entries = list(self._plugins.values())
        if plugin_type is None:
            return entries
        return [entry for entry in entries if entry.manifest.type == plugin_type]

    def find_providers(self, capability_name: str) -> list[RegisteredPlugin]:
        return [
            entry
            for entry in self._plugins.values()
            if any(capability.provides == capability_name for capability in entry.capabilities)
        ]

    def unregister(self, name: str) -> None:
        self._plugins.pop(name, None)

    def __len__(self) -> int:
        return len(self._plugins)

    def __contains__(self, name: str) -> bool:
        return name in self._plugins
