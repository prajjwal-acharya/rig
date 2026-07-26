from __future__ import annotations

from collections.abc import Sequence
from typing import Any, ClassVar

import pytest

from rig.plugins.capability import Capability
from rig.plugins.context import PluginCache, PluginContext, PluginLogger
from rig.plugins.interface import Plugin
from rig.plugins.manifest import PluginManifest
from rig.plugins.types import PluginType


def make_manifest(name: str = "sample-plugin", **overrides: Any) -> PluginManifest:
    fields: dict[str, Any] = {
        "name": name,
        "version": "1.0.0",
        "type": PluginType.LANGUAGE,
        "api_version": "1.0",
        "description": "A sample plugin used in tests.",
    }
    fields.update(overrides)
    return PluginManifest(**fields)


class RecordingPlugin(Plugin):
    manifest: ClassVar[PluginManifest] = make_manifest()

    def __init__(self) -> None:
        self.initialized_with: PluginContext | None = None
        self.registered = False
        self.shut_down = False

    def initialize(self, context: PluginContext) -> None:
        self.initialized_with = context

    def register(self) -> Sequence[Capability]:
        self.registered = True
        return [Capability(provides="sample-capability")]

    def shutdown(self) -> None:
        self.shut_down = True


class FailingConstructionPlugin(Plugin):
    manifest: ClassVar[PluginManifest] = make_manifest(name="failing-construction")

    def __init__(self) -> None:
        raise RuntimeError("boom during construction")

    def initialize(self, context: PluginContext) -> None:
        pass

    def register(self) -> Sequence[Capability]:
        return []

    def shutdown(self) -> None:
        pass


class FailingInitializePlugin(Plugin):
    manifest: ClassVar[PluginManifest] = make_manifest(name="failing-initialize")

    def initialize(self, context: PluginContext) -> None:
        raise RuntimeError("boom during initialize")

    def register(self) -> Sequence[Capability]:
        return []

    def shutdown(self) -> None:
        pass


class FailingRegisterPlugin(Plugin):
    manifest: ClassVar[PluginManifest] = make_manifest(name="failing-register")

    def initialize(self, context: PluginContext) -> None:
        pass

    def register(self) -> Sequence[Capability]:
        raise RuntimeError("boom during register")

    def shutdown(self) -> None:
        pass


class FailingShutdownPlugin(Plugin):
    manifest: ClassVar[PluginManifest] = make_manifest(name="failing-shutdown")

    def initialize(self, context: PluginContext) -> None:
        pass

    def register(self) -> Sequence[Capability]:
        return []

    def shutdown(self) -> None:
        raise RuntimeError("boom during shutdown")


@pytest.fixture
def plugin_context() -> PluginContext:
    return PluginContext(
        snapshot=None,
        config={},
        logger=PluginLogger("test"),
        cache=PluginCache(),
    )
