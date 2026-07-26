# ADR-004: Storage Backend

## Status

Accepted

## Date

2026-07-27

## Context

The engineering graph eventually needs persistence, indexing, and efficient
queries at repository scale. Early implementation work, however, is focused on
getting the scanner, parser, IR, graph, and semantic analysis contracts correct.

The current repository contains an in-memory graph model and deterministic JSON
serialization helpers, but it does not yet include a persistent graph database,
SQLite schema, external graph store, or query engine implementation.

## Decision

Use an in-memory graph model for the current phase and defer selection of a
persistent storage backend.

The current storage boundary is:

- `Graph`, `Node`, `Edge`, `GraphMetadata`, and `Properties` as immutable
  in-memory values.
- `GraphIndex` for fast lookup over a built graph.
- `graph_to_dict` and `graph_to_json` for deterministic serialization.
- Deterministic identifiers so persisted graph records can be compared and
  incrementally updated in a future backend.

No storage backend is selected yet. Future storage work should preserve the
graph model and introduce persistence behind a storage/query abstraction rather
than changing analysis code to depend on a specific database.

## Alternatives Considered

### SQLite-backed graph tables

SQLite would be local-first, portable, and easy to ship, but choosing the schema
too early could freeze graph and query assumptions before the pipeline settles.

### Embedded graph database

An embedded graph database may eventually fit traversal-heavy workloads, but it
would add operational and dependency weight before the graph contract is stable.

### External graph database

External graph databases are powerful for large deployments, but they conflict
with the project's local-first starting point and would complicate early
developer setup.

### JSON files only

JSON serialization is useful for snapshots, tests, and interchange, but it is
not enough by itself for indexed queries or incremental updates at scale.

## Consequences

Deferring persistent storage keeps early development fast and lets the graph,
IR, and analysis contracts stabilize first. Tests can operate on plain value
objects, and the CLI can report pipeline output without requiring a database.

The tradeoff is that current graph results are ephemeral unless explicitly
serialized by a caller. Query performance, incremental persistence, history, and
large-repository storage remain future work.

When storage is added, the chosen backend must support deterministic graph IDs,
node and edge properties, relationship traversal, metadata, versioning, and
incremental updates.
