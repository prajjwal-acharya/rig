from __future__ import annotations

from rig.plugins.context import PluginContext
from rig.plugins.discovery import PluginDescriptor, StaticPluginSource
from rig.plugins.manager import PluginManager
from rig.plugins.types import PluginState
from tests.plugins.conftest import (
    FailingConstructionPlugin,
    FailingInitializePlugin,
    FailingRegisterPlugin,
    FailingShutdownPlugin,
    RecordingPlugin,
    make_manifest,
)


def _source_for(*plugin_classes: type) -> list[StaticPluginSource]:
    return [StaticPluginSource(PluginDescriptor.from_plugin_class(cls) for cls in plugin_classes)]


def test_load_all_registers_valid_plugin(plugin_context: PluginContext) -> None:
    manager = PluginManager()

    report = manager.load_all(_source_for(RecordingPlugin), plugin_context)

    assert len(report.registered) == 1
    assert report.failed == []
    assert "sample-plugin" in manager.registry

    entry = manager.registry.get("sample-plugin")
    assert entry.state == PluginState.REGISTERED
    assert entry.capabilities[0].provides == "sample-capability"
    assert entry.plugin.initialized_with is plugin_context  # type: ignore[attr-defined]


def test_load_all_isolates_invalid_manifest(plugin_context: PluginContext) -> None:
    bad_manifest = make_manifest(name="Bad Name!")
    descriptor = PluginDescriptor(manifest=bad_manifest, factory=RecordingPlugin)
    manager = PluginManager()

    report = manager.load_all([StaticPluginSource([descriptor])], plugin_context)

    assert report.registered == []
    assert report.failed[0].name == "Bad Name!"
    assert report.failed[0].stage == PluginState.VALIDATED


def test_load_all_isolates_incompatible_api_version(plugin_context: PluginContext) -> None:
    manifest = make_manifest(name="future-plugin", api_version="99.0")
    descriptor = PluginDescriptor(manifest=manifest, factory=RecordingPlugin)
    manager = PluginManager()

    report = manager.load_all([StaticPluginSource([descriptor])], plugin_context)

    assert report.registered == []
    assert report.failed[0].name == "future-plugin"
    assert report.failed[0].stage == PluginState.VALIDATED


def test_load_all_isolates_construction_failure(plugin_context: PluginContext) -> None:
    manager = PluginManager()

    report = manager.load_all(_source_for(FailingConstructionPlugin), plugin_context)

    assert report.registered == []
    assert report.failed[0].stage == PluginState.LOADED
    assert "boom during construction" in report.failed[0].error


def test_load_all_isolates_initialize_failure(plugin_context: PluginContext) -> None:
    manager = PluginManager()

    report = manager.load_all(_source_for(FailingInitializePlugin), plugin_context)

    assert report.registered == []
    assert report.failed[0].stage == PluginState.INITIALIZED
    assert "failing-initialize" not in manager.registry


def test_load_all_isolates_register_failure(plugin_context: PluginContext) -> None:
    manager = PluginManager()

    report = manager.load_all(_source_for(FailingRegisterPlugin), plugin_context)

    assert report.registered == []
    assert report.failed[0].stage == PluginState.REGISTERED
    assert "failing-register" not in manager.registry


def test_load_all_isolates_duplicate_across_sources(plugin_context: PluginContext) -> None:
    manager = PluginManager()

    report = manager.load_all(_source_for(RecordingPlugin, RecordingPlugin), plugin_context)

    assert len(report.registered) == 1
    assert len(report.failed) == 1
    assert report.failed[0].stage == PluginState.REGISTERED


def test_load_all_continues_after_a_failure(plugin_context: PluginContext) -> None:
    manager = PluginManager()

    report = manager.load_all(_source_for(FailingInitializePlugin, RecordingPlugin), plugin_context)

    assert len(report.registered) == 1
    assert report.registered[0].manifest.name == "sample-plugin"
    assert len(report.failed) == 1
    assert report.failed[0].name == "failing-initialize"


def test_shutdown_all_calls_shutdown_on_every_registered_plugin(
    plugin_context: PluginContext,
) -> None:
    manager = PluginManager()
    manager.load_all(_source_for(RecordingPlugin), plugin_context)

    failures = manager.shutdown_all()

    assert failures == []
    entry = manager.registry.get("sample-plugin")
    assert entry.plugin.shut_down is True  # type: ignore[attr-defined]
    assert entry.state == PluginState.SHUTDOWN


def test_shutdown_all_isolates_failures(plugin_context: PluginContext) -> None:
    manager = PluginManager()
    manager.load_all(_source_for(FailingShutdownPlugin), plugin_context)

    failures = manager.shutdown_all()

    assert len(failures) == 1
    assert failures[0].name == "failing-shutdown"
    entry = manager.registry.get("failing-shutdown")
    assert entry.state == PluginState.FAILED
