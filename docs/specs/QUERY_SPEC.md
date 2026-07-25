# QUERY_SPEC.md

> **Repository Intelligence Graph (RIG)**
>
> Version: 0.1.0
> Status: Draft
> Authors: RIG Contributors

---

# 1. Introduction

The Query Engine is the primary interface for interacting with the Repository Intelligence Graph.

It enables developers, IDEs, AI systems, CI pipelines, and third-party tools to retrieve engineering knowledge without understanding the internal graph representation.

The Query Engine acts as the "SQL layer" of RIG.

---

# 2. Purpose

The Query Engine provides a unified mechanism to:

- Search repositories
- Traverse relationships
- Analyze dependencies
- Retrieve architecture
- Perform impact analysis
- Discover ownership
- Support AI context generation

The underlying graph implementation is completely hidden from clients.

---

# 3. Design Goals

The Query Engine should be:

- Storage agnostic
- Language agnostic
- Deterministic
- Extensible
- Composable
- Efficient
- Easy to embed
- AI-friendly

---

# 4. Non Goals

The Query Engine is **not**

- A graph database
- A storage engine
- A search index
- A visualization engine
- A query planner

Those responsibilities belong to separate components.

---

# 5. Architecture

```
             Applications

      CLI
      SDK
      REST API
      VS Code
      AI Agents

              │

              ▼

        Query Engine

              │

              ▼

     Repository Graph

              │

              ▼

      Graph Storage Layer
```

Every consumer communicates through the Query Engine.

---

# 6. Query Pipeline

```
Client

↓

Request

↓

Validation

↓

Optimization

↓

Execution

↓

Result Formatting

↓

Response
```

Every query follows this lifecycle.

---

# 7. Query Types

RIG supports five categories of queries.

## Lookup

Retrieve a single entity.

Example

```
Service("auth")
```

---

## Traversal

Walk graph relationships.

Example

```
Service

↓

Endpoints

↓

Functions
```

---

## Search

Locate entities.

Examples

```
Search("login")

Search(type="Service")

Search(owner="Platform")
```

---

## Analysis

Perform graph computations.

Examples

- Dependency analysis
- Circular dependency detection
- Impact analysis
- Ownership analysis

---

## Aggregation

Generate statistics.

Examples

```
Functions per module

Services per repository

Dependencies by language

Largest package

Most connected node
```

---

# 8. Query Model

Every query contains

```
Target

Filters

Traversal

Projection

Pagination
```

Queries are immutable.

---

# 9. Entity Queries

Retrieve nodes.

Examples

```
Repository

Package

Module

File

Class

Function

API

Service

Database

Queue
```

---

# 10. Relationship Queries

Retrieve graph relationships.

Examples

```
CALLS

IMPORTS

USES

DEPENDS_ON

CONTAINS

READS

WRITES

OWNS
```

---

# 11. Traversal API

Traversal begins from a node.

Example

```
Service

↓

Endpoints

↓

Functions

↓

Dependencies
```

Traversal supports

- Depth limits
- Direction
- Filters
- Cycle detection

---

# 12. Filtering

Supported filters

```
Type

Language

Framework

Owner

Visibility

Version

Metadata

Tags
```

Example

```
Functions

WHERE

language = "Python"

AND

visibility = "public"
```

---

# 13. Sorting

Results may be sorted by

```
Name

Created Time

Updated Time

Degree

Weight

Version
```

Sorting is stable.

---

# 14. Pagination

Large result sets support

```
Offset

Limit

Cursor
```

Cursor pagination is preferred.

---

# 15. Graph Algorithms

The Query Engine provides built-in graph algorithms.

Examples

- Shortest Path
- Reachability
- Connected Components
- Dependency Tree
- Cycle Detection
- Topological Sort
- Dominator Analysis
- Centrality

Plugins may register additional algorithms.

---

# 16. Impact Analysis

Impact analysis determines what may be affected by a change.

Example

```
Function

↓

Callers

↓

Services

↓

APIs

↓

Deployments
```

Useful for

- Refactoring
- CI
- Pull Requests
- AI Planning

---

# 17. Dependency Analysis

Examples

```
Module

↓

Imports

↓

Packages

↓

External Libraries
```

Supports

- Dependency trees
- Circular dependency detection
- Dependency depth
- Unused dependencies

---

# 18. Search

Supports

- Exact search
- Prefix search
- Fuzzy search
- Metadata search
- Full-text search
- Symbol search

Future versions may include semantic search.

---

# 19. AI Context Queries

Specialized queries provide structured context for AI systems.

Examples

```
Context(Service)

Context(Function)

Context(API)

Context(Module)
```

Returned information may include

- Description
- Dependencies
- Call graph
- Ownership
- Documentation
- Recent commits
- Review history
- Architecture references

---

# 20. Result Model

Every response includes

```json
{
  "nodes": [],
  "edges": [],
  "metadata": {},
  "statistics": {}
}
```

Responses are immutable.

---

# 21. Query Optimization

Before execution

```
Validate

↓

Optimize

↓

Execute
```

Possible optimizations

- Predicate pushdown
- Index utilization
- Traversal pruning
- Duplicate elimination
- Cache reuse

---

# 22. Caching

Queries may be cached.

Cache keys include

- Query
- Graph version
- Parameters

Cache invalidation occurs after graph updates.

---

# 23. Error Handling

Errors are classified as

```
Validation Error

Execution Error

Timeout

Permission Error

Internal Error
```

Partial results may be returned when safe.

---

# 24. Security

Queries operate in read-only mode.

Restrictions

- No graph mutation
- No repository modification
- No arbitrary execution

Future versions may introduce role-based authorization.

---

# 25. Performance Objectives

The Query Engine should

- Support large monorepos
- Execute incrementally
- Reuse indexes
- Optimize traversals
- Parallelize independent work
- Minimize memory usage

---

# 26. Language Bindings

The Query Engine should be accessible through

- Rust SDK
- Python SDK
- TypeScript SDK
- REST API
- CLI

Future

- Go SDK
- Java SDK
- GraphQL

---

# 27. REST Mapping

Every query type maps cleanly to REST.

Examples

```
GET /repositories

GET /services

GET /functions

GET /dependencies

GET /impact

GET /context
```

REST is an interface, not the query language itself.

---

# 28. SDK Mapping

Example

```python
service = rig.service("auth")

service.dependencies()

service.endpoints()

service.call_graph()

service.context()
```

Example

```typescript
const auth = rig.service("auth")

await auth.dependencies()

await auth.context()
```

SDKs expose typed interfaces built on the Query Engine.

---

# 29. Extension Model

Plugins may contribute

- New query operators
- New graph algorithms
- New filters
- New result projections
- New AI context providers

Existing query semantics must remain unchanged.

---

# 30. Versioning

The Query Engine follows Semantic Versioning.

Breaking changes require a major version.

New operators are additive.

Deprecated APIs remain supported for at least one major release.

---

# 31. Related Specifications

The Query Engine consumes

- GRAPH_SCHEMA.md
- IR_SPEC.md

The Query Engine is extended by

- PLUGIN_SPEC.md

The Query Engine is defined within the architecture described by

- ARCHITECTURE.md

---

# 32. Future Directions

Planned capabilities include

- Natural language querying
- GraphQL interface
- AI-assisted query planning
- Multi-repository traversal
- Runtime telemetry queries
- Engineering analytics
- Historical graph queries
- Temporal graph analysis

These additions should preserve backward compatibility.

---

# 33. Conclusion

The Query Engine provides the canonical interface for interacting with the Repository Intelligence Graph.

By abstracting graph storage and exposing a consistent, extensible query model, it enables developers, AI systems, and engineering tools to retrieve structured software knowledge efficiently.

Every consumer—from the CLI to future AI agents—interacts with RIG through the Query Engine, making it the primary access layer for Engineering Intelligence.
