# Architecture Decision Records

An ADR captures a single significant architectural decision, the context that
drove it, the decision itself, alternatives considered, and consequences.

Accepted ADRs describe the design contract currently guiding implementation. If
a decision changes later, prefer adding a new ADR that supersedes the old one so
the historical reasoning stays visible.

## Log

| ID | Title | Status |
| --- | --- | --- |
| [ADR-001](0001-graph-first-architecture.md) | Graph-first Architecture | Accepted |
| [ADR-002](0002-intermediate-representation.md) | Intermediate Representation | Accepted |
| [ADR-003](0003-plugin-system.md) | Plugin System | Accepted |
| [ADR-004](0004-storage-backend.md) | Storage Backend | Accepted |
| [ADR-005](0005-parser-interface.md) | Parser Interface | Accepted |

## Current Decision Summary

RIG currently follows these core decisions:

- The engineering graph is the canonical repository intelligence model.
- Language-specific parsers feed a language-neutral repository IR before graph
  construction.
- Plugins use explicit manifests, lifecycle hooks, capability declarations, and
  managed discovery/registration.
- Persistent storage is deferred while the graph contract stabilizes; the
  current backend is an in-memory graph with deterministic serialization.
- Parser implementations share a language-agnostic parse context/result
  contract, with Tree-sitter Go support as the first concrete parser backend.

## Writing a New ADR

Copy [`template.md`](template.md) to `docs/adr/NNNN-title.md`, using the next
sequential number, then add a row to the log above.
