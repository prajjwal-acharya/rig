from __future__ import annotations

from importlib.metadata import EntryPoint

import pytest

from rig.plugins.discovery import (
    EntryPointPluginSource,
    PluginDescriptor,
    StaticPluginSource,
)
from tests.plugins.conftest import RecordingPlugin, make_manifest


def test_static_source_returns_configured_descriptors() -> None:
    descriptor = PluginDescriptor.from_plugin_class(RecordingPlugin)
    source = StaticPluginSource([descriptor])

    discovered = source.discover()

    assert discovered == [descriptor]


def test_descriptor_from_plugin_class_reads_manifest_without_instantiating() -> None:
    descriptor = PluginDescriptor.from_plugin_class(RecordingPlugin)

    assert descriptor.manifest is RecordingPlugin.manifest
    assert descriptor.factory is RecordingPlugin


def test_entry_point_source_discovers_valid_plugin(monkeypatch: pytest.MonkeyPatch) -> None:
    entry_point = EntryPoint(
        name="recording",
        value="tests.plugins.conftest:RecordingPlugin",
        group="rig.plugins",
    )

    def fake_entry_points(*, group: str) -> list[EntryPoint]:
        assert group == "rig.plugins"
        return [entry_point]

    import rig.plugins.discovery as discovery_module

    monkeypatch.setattr(discovery_module.metadata, "entry_points", fake_entry_points)

    source = EntryPointPluginSource()
    descriptors = source.discover()

    assert len(descriptors) == 1
    assert descriptors[0].manifest.name == make_manifest().name


def test_entry_point_source_skips_broken_entry_points(monkeypatch: pytest.MonkeyPatch) -> None:
    broken = EntryPoint(name="broken", value="does.not.exist:Nothing", group="rig.plugins")

    def fake_entry_points(*, group: str) -> list[EntryPoint]:
        return [broken]

    import rig.plugins.discovery as discovery_module

    monkeypatch.setattr(discovery_module.metadata, "entry_points", fake_entry_points)

    source = EntryPointPluginSource()

    assert source.discover() == []
