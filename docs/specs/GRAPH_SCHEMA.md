# GRAPH_SCHEMA.md

> **Repository Intelligence Graph (RIG)**
>
> Version: 0.1.0
> Status: Draft
> Authors: RIG Contributors

---

# 1. Purpose

The Graph Schema defines the canonical representation of software systems within RIG.

Every repository analyzed by RIG is transformed into a directed property graph.

The schema specifies:

- Node types
- Edge types
- Metadata
- Constraints
- Identifiers
- Relationships
- Versioning
- Serialization

All parsers, plugins, query engines, APIs, and visualizations MUST conform to this specification.

---

# 2. Design Philosophy

The graph represents **engineering knowledge**, not merely source code.

Every meaningful engineering artifact becomes a node.

Relationships become explicit graph edges.

The schema is:

- Language independent
- Framework independent
- Storage independent
- Extensible
- Backward compatible

---

# 3. Graph Model

RIG uses a **Directed Property Graph**.

A graph consists of:

```
Graph

├── Nodes
├── Edges
└── Metadata
```

Every node owns properties.

Every edge owns properties.

Both are uniquely identifiable.

---

# 4. Core Concepts

## Node

Represents an engineering entity.

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
- Deployment

---

## Edge

Represents a relationship.

Examples

```
CALLS

IMPORTS

OWNS

DEPENDS_ON

IMPLEMENTS

EXPOSES

CONTAINS

USES
```

---

## Property

Metadata attached to nodes or edges.

Examples

```
language

visibility

owner

version

path

framework
```

---

# 5. Graph Hierarchy

```
Repository

│

├── Packages

│

├── Modules

│

├── Files

│

├── Classes

│

├── Functions

│

├── APIs

│

├── Services

│

├── Databases

│

├── Infrastructure

│

└── Configuration
```

---

# 6. Node Types

## Repository

Represents the entire project.

Properties

```
id

name

root

branch

commit

created_at

updated_at
```

---

## Package

Represents a language package.

Examples

```
Python package

Java package

Go package

Rust crate
```

---

## Module

Logical grouping of source files.

---

## File

Represents a physical source file.

Properties

```
path

language

checksum

size
```

---

## Namespace

Programming namespace.

---

## Class

Represents object-oriented classes.

---

## Interface

Language interface.

---

## Struct

Native data structure.

---

## Enum

Language enumeration.

---

## Function

Callable unit.

Properties

```
signature

visibility

async

generic

return_type
```

---

## Variable

Global variables.

---

## Constant

Immutable values.

---

## API

REST

GraphQL

gRPC

RPC

WebSocket

---

## Endpoint

Single callable endpoint.

---

## Service

Microservice or application.

---

## Database

Database instance.

Examples

```
Postgres

MongoDB

Redis

MySQL
```

---

## Table

Database table.

---

## Queue

Kafka

RabbitMQ

SQS

NATS

---

## Topic

Messaging topic.

---

## Deployment

Runtime deployment.

---

## Container

Docker container.

---

## Cluster

Kubernetes cluster.

---

## Secret

Logical secret.

Never stores secret values.

---

## Environment Variable

Configuration variable.

---

## Pipeline

CI/CD pipeline.

---

## Workflow

Automation workflow.

---

## Documentation

README

Architecture

ADR

RFC

---

## Test

Test suite.

---

## Dependency

External package.

---

# 7. Edge Types

---

## CONTAINS

Hierarchy.

```
Repository

↓

Package

↓

Module

↓

File
```

---

## IMPORTS

Module imports another module.

---

## CALLS

Function calls function.

---

## DEPENDS_ON

General dependency.

---

## IMPLEMENTS

Class implements interface.

---

## EXTENDS

Inheritance.

---

## EXPOSES

Service exposes endpoint.

---

## RETURNS

Function returns type.

---

## ACCEPTS

Function accepts parameter.

---

## REFERENCES

Documentation reference.

---

## READS

Consumes resource.

---

## WRITES

Produces resource.

---

## PUBLISHES

Publishes event.

---

## SUBSCRIBES

Consumes event.

---

## CONNECTS_TO

Infrastructure connection.

---

## DEPLOYS_TO

Deployment mapping.

---

## OWNS

Ownership.

---

## CONFIGURES

Configuration relationship.

---

## TESTS

Test coverage.

---

## DOCUMENTS

Documentation relationship.

---

# 8. Common Node Properties

Every node contains

```
id

type

name

display_name

version

created_at

updated_at

metadata
```

---

# 9. Common Edge Properties

Every edge contains

```
id

type

source

target

created_at

metadata
```

---

# 10. Metadata Model

Metadata is extensible.

Example

```json
{
  "language": "Python",
  "framework": "FastAPI",
  "owner": "Backend Team",
  "stability": "stable"
}
```

Plugins may extend metadata.

Core metadata MUST remain immutable.

---

# 11. Identifiers

Every node has a globally unique identifier.

```
rig://repository/auth

rig://service/payment

rig://api/user/login

rig://function/auth/login
```

Identifiers MUST remain stable across rescans.

---

# 12. Constraints

The graph must satisfy:

- No duplicate identifiers
- Directed edges only
- No orphan nodes
- Edge endpoints must exist
- Type-safe relationships
- Schema validation required

---

# 13. Versioning

Schema follows Semantic Versioning.

```
MAJOR

MINOR

PATCH
```

Breaking graph changes require MAJOR updates.

---

# 14. Serialization

Supported formats

```
JSON

JSON-LD

GraphML

GEXF

Neo4j Export

CSV
```

Future

```
Apache Arrow

Parquet
```

---

# 15. Extension Model

Plugins may introduce

- New node types
- New edge types
- New metadata
- New validators

Plugins MUST NOT modify existing core semantics.

---

# 16. Example Graph

```
Repository

│

├── Service(Auth)

│      │

│      ├── API(Login)

│      │

│      ├── Database(Postgres)

│      │

│      └── Queue(Kafka)
```

Relationships

```
Repository

↓

CONTAINS

↓

Service

↓

EXPOSES

↓

API

↓

READS

↓

Database

↓

PUBLISHES

↓

Queue
```

---

# 17. Validation Rules

Every graph MUST pass:

- Schema validation
- Node validation
- Edge validation
- Metadata validation
- Identifier validation
- Relationship validation

Graphs failing validation are rejected.

---

# 18. Future Compatibility

Future schema additions include

- AI agents
- LLM memory
- Architecture rules
- Engineering decisions
- Review knowledge
- Organizational ownership
- Runtime telemetry

Backward compatibility remains mandatory.

---

# 19. Related Specifications

This specification is consumed by

- IR_SPEC.md
- PLUGIN_SPEC.md
- QUERY_SPEC.md

The graph schema serves as the canonical data model for all future RIG components.

---

# 20. Conclusion

The Graph Schema defines the shared language through which every RIG component communicates.

By representing software systems as directed property graphs with stable semantics, RIG enables consistent repository analysis, extensibility, interoperability, and long-term compatibility across languages, frameworks, and tooling ecosystems.
