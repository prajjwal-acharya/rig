# Commit History

This page summarizes the project work represented by every commit currently
reachable from `main`. It was prepared from the tracked repository files and
the git log through commit `8e81b27` on 2026-07-27.

## Timeline

| Commit | Date | Summary |
| --- | --- | --- |
| `f033807` | 2026-07-25 | Created the repository baseline with ignore rules, Apache-2.0 licensing, and a minimal README. |
| `1f404ee` | 2026-07-26 | Added the first documentation foundation: architecture specs, graph schema, IR, plugin, query specs, and ADR placeholders. |
| `c5842b6` | 2026-07-26 | Added project scaffolding for Python packaging, CI, pre-commit, MkDocs, contribution docs, changelog, and initial tests. |
| `7499726` | 2026-07-26 | Introduced repository scanning, ignore handling, metadata collection, plugin infrastructure, and the first CLI scan command. |
| `ac6901f` | 2026-07-26 | Added the language registry and language-agnostic parser framework with parser managers, stubs, and parsing pipeline tests. |
| `8e81b27` | 2026-07-27 | Built out the current compiler-style pipeline: Tree-sitter Go parsing, IR, symbols, references, types, graph generation, semantic analyses, and expanded CLI commands. |

## Commit Details

### `f033807` - Initial Commit

The first commit established the repository shell.

- Added `.gitignore` rules for common operating system, editor, Python, build,
  virtual environment, and cache artifacts.
- Added the Apache-2.0 `LICENSE`.
- Added a minimal `README.md` describing rig as a tool that transforms
  repositories into queryable engineering graphs.

### `1f404ee` - Documentation Foundation

This commit made the repository specification-driven before implementation
began.

- Added the documentation homepage at `docs/index.md`.
- Added core specs under `docs/specs`:
  - `ARCHITECTURE.md`
  - `GRAPH_SCHEMA.md`
  - `IR_SPEC.md`
  - `PLUGIN_SPEC.md`
  - `QUERY_SPEC.md`
- Added ADR structure under `docs/adr`, including the ADR index, template, and
  initial records for graph-first architecture, IR, plugins, storage, and parser
  interface decisions.

The specs describe the intended architecture: repository scanner, language
parsers, intermediate representation, graph generation, query layer, plugin
model, and future storage/query surfaces.

### `c5842b6` - Project Scaffolding

This commit turned the documentation repository into a runnable Python project.

- Added `pyproject.toml` with package metadata, Python `>=3.10`, development
  tooling groups, the `rig` console script, Ruff, pytest, and mypy settings.
- Added `uv.lock` to lock the dependency graph.
- Added `.editorconfig` and `.pre-commit-config.yaml`.
- Added GitHub issue templates, pull request template, and CI workflow.
- Added contributor-facing files: `CHANGELOG.md`, `CONTRIBUTING.md`,
  `CODE_OF_CONDUCT.md`, and `SECURITY.md`.
- Created empty `examples`, `scripts`, `rig`, and `tests` roots.
- Added a placeholder test so CI had a runnable starting point.
- Added `mkdocs.yml` to publish the documentation site.

### `7499726` - Scanner, Plugin System, and Initial CLI

This commit added the first functional implementation layer.

- Added the `rig.scanner` package:
  - repository path location and git-root discovery
  - recursive file walking
  - `.gitignore` and optional hidden-file filtering
  - metadata collection for size, timestamps, checksums, and hidden status
  - repository snapshots and statistics
- Added the `rig.plugins` package:
  - plugin manifests and compatibility checks
  - plugin lifecycle interface
  - plugin registry and capability lookup
  - static and entry-point discovery sources
  - plugin loading reports and isolated failure handling
- Added the first CLI implementation for `rig scan`.
- Added test suites for scanner behavior, plugin behavior, and CLI scan output.

At this point the CLI lived in a single `rig/cli.py` module. A later commit
reorganized it into the current `rig/cli` package.

### `ac6901f` - Language and Parser Framework

This commit introduced a language-aware parsing layer while keeping parser
implementations replaceable.

- Added `rig.languages`:
  - immutable `Language` model
  - default registry for common languages and file extensions
  - language detection for scanned files
  - repository language reports and aggregate counts
- Added `rig.parsers`:
  - parser interface
  - parser registry and duplicate checks
  - parser manager
  - parse context, result, and diagnostic models
  - repository file parsing pipeline
  - stub parsers for early Go and Python parsing coverage
- Extended the CLI beyond scanning so later pipeline stages could build on the
  same scan/detect/parse flow.
- Added dedicated tests for language detection, parser registration, parser
  management, parser results, stubs, and pipeline behavior.

The important design outcome was that language detection, parser selection, and
parse result handling became independent from any specific parsing backend.

### `8e81b27` - Compiler Pipeline and Semantic Analysis

This commit is the largest implementation step so far. It converted the early
scanner/parser project into a multi-stage repository analysis pipeline.

- Replaced the single-file CLI module with the current `rig/cli` package:
  - `scan`
  - `detect`
  - `parse`
  - `ir`
  - `symbols`
  - `references`
  - `types`
  - `graph`
  - `analyze`
  - `stats`
- Added Tree-sitter parsing support:
  - grammar registry
  - reusable backend
  - Go grammar adapter
  - syntax tree and syntax node wrappers
  - traversal helpers
  - parser factory that combines real Tree-sitter parsers with stubs
- Added the IR layer:
  - source locations
  - declaration models for functions, types, variables/constants, and imports
  - file and package models
  - deterministic identifiers
  - repository IR builder
  - Go IR builder for Tree-sitter syntax trees
- Added symbol support:
  - repository, package, and file scopes
  - function, type, variable, constant, and package symbols
  - deterministic symbol IDs
  - symbol table, visitor, resolver, diagnostics, and Go symbol builder
- Added reference resolution:
  - resolved and unresolved reference models
  - reference index
  - deterministic reference IDs
  - Go reference resolver
  - graph enrichment with `REFERENCES` edges
- Added type modeling:
  - struct, interface, alias, and named type models
  - type index and resolver
  - Go type builder and diagnostics
- Added graph support:
  - graph node, edge, metadata, and index models
  - relationship enum covering structural and semantic relationships
  - graph properties and JSON serialization
  - graph builder registry and accumulator
  - structural graph builder
  - import graph builder
- Added semantic analysis support:
  - analysis interface, context, registry, manager, result, capabilities, and
    diagnostics
  - call graph analysis
  - type relationship analysis
  - dependency analysis
  - sequential CLI orchestration that threads graph-enriching analysis results
    through the full pipeline
- Added `tree-sitter` and `tree-sitter-go` runtime dependencies.
- Added broad unit and integration coverage for the new packages and CLI
  pipeline stages.

## Current Implementation Snapshot

The current repository is a Python package named `rig` at version `0.1.0`.
The implemented pipeline is:

```text
repository path
-> locate repository
-> walk files
-> apply ignore rules
-> collect metadata
-> detect languages
-> parse files
-> build repository IR
-> build symbol table
-> resolve references
-> build type index
-> build structural/import/reference graph
-> run call graph, type relationship, and dependency analyses
-> report through the CLI
```

The main implementation packages are:

| Package | Current role |
| --- | --- |
| `rig.scanner` | Locates repositories, walks files, applies ignore rules, collects metadata, and builds snapshots. |
| `rig.languages` | Defines language metadata, extension/filename mappings, detection, and language statistics. |
| `rig.parsers` | Defines parser contracts, parser registries/managers, parse results, stubs, and Tree-sitter integration. |
| `rig.ir` | Defines the repository intermediate representation and Go IR builder. |
| `rig.symbols` | Builds scoped symbol tables and resolves names within repository/package/file scope boundaries. |
| `rig.references` | Resolves identifier references and enriches graphs with reference edges. |
| `rig.types` | Builds and indexes Go type information. |
| `rig.graph` | Defines the in-memory graph model, builders, properties, identifiers, serialization, and traversal helpers. |
| `rig.analysis` | Runs graph-enriching analyses for calls, type relationships, and dependencies. |
| `rig.plugins` | Provides plugin manifest, discovery, registry, context, manager, lifecycle, and capability primitives. |
| `rig.cli` | Exposes the scanner-to-analysis pipeline through the `rig` command. |

## CLI Surface

The current console script is `rig = "rig.cli:main"`. Available commands are:

| Command | Purpose |
| --- | --- |
| `rig scan [path]` | Scan files, report ignored entries, language counts, plugin loading, and optional per-file metadata. |
| `rig detect [path]` | Scan and report language percentages and file counts. |
| `rig parse [path]` | Scan, detect, parse, and report parser usage and syntax diagnostics. |
| `rig ir [path]` | Build repository IR and report packages, files, declarations, and diagnostics. |
| `rig symbols [path]` | Build the symbol table and report scopes, symbol kinds, and duplicate diagnostics. |
| `rig references [path]` | Resolve references and report resolution totals and diagnostics. |
| `rig types [path]` | Build the type index and report type categories and diagnostics. |
| `rig graph [path]` | Build the knowledge graph, run semantic analyses, and report nodes, edges, and relationships. |
| `rig analyze [path]` | Run the full compiler pipeline and print a high-level repository analysis summary. |
| `rig stats [path]` | Print repository-wide statistics across IR, symbols, references, types, graph, and analyses. |

## Test and Tooling Coverage

The repository now includes focused tests across all implemented subsystems:

- scanner tests for walking, ignore behavior, repository location, metadata, and
  snapshots
- plugin tests for manifests, lifecycle, discovery, registry, manager behavior,
  and failure isolation
- language tests for model normalization, catalog coverage, detection,
  registry behavior, pipeline reports, and statistics
- parser tests for registries, managers, stubs, parse models, parse pipeline,
  Tree-sitter backend, grammar registry, parser factory, traversal, and Go
  integration
- IR tests for models, identifiers, builders, repository assembly, visitor, and
  Go extraction
- graph tests for models, properties, identifiers, serialization, registries,
  accumulators, structural graph building, import graph enrichment, and
  integration behavior
- symbol tests for scopes, symbols, identifiers, builder behavior, table
  indexing, resolver behavior, visitor, and integration
- reference tests for models, identifiers, indexes, resolver behavior, graph
  enrichment, diagnostics, and integration
- type tests for models, identifiers, indexes, resolver, builder behavior,
  diagnostics, visitor, and integration
- analysis tests for context, capabilities, registry, manager execution,
  results, diagnostics, call graph, type relationships, dependency analysis,
  and end-to-end semantic analysis
- CLI tests for scan behavior and full pipeline command output

CI runs Ruff, mypy, pytest, and pre-commit through `uv`.

## Documentation State

The documentation was created before most implementation work. As of
`8e81b27`, the codebase has advanced beyond parts of the original draft specs.

Important follow-ups for future documentation work:

- Update architecture docs to reflect the implemented Python package layout.
- Clarify which spec areas are implemented now and which remain planned.
- Replace ADR placeholders with accepted decisions and rationale.
- Document the concrete Go/Tree-sitter pipeline separately from planned
  language support.
- Add user-facing CLI examples for each command.
- Add extension guides for parser, graph builder, analysis, and plugin authors.
