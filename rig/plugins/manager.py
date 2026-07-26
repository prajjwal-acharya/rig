from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from rig.plugins.context import PluginContext
from rig.plugins.discovery import PluginDescriptor, PluginSource
from rig.plugins.errors import PluginError
from rig.plugins.manifest import check_api_compatibility, validate_manifest
from rig.plugins.registry import PluginRegistry, RegisteredPlugin
from rig.plugins.types import PluginState


@dataclass(frozen=True)
class PluginFailure:
    name: str
    stage: PluginState
    error: str


@dataclass(frozen=True)
class PluginLoadReport:
    registered: list[RegisteredPlugin]
    failed: list[PluginFailure]


class PluginManager:
    def __init__(self, registry: PluginRegistry | None = None) -> None:
        self.registry = registry or PluginRegistry()

    def discover(self, sources: Sequence[PluginSource]) -> list[PluginDescriptor]:
        descriptors: list[PluginDescriptor] = []
        for source in sources:
            descriptors.extend(source.discover())
        return descriptors

    def load_all(
        self,
        sources: Sequence[PluginSource],
        context: PluginContext,
    ) -> PluginLoadReport:
        failed: list[PluginFailure] = []
        registered: list[RegisteredPlugin] = []

        for descriptor in self.discover(sources):
            name = descriptor.manifest.name

            try:
                validate_manifest(descriptor.manifest)
                check_api_compatibility(descriptor.manifest)
            except PluginError as exc:
                failed.append(PluginFailure(name, PluginState.VALIDATED, str(exc)))
                continue

            try:
                plugin = descriptor.factory()
            except Exception as exc:  # noqa: BLE001 - a plugin must never crash the platform
                failed.append(PluginFailure(name, PluginState.LOADED, str(exc)))
                continue

            try:
                plugin.initialize(context)
            except Exception as exc:  # noqa: BLE001
                failed.append(PluginFailure(name, PluginState.INITIALIZED, str(exc)))
                continue

            try:
                capabilities = plugin.register()
                entry = self.registry.register(descriptor.manifest, plugin, capabilities)
            except Exception as exc:  # noqa: BLE001
                failed.append(PluginFailure(name, PluginState.REGISTERED, str(exc)))
                continue

            registered.append(entry)

        return PluginLoadReport(registered=registered, failed=failed)

    def shutdown_all(self) -> list[PluginFailure]:
        failures: list[PluginFailure] = []
        for entry in self.registry.list_plugins():
            try:
                entry.plugin.shutdown()
                entry.state = PluginState.SHUTDOWN
            except Exception as exc:  # noqa: BLE001 - one plugin's shutdown must not block others
                entry.state = PluginState.FAILED
                failures.append(PluginFailure(entry.manifest.name, PluginState.SHUTDOWN, str(exc)))
        return failures
