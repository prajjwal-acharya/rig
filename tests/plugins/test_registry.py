from __future__ import annotations

import pytest

from rig.plugins.capability import Capability
from rig.plugins.errors import DuplicatePluginError, PluginNotFoundError
from rig.plugins.registry import PluginRegistry
from rig.plugins.types import PluginState, PluginType
from tests.plugins.conftest import RecordingPlugin, make_manifest


def test_register_and_get() -> None:
    registry = PluginRegistry()
    manifest = make_manifest(name="alpha")
    plugin = RecordingPlugin()

    entry = registry.register(manifest, plugin, [Capability(provides="alpha-capability")])

    assert registry.get("alpha") is entry
    assert entry.state == PluginState.REGISTERED


def test_duplicate_registration_is_rejected() -> None:
    registry = PluginRegistry()
    manifest = make_manifest(name="alpha")

    registry.register(manifest, RecordingPlugin())

    with pytest.raises(DuplicatePluginError):
        registry.register(manifest, RecordingPlugin())


def test_get_missing_plugin_raises() -> None:
    registry = PluginRegistry()

    with pytest.raises(PluginNotFoundError):
        registry.get("does-not-exist")


def test_list_plugins_filters_by_type() -> None:
    registry = PluginRegistry()
    registry.register(make_manifest(name="lang", type=PluginType.LANGUAGE), RecordingPlugin())
    registry.register(
        make_manifest(name="infra", type=PluginType.INFRASTRUCTURE), RecordingPlugin()
    )

    language_plugins = registry.list_plugins(PluginType.LANGUAGE)

    assert [entry.manifest.name for entry in language_plugins] == ["lang"]
    assert len(registry.list_plugins()) == 2


def test_find_providers_resolves_capability() -> None:
    registry = PluginRegistry()
    registry.register(
        make_manifest(name="python"),
        RecordingPlugin(),
        [Capability(provides="python-parsing")],
    )
    registry.register(
        make_manifest(name="go"),
        RecordingPlugin(),
        [Capability(provides="go-parsing")],
    )

    providers = registry.find_providers("python-parsing")

    assert [entry.manifest.name for entry in providers] == ["python"]


def test_find_providers_returns_empty_for_unknown_capability() -> None:
    registry = PluginRegistry()

    assert registry.find_providers("nonexistent") == []


def test_contains_and_len() -> None:
    registry = PluginRegistry()
    registry.register(make_manifest(name="alpha"), RecordingPlugin())

    assert "alpha" in registry
    assert "beta" not in registry
    assert len(registry) == 1


def test_unregister_removes_plugin() -> None:
    registry = PluginRegistry()
    registry.register(make_manifest(name="alpha"), RecordingPlugin())

    registry.unregister("alpha")

    assert "alpha" not in registry
    with pytest.raises(PluginNotFoundError):
        registry.get("alpha")
