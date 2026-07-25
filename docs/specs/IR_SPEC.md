# IR_SPEC.md

> **Repository Intelligence Graph (RIG)**
>
> Version: 0.1.0
> Status: Draft
> Authors: RIG Contributors

---

# 1. Introduction

The **Intermediate Representation (IR)** is the canonical internal representation used by RIG.

Every parser converts source artifacts into IR.

Every downstream component consumes IR.

No component communicates directly with language-specific parsers.

The IR provides a stable contract between parsing and graph generation, similar to how LLVM IR separates frontends from backends.

---

# 2. Purpose

The IR exists to decouple language parsing from graph generation.

Instead of every analysis tool understanding every programming language, they only understand the IR.

```
Repository

↓

Language Parser

↓

Intermediate Representation (IR)

↓

Graph Generation

↓

Repository Graph
```

---

# 3. Design Goals

The IR must be:

- Language agnostic
- Deterministic
- Extensible
- Serializable
- Incrementally updatable
- Easy to validate
- Rich enough for semantic analysis
- Independent of storage

---

# 4. Non Goals

The IR is **not**:

- An Abstract Syntax Tree (AST)
- A graph database format
- A compiler IR
- An executable representation
- A runtime model

The IR captures **engineering semantics**, not execution semantics.

---

# 5. Pipeline

```
Repository

↓

Scanner

↓

Language Parser

↓

AST

↓

IR

↓

Graph Generator

↓

Repository Graph
```

Every parser MUST emit valid IR.

Every graph builder MUST consume only IR.

---

# 6. Core Model

The IR consists of four primary elements.

```
IR

├── Entities
├── Relationships
├── Metadata
└── Source Locations
```

---

# 7. Entity Model

An Entity represents any identifiable engineering artifact.

Examples

- Repository
- Package
- Module
- File
- Class
- Function
- API
- Service
- Database
- Queue

Every entity is immutable during one compilation cycle.

---

## Entity Structure

```json
{
  "id": "entity.function.login",
  "kind": "Function",
  "name": "login",
  "language": "Python",
  "metadata": {}
}
```

---

# 8. Relationship Model

Relationships connect entities.

Examples

```
CALLS

IMPORTS

USES

DEPENDS_ON

CONTAINS

OWNS

IMPLEMENTS
```

---

## Relationship Structure

```json
{
  "id": "rel001",
  "type": "CALLS",
  "source": "entity.login",
  "target": "entity.verify_token",
  "metadata": {}
}
```

---

# 9. Metadata Model

Metadata stores language-specific or framework-specific information.

Example

```json
{
  "framework": "FastAPI",
  "async": true,
  "visibility": "public"
}
```

Metadata is optional.

Unknown metadata MUST NOT invalidate IR.

---

# 10. Source Locations

Every entity may reference its source.

```json
{
  "file": "auth/login.py",
  "line": 34,
  "column": 12,
  "endLine": 61
}
```

Purpose

- IDE integration
- Error reporting
- Graph navigation
- Visualization

---

# 11. Entity Types

The IR supports the following core entity kinds.

```
Repository

Package

Module

File

Namespace

Class

Interface

Struct

Enum

Function

Variable

Constant

Service

API

Endpoint

Database

Table

Queue

Topic

Pipeline

Workflow

Documentation

Dependency

Configuration
```

Plugins may extend this list.

---

# 12. Relationship Types

Core relationships include

```
CONTAINS

CALLS

IMPORTS

USES

READS

WRITES

PUBLISHES

SUBSCRIBES

DEPENDS_ON

IMPLEMENTS

EXTENDS

EXPOSES

RETURNS

ACCEPTS

OWNS

CONFIGURES

DOCUMENTS
```

---

# 13. Symbol Resolution

Every parser MUST resolve symbols where possible.

Example

```
login()

↓

Function

↓

Fully Qualified Identifier
```

Unresolved symbols must be marked explicitly.

Never silently discard unresolved references.

---

# 14. Canonical Identifiers

Every entity receives a globally unique identifier.

Examples

```
rig://repo/demo

rig://module/auth

rig://function/login

rig://service/payment
```

Identifiers must remain stable across rescans unless the underlying entity changes.

---

# 15. Validation Rules

A valid IR must satisfy

- Unique entity IDs
- Unique relationship IDs
- Valid references
- No dangling entities
- Valid kinds
- Valid relationship types
- Metadata schema compliance

---

# 16. Serialization

Supported formats

```
JSON

Binary

MessagePack

Protocol Buffers (Future)
```

Serialization must preserve

- ordering
- identifiers
- metadata
- source locations

---

# 17. Incremental Updates

The IR supports partial regeneration.

When only one file changes

```
Repository

↓

Changed File

↓

Parser

↓

IR Update

↓

Graph Update
```

The entire repository should not require reparsing.

---

# 18. Parser Contract

Every parser must implement

```
Scan()

↓

Parse()

↓

Semantic Analysis()

↓

Generate IR()

↓

Validate()

↓

Return
```

Parsers never generate graph nodes directly.

---

# 19. Graph Generator Contract

Graph generation begins only after IR validation.

Responsibilities

- Convert entities into graph nodes
- Convert relationships into graph edges
- Merge duplicate entities
- Preserve metadata
- Generate indexes

---

# 20. Error Model

Parsing errors

↓

Parser

Semantic errors

↓

IR Validator

Graph errors

↓

Graph Generator

Errors are categorized as

```
Fatal

Recoverable

Warning
```

Recoverable errors should preserve as much IR as possible.

---

# 21. Compatibility

The IR follows Semantic Versioning.

```
MAJOR

MINOR

PATCH
```

Breaking field changes require a major version.

New optional fields require a minor version.

---

# 22. Extension Model

Plugins may extend

- Entity kinds
- Relationship kinds
- Metadata
- Validation rules

Plugins MUST NOT modify existing core semantics.

---

# 23. Example IR

```json
{
  "entities": [
    {
      "id": "function.login",
      "kind": "Function",
      "name": "login"
    },
    {
      "id": "function.verify",
      "kind": "Function",
      "name": "verify"
    }
  ],
  "relationships": [
    {
      "type": "CALLS",
      "source": "function.login",
      "target": "function.verify"
    }
  ]
}
```

---

# 24. Relationship to Other Specifications

The IR is consumed by

- GRAPH_SCHEMA.md
- QUERY_SPEC.md

The IR is produced by

- Language Parsers
- Plugins

The IR is transformed into the Repository Graph by the Graph Generation Engine.

---

# 25. Future Directions

Future IR enhancements may include

- Runtime entities
- AI-generated symbols
- Architecture annotations
- Review knowledge
- Decision metadata
- Telemetry integration
- Multi-repository references
- Cross-language symbol resolution

These additions must remain backward compatible.

---

# 26. Conclusion

The Intermediate Representation is the semantic backbone of RIG.

By providing a stable, language-independent contract between parsing and graph generation, the IR enables new language frontends, analysis modules, and plugins to integrate without changing downstream systems.

Every parser speaks IR.

Every graph builder understands IR.

This separation ensures that RIG remains modular, extensible, and capable of supporting future languages, frameworks, and engineering intelligence capabilities.
