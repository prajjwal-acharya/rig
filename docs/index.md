# Repository Intelligence Graph (RIG)

Welcome to the official documentation for **Repository Intelligence Graph (RIG)**.

This documentation serves as the engineering reference for the project. It contains the architectural specifications, design decisions, implementation guidelines, and contributor resources that define how RIG is built and how it evolves.

Whether you're exploring the project, contributing a new parser, or implementing a core subsystem, these documents are the authoritative source of truth.

---

## Documentation Structure

The documentation is organized into two primary sections.

### Architecture Specifications

The specification documents define the technical blueprint of RIG. These documents describe the intended system design, interfaces, contracts, and constraints before implementation.

They are the primary reference for anyone contributing to the project.

The current specifications include:

- **System Architecture** — Overall system design, component responsibilities, and development roadmap.
- **Graph Schema** — Definition of the engineering graph, including nodes, edges, metadata, and graph invariants.
- **Intermediate Representation (IR)** — Canonical representation produced by every parser before graph construction.
- **Plugin Specification** — Contracts for parser plugins, lifecycle, registration, and extensibility.
- **Query Specification** — Public query interface used by the CLI, SDK, REST API, visualization layer, and future AI systems.

---

### Architecture Decision Records (ADRs)

Architecture Decision Records document important technical decisions made during the development of RIG.

Each ADR captures:

- The problem being solved
- The context surrounding the decision
- The chosen solution
- Alternatives that were considered
- Long-term consequences

Unlike the specification documents, ADRs explain **why** the system was designed a particular way.

---

## Documentation Philosophy

RIG follows a **Specification-Driven Development** approach.

Every major subsystem is designed and documented before implementation begins. Specifications define the intended behavior, while implementations are expected to conform to those specifications.

This approach provides several benefits:

- Clear architectural direction
- Stable interfaces between components
- Easier collaboration and code reviews
- Better long-term maintainability
- Reduced architectural drift as the project evolves

---

## Recommended Reading Order

If you're new to the project, the following reading order is recommended:

1. System Architecture
2. Graph Schema
3. Intermediate Representation (IR)
4. Plugin Specification
5. Query Specification
6. Architecture Decision Records

This sequence provides a complete understanding of the platform before diving into implementation.

---

## Current Status

RIG is currently in the **Architecture & Foundation** phase.

The core specifications are being finalized before implementation begins. Once these specifications are complete, development will proceed in incremental stages, beginning with repository understanding and graph generation.

---

## Guiding Principles

The project is built around a small set of core principles:

- **Local-First** — Core functionality should work without cloud services.
- **Graph-First** — The engineering graph is the primary source of truth.
- **Plugin-First** — Language and infrastructure support are implemented as extensible plugins.
- **Specification-Driven** — Architecture and interfaces are defined before implementation.
- **Incremental by Design** — Changes should update only affected portions of the graph rather than requiring full reconstruction.

---

## Contributing

Before contributing to RIG, contributors are encouraged to read the architecture specifications and relevant ADRs. These documents establish the design contracts that guide implementation and help maintain consistency across the project.

Welcome to the RIG project.
