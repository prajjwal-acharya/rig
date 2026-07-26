# ADR-001: Graph-first Architecture

## Status

Accepted

## Date

2026-07-27

## Context

rig transforms repositories into queryable engineering graphs. The core data
model choice shapes every downstream component: parsers, IR builders, symbol
resolution, semantic analysis, storage, query APIs, and CLI output.

The repository now contains a concrete in-memory graph implementation in
`rig.graph`. Graph builders create nodes and edges from repository IR, then
later stages enrich the same graph with imports, references, calls, type
relationships, and dependencies.

The project needs a model that can represent both structural facts, such as
"repository contains package", and semantic facts, such as "function calls
function" or "type embeds type".

## Decision

Use a directed property graph as the canonical repository intelligence model.

The current implementation reflects this decision through:

- `Graph`, `Node`, `Edge`, and `GraphMetadata` value objects.
- Open-ended node `type` strings so new graph builders can introduce new node
  kinds without changing the core model.
- A shared `RelationshipType` enum for known relationship families, including
  `CONTAINS`, `DECLARES`, `IMPORTS`, `REFERENCES`, `CALLS`, `DEPENDS_ON`,
  `IMPLEMENTS`, `EXTENDS`, `EMBEDS`, `ALIASES`, and type-specific
  relationships.
- Immutable `Properties` attached to nodes, edges, and metadata.
- Deterministic graph and edge identifiers.
- `GraphIndex` as a read-optimized lookup view over an already-built graph.
- Graph builders and analyses that return enriched graph values rather than
  mutating global state.

The graph is produced after scanning, parsing, IR construction, symbol table
construction, reference resolution, and type indexing. Analysis modules then
enrich the graph with additional semantic relationships.

## Alternatives Considered

### Relational schema

A relational schema would make tabular reporting straightforward, but it would
force relationship traversal into joins and would make extensible relationship
types more rigid.

### Document index

A document index would be simple to serialize and search, but it would not make
relationships first-class. Impact analysis, dependency analysis, and graph
traversal would require secondary indexes that effectively recreate a graph.

### AST-first model

Using parser ASTs as the primary model would preserve maximum syntax detail,
but it would couple downstream systems to parser-specific tree shapes and make
multi-language analysis harder.

## Consequences

Graph-first modeling makes relationship-driven workflows natural:

- architecture queries
- dependency traversal
- call graph generation
- type relationship analysis
- reference lookup
- future query and visualization layers

It also introduces responsibilities:

- graph IDs must remain deterministic
- graph builders must avoid duplicate nodes and edges
- relationship semantics must stay documented
- storage and query layers must preserve graph meaning rather than flattening it

The graph should remain the system-of-record for repository intelligence, while
ASTs and IR remain pipeline inputs used to produce and enrich that graph.
