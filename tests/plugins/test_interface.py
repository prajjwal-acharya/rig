from __future__ import annotations

import pytest

from rig.plugins.interface import Plugin
from tests.plugins.conftest import RecordingPlugin


def test_plugin_is_abstract() -> None:
    with pytest.raises(TypeError):
        Plugin()  # type: ignore[abstract]


def test_incomplete_plugin_cannot_be_instantiated() -> None:
    class IncompletePlugin(Plugin):
        def initialize(self, context: object) -> None:
            pass

    with pytest.raises(TypeError):
        IncompletePlugin()  # type: ignore[abstract]


def test_concrete_plugin_exposes_manifest_on_the_class() -> None:
    assert RecordingPlugin.manifest.name == "sample-plugin"


def test_concrete_plugin_lifecycle_methods_are_callable(plugin_context: object) -> None:
    plugin = RecordingPlugin()

    plugin.initialize(plugin_context)  # type: ignore[arg-type]
    capabilities = plugin.register()
    plugin.shutdown()

    assert plugin.initialized_with is plugin_context
    assert plugin.registered is True
    assert plugin.shut_down is True
    assert capabilities[0].provides == "sample-capability"
