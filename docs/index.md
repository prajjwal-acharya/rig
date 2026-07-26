# Repository Intelligence Graph (RIG)

Welcome to the official documentation for **Repository Intelligence Graph
(RIG)**.

RIG transforms repositories into structured, queryable engineering graphs. The
documentation captures both the design intent and the implementation history so
contributors can understand where the project came from and what exists today.

## Documentation Structure

The documentation is organized into three primary sections.

### Architecture Specifications

The specification documents define the technical blueprint of RIG. These
documents describe the intended system design, interfaces, contracts, and
constraints.

Current specifications include:

- **System Architecture** - Overall system design, component responsibilities,
  and development roadmap.
- **Graph Schema** - Definition of the engineering graph, including nodes,
  edges, metadata, and graph invariants.
- **Intermediate Representation (IR)** - Canonical representation produced by
  parsers before graph construction.
- **Plugin Specification** - Contracts for parser plugins, lifecycle,
  registration, and extensibility.
- **Query Specification** - Public query interface intended for CLI, SDK, REST
  API, visualization, and future AI systems.

### Architecture Decision Records

Architecture Decision Records (ADRs) document important technical decisions
made during development. Each ADR captures the problem being solved, the
surrounding context, the chosen solution, alternatives considered, and long-term
consequences.

Unlike the specification documents, ADRs explain why the system was designed a
particular way.

### Development History

The development history records what each commit has added so far. It connects
the current file tree to the git history, including the transition from early
repository scaffolding to the implemented scanner, parser, IR, graph, semantic
analysis, and CLI pipeline.

Start with [Commit History](development/commit-history.md) when you want to
understand how the current codebase evolved.

## Current Status

RIG is in an early implementation phase. The repository now includes:

- Python package scaffolding, CI, pre-commit, tests, and MkDocs configuration.
- Repository scanning with ignore handling and file metadata collection.
- Plugin primitives for manifests, discovery, lifecycle management, registry,
  context, capabilities, and load reporting.
- Language detection and a language-agnostic parser framework.
- Tree-sitter-backed Go parsing.
- Repository IR, symbol table construction, reference resolution, type
  indexing, graph construction, and graph enrichment.
- Semantic analyses for call graphs, type relationships, and dependencies.
- CLI commands for each pipeline stage: `scan`, `detect`, `parse`, `ir`,
  `symbols`, `references`, `types`, `graph`, `analyze`, and `stats`.

Some existing specifications still describe planned future capabilities or
draft architecture. Treat this documentation as both a design reference and a
living record of implementation progress.

## Recommended Reading Order

If you are new to the project, read in this order:

1. [Commit History](development/commit-history.md)
2. [System Architecture](specs/ARCHITECTURE.md)
3. [Graph Schema](specs/GRAPH_SCHEMA.md)
4. [Intermediate Representation](specs/IR_SPEC.md)
5. [Plugin Specification](specs/PLUGIN_SPEC.md)
6. [Query Specification](specs/QUERY_SPEC.md)
7. [Architecture Decision Records](adr/index.md)

## Guiding Principles

The project is built around a small set of core principles:

- **Local-First** - Core functionality should work without cloud services.
- **Graph-First** - The engineering graph is the primary source of truth.
- **Plugin-First** - Language and infrastructure support should be extensible.
- **Specification-Driven** - Architecture and interfaces are documented as the
  project evolves.
- **Incremental by Design** - Changes should update affected portions of the
  graph rather than requiring full reconstruction.

## Contributing

Before contributing to RIG, read the relevant specs, ADRs, and development
history. Together they show both the target architecture and the implementation
already present in the repository.
