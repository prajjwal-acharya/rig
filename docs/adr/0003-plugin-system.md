# ADR-003: Plugin System

## Status

Accepted

## Date

2026-07-27

## Context

rig needs to grow across languages, frameworks, infrastructure providers,
analysis modules, visualization surfaces, export formats, and query systems.
Those extensions should not require every contribution to edit the same central
files.

The repository now includes foundational plugin primitives in `rig.plugins`.
Some core pipeline stages are still wired directly, but the plugin model defines
the extension boundary the project will build toward.

## Decision

Provide an in-process plugin system with explicit manifests, lifecycle hooks,
capability declarations, discovery sources, registration, and isolated failure
handling.

The current plugin system includes:

- `PluginManifest` with `name`, `version`, `type`, `api_version`,
  description, author, and optional rig version bounds.
- `PluginType` categories for language, framework, infrastructure,
  intelligence, visualization, export, and query plugins.
- API compatibility checks based on major `api_version` compatibility.
- A `Plugin` interface with `initialize`, `register`, and `shutdown` hooks.
- `Capability` objects describing what a plugin provides, consumes, and
  produces.
- `PluginContext` for snapshots, config, logging, and cache access.
- `PluginRegistry` for registered plugin instances and capability lookup.
- Static and Python entry-point discovery sources.
- `PluginManager` load and shutdown flows that isolate invalid manifests,
  incompatible API versions, construction errors, lifecycle errors, duplicate
  plugins, and shutdown failures.

Plugins run in-process for the current phase. Process isolation or sandboxing
can be added later for untrusted plugin execution if the project needs it.

## Alternatives Considered

### Central registries only

Hard-coded central registries are simple early on, but every extension would
require editing core package code.

### Configuration-only plugins

Configuration-only plugin loading is useful for simple adapters, but it cannot
express lifecycle, registration, capabilities, diagnostics, or richer extension
behavior.

### Out-of-process plugins from the start

Out-of-process plugins provide stronger isolation, but they add serialization,
process management, version negotiation, and debugging complexity before the
extension contracts are stable.

## Consequences

The plugin foundation makes extension points explicit and testable. Plugin
authors get a clear manifest and lifecycle contract, while rig can report
partial failures instead of crashing the whole load process.

The tradeoff is that the current in-process model trusts plugin code. Future
work must define stronger isolation if plugins are installed from untrusted
sources or run in enterprise environments with stricter security requirements.

The core pipeline should continue moving direct registrations toward plugin
registries where doing so improves extensibility without obscuring simple core
behavior.
