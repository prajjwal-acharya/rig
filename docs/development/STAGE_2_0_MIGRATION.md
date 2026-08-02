# Stage 2.0 Migration Report — Restore Architectural Boundaries

> Status: Completed
> Scope: Internal architectural refactor. No feature, algorithm, CLI, or
> public-schema change.
> Companion: [ARCHITECTURE_AUDIT.md](../ARCHITECTURE_AUDIT.md) (Stage 1), which
> identified the violation this stage removes (finding **F1**).

---

## 1. Objective

Restore RIG's intended compiler layering so that **Tree-sitter is an
implementation detail of parsing**, and the **Intermediate Representation is
the canonical semantic boundary**. Before this change, three components in the
semantic and analysis layers bypassed the IR and read Go syntax trees directly:

- Reference resolution (`references`)
- Type-relationship analysis (`analysis`)
- Dependency analysis (`analysis`)

After this change, no semantic, analysis, graph, or CLI package depends on
Tree-sitter. Each consumes language-neutral IR facts instead.

Target layering (now enforced by tests):

```
parsers  ─┐
          ▼
        frontends (Go)          ← the only non-parser code allowed to see Tree-sitter
          ▼
         IR                     ← canonical semantic boundary (neutral)
          ▼
       symbols
          ▼
      references
          ▼
       analysis
          ▼
        graph
          ▼
         cli
```

---

## 2. Required audit — every `rig.parsers.treesitter` / `tree_sitter` import outside the parser layer

Snapshot taken before the refactor, with the reason each import existed and how
it was resolved.

| # | Location | Why it existed | Resolution |
|---|----------|----------------|------------|
| 1 | `rig/ir/builders/go.py` | The Go IR builder turns a Tree-sitter tree into structural IR. It lived *inside* the neutral `ir/` package. | **Moved** to `rig/frontends/go/ir_builder.py`. The neutral `ir/` package no longer contains any language implementation. |
| 2 | `rig/references/resolver.py` | `GoReferenceResolver` re-walked function bodies / type / var specs to find identifier references, because the IR did not carry them. | **Removed.** The tree walk moved into the Go frontend, which now emits neutral `ReferenceUse` facts into the IR. The resolver (`IRReferenceResolver`) binds those facts to symbols with no syntax access. |
| 3 | `rig/analysis/typerelationships.py` | Walked struct fields, aliases, and method signatures for type→type relationships, because the IR did not carry them. | **Removed.** Extraction moved into the Go frontend (`DeclaredTypeUses` / `MethodTypeUses`); the analysis resolves those facts via the Type Index. |
| 4 | `rig/analysis/dependency.py` | Walked qualified type/call references (`pkg.Type`, `pkg.Func()`) for package dependencies, because the IR did not carry them. | **Removed.** Extraction moved into the Go frontend (`QualifiedUse` / `UnsupportedDependencyUse`); the analysis resolves qualifiers to packages via the IR's imports. |
| 5 | `rig/cli/pipeline.py` | Imported `rig.parsers.treesitter.factory.build_default_registry` to build the parser registry. | **Rerouted.** A neutral entry point `rig.parsers.factory.build_default_parser_registry()` now hides backend selection; the CLI imports `rig.parsers`, never `rig.parsers.treesitter`. |

**Result:** every Tree-sitter import now lives in `rig/parsers/**` (the backend)
or `rig/frontends/**` (language frontends). This is asserted by
`tests/architecture/test_layering.py`.

---

## 3. What changed

### 3.1 New: neutral IR semantic-fact carriers (`rig/ir/model.py`)

The IR previously modeled only structural declarations (a "table of contents").
It now also carries the syntax-extracted, **pre-resolution** facts the semantic
layers need — expressed in language-neutral terms, populated per language by a
frontend:

- `ReferenceUse` — an identifier used (not declared) in source, with a
  kind hint and whether it resolves at file or repository scope.
- `DeclaredTypeUses` / `StructFieldUse` / `TypeUse` — a declared type's outgoing
  named-type references (struct fields, alias target).
- `MethodTypeUses` — a method's receiver / parameter / return named-type
  references.
- `QualifiedUse` — a module-qualified reference (`pkg.Type` / `pkg.Func()`).
- `UnsupportedDependencyUse` — a frontend-detected construct the dependency
  analysis cannot treat as a source (generic exported type; unrecognized call
  shape), carried so the analysis can report it without re-parsing.

These are attached to `File` with empty-tuple defaults, so the addition is
backward compatible: a `File` constructed without them is still valid.

> **Design note.** These carriers deliberately relocate *existing* extracted
> information to the IR; no new language concept was invented and no new
> semantic capability was added. They are pre-resolution *facts* — resolution
> (name → symbol / type / package) still happens in the semantic and analysis
> layers, which is where it belongs.

### 3.2 New: Go frontend (`rig/frontends/go/`)

- `ir_builder.py` — `GoIRBuilder` (moved from `rig/ir/builders/go.py`), now the
  single non-parser home for Tree-sitter. It produces the structural IR **and**
  all the semantic-fact carriers above, in one place.
- `predeclared.py` — Go's predeclared identifiers and builtin type names, moved
  out of the semantic/analysis layers. The frontend filters these while
  extracting, so downstream layers need no Go-specific lists.

### 3.3 Neutralized consumers

- `rig/references/resolver.py` — `IRReferenceResolver` (language-neutral) reads
  `File.reference_uses`. `GoReferenceResolver` is retained as a backwards-
  compatible alias.
- `rig/analysis/typerelationships.py` — `TypeRelationshipAnalysis` reads
  `File.declared_type_uses` / `File.method_type_uses`.
- `rig/analysis/dependency.py` — `DependencyAnalysis` reads `File.qualified_uses`
  / `File.unsupported_dependency_uses` and the IR's imports.

The three consumers' constructors no longer take `parsed_files`; they consume
the IR from the `AnalysisContext` / `RepositoryIR`.

### 3.4 Neutral parser entry point

`rig/parsers/factory.py::build_default_parser_registry()` — lets callers ask
`rig.parsers` for a ready registry without naming a backend (the Tree-sitter
import is lazy, inside the function).

### 3.5 Tests

- `tests/architecture/test_layering.py` (**new**) — parses the import graph and
  enforces: no neutral/semantic/analysis/CLI module imports Tree-sitter; every
  Tree-sitter import is confined to `parsers`/`frontends`; `rig/ir/builders/`
  does not exist; analysis and references never import the parser layer.
- Existing tests updated only where they constructed a moved/changed class
  (`from rig.frontends.go import GoIRBuilder`; resolver/analysis constructors
  without `parsed_files`). `tests/ir/builders/test_go.py` moved to
  `tests/frontends/go/test_ir_builder.py`.

---

## 4. What did **not** change (preserved contracts)

Verified by a byte-for-byte golden comparison of a multi-package Go fixture
(structs, interfaces, aliases, embedding, methods, generics, cross-package
imports/types/calls, duplicate names, blank imports, predeclared identifiers)
across every CLI command (`detect`, `parse`, `ir`, `symbols`, `references`,
`types`, `graph`, `analyze`, `stats`, incl. `--verbose`) **and** the full
serialized knowledge graph JSON:

- CLI commands, arguments, and output — identical.
- Diagnostics (messages, severities, counts) surfaced by the CLI — identical.
- IR / Symbol Table / Reference Index / Type Index / Analysis public APIs —
  unchanged.
- Graph model and JSON serialization (nodes, edges, metadata, statistics) —
  identical (deterministic ids and ordering preserved; all fact-derived ids are
  content-based, so relocating extraction cannot change them).
- Determinism — identifiers, ordering, statistics all preserved.

Quality gates, all green after the change:

- `pytest`: **777 passed** (772 pre-existing + 5 new architecture tests).
- `ruff check` / `ruff format --check`: clean.
- `mypy`: no issues in 109 source files.

---

## 5. Architectural violations removed

1. **Layer-skipping (F1).** `references`, `analysis/typerelationships`, and
   `analysis/dependency` no longer reach past the IR into the parser's syntax
   tree. Syntax now stays in the parser/frontend layer; semantics are consumed
   from the IR.
2. **Language implementation inside the neutral IR.** `rig/ir/builders/go.py`
   removed; the neutral `ir/` package now contains only models, identifiers,
   interfaces, registry, diagnostics, and visitor.
3. **Go knowledge leaking into semantic/analysis layers.** Predeclared
   identifiers and builtin type names moved from `references`/`analysis` into the
   Go frontend.
4. **CLI naming the parser backend.** The CLI now composes `rig.parsers`, not
   `rig.parsers.treesitter`.

A future regression of any of these fails `tests/architecture/test_layering.py`.

---

## 6. Remaining intentional dependencies (documented, not hidden)

These do **not** violate the Stage 2.0 goal ("no semantic package depends on
Tree-sitter"); they are downward dependencies on neutral modules, called out for
transparency:

1. **`rig/ir/repository.py` imports `rig.parsers.pipeline.ParsedFile`.**
   `build_repository_ir(...)` is neutral orchestration that dispatches parse
   results to a registered `IRBuilder` by language. `rig.parsers.pipeline` is a
   Tree-sitter-free module (a `ParsedFile` is a neutral dataclass whose
   `syntax_tree` field is typed `Any`). This import was **kept** rather than
   moved, to preserve the widely-used `rig.ir.build_repository_ir` public API;
   it introduces no Tree-sitter dependency and no import cycle. Relocating this
   orchestration out of `ir/` is a candidate for a later, purely cosmetic stage.

2. **`GoReferenceResolver` name retained** as an alias of the now-neutral
   `IRReferenceResolver`, for API stability. The class is language-neutral; the
   Go-flavored name is vestigial and slated for a later rename.

3. **Test scaffolding in `tests/analysis/test_dependency.py` and
   `test_typerelationships.py`** still constructs `parsed_files` in helpers even
   though the analyses no longer require it. This is harmless (mypy/ruff clean)
   and left untouched to keep the refactor's test diff minimal.

No component still requires Tree-sitter that is not a parser or a language
frontend. There is no hidden architectural debt beyond the three cosmetic items
above.

---

## 7. Follow-on stages (unchanged from the Stage 1 roadmap)

This stage restored the boundary; it did **not** attempt the deeper items the
audit flagged, which remain future work:

- Stage 2.1 — IR normalization: neutral visibility and module/grouping models
  (the IR is now the boundary, but still carries some Go-shaped assumptions such
  as `is_exported` and `package`).
- Stage 2.3 — analysis language-neutrality / dispatch (honor
  `supported_languages`); build the type index once.
- Stage 2.5 — graph enrichment performance (single materialization; O(1)
  `Properties`).

The boundary this stage restored is the prerequisite that makes those safe.
