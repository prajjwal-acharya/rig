# ADR-002: Intermediate Representation

## Status

Accepted

## Date

2026-07-27

## Context

Language parsers expose different syntax tree shapes and naming conventions.
Graph builders and semantic analyses need a stable input that is not coupled to
Tree-sitter, Go syntax, Python syntax, or any other language-specific AST.

The current codebase includes parser results in `rig.parsers`, a Tree-sitter
Go parser, and a concrete repository IR in `rig.ir`. The IR is the boundary
between parsing and repository intelligence.

## Decision

Use a language-neutral repository IR between parser output and graph
construction.

The current IR captures:

- source locations with line, column, and optional byte offsets
- repositories
- packages
- files
- declarations
- function declarations
- type declarations
- variable and constant declarations
- import declarations

Each language adds an `IRBuilder` implementation that maps parser output into
this common model. The current implementation includes `GoIRBuilder`.

The IR intentionally does not own every semantic index. Symbols, references,
types, and graph relationships are derived downstream by dedicated packages:

- `rig.symbols` builds scoped symbol tables from IR
- `rig.references` resolves identifier references against symbols and syntax
  trees
- `rig.types` builds type indexes from IR and symbols
- `rig.graph` turns IR and semantic indexes into graph nodes and edges
- `rig.analysis` enriches the graph with higher-level semantic relationships

This keeps the IR small enough to be a stable cross-language contract while
leaving richer analysis to specialized stages.

## Alternatives Considered

### Direct AST-to-graph construction

Directly building graphs from parser ASTs would reduce one pipeline stage, but
it would make graph builders language-specific and harder to test.

### Large semantic IR

Embedding symbols, references, type relationships, and dependency edges
directly in the IR would centralize information, but it would make the IR harder
to evolve and would blur the boundary between extraction and analysis.

### Per-language IR models

Per-language IRs would preserve each language's syntax more precisely, but they
would make graph construction and cross-language analysis less consistent.

## Consequences

The IR gives graph builders and semantic analyzers a stable input contract.
Adding language support requires an IR builder for that language, not a rewrite
of downstream graph logic.

The tradeoff is that language-specific detail can be lost if the IR model is
too narrow. New declaration kinds or metadata should be added carefully when
multiple pipeline stages need them, and language-specific details should remain
in parser syntax trees until the common model requires them.
