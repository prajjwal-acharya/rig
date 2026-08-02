# Language-Neutrality Requirements

> Status: Draft — planning input, not yet scheduled.
> Scope: What must be implemented so RIG stops being a Go analyzer with a
> language-neutral facade, and becomes an architecture that actually adds
> languages by extension rather than by editing the core.
> Inputs: [ARCHITECTURE_AUDIT.md](../ARCHITECTURE_AUDIT.md) (Stage 1 findings
> F1–F5, recommendations C1–C5/M1–M9/L1–L7) and
> [STAGE_2_0_MIGRATION.md](STAGE_2_0_MIGRATION.md) (what has already shipped).
> This document does not re-argue the audit; it re-derives a single ordered
> checklist from it, marks what's done, and states the acceptance test for
> each remaining item against the code as it exists today.

---

## 1. How to read this

Each item below is a **requirement**, not a suggestion: a concrete condition
that must hold in the codebase. Every item has:

- **Why it's biased today** — the specific Go leak, quoted against current
  file/line reality (verified against the working tree, not just the audit).
- **Requirement** — what must be true when it's done.
- **Acceptance test** — a check (often literally `grep -rl`) that proves it.

Items are grouped into three tiers, matching the audit's severity, and
ordered so each tier is safe to build once the previous one is done. **Do not
start the second language (Python) until Tier 1 is complete** — every item in
Tier 1 gets more expensive to retrofit the more Go-specific code sits on top
of it.

---

## 2. Already done (Stage 2.0, on `chore/update-pyproject-uvlock`)

Recorded here so the checklist below doesn't re-list it. See
[STAGE_2_0_MIGRATION.md](STAGE_2_0_MIGRATION.md) for full detail.

- ✅ No semantic/analysis/graph/CLI package imports Tree-sitter. All
  Tree-sitter usage is confined to `rig/parsers/**` and `rig/frontends/**`.
- ✅ `rig/frontends/go/` exists as the single non-parser home for Go syntax
  handling (`ir_builder.py`, `predeclared.py`).
- ✅ The IR gained neutral **fact carriers** — `ReferenceUse`,
  `DeclaredTypeUses`/`StructFieldUse`/`TypeUse`, `MethodTypeUses`,
  `QualifiedUse`, `UnsupportedDependencyUse` — so `references`,
  `analysis.typerelationships`, and `analysis.dependency` consume IR facts
  instead of re-walking syntax.
- ✅ `rig/parsers/factory.py::build_default_parser_registry()` gives the CLI a
  backend-neutral entry point.
- ✅ `tests/architecture/test_layering.py` enforces the above and fails CI on
  regression.

This closes the *layer-skipping* half of **F1** (syntax reaching past the
IR). It does **not** close F1's other half (the IR is still thin), nor does
it touch F2, F3, F4, or F5. Those are what remain.

---

## 3. Tier 1 — Blocking (must land before a second language is added)

### 3.1 Complete the IR so it carries semantics, not just a table of contents

**Why it's biased today.** `rig/ir/model.py` still models only
`FunctionDeclaration` (name, param count, exported),
`TypeDeclaration` (name, `underlying_kind: str`, exported),
`VariableDeclaration` (name, const, exported), `ImportDeclaration`. There are
no method declarations, no class/struct member types beyond the
already-added fact carriers, no expression-level detail. The Stage 2.0 fact
carriers (`DeclaredTypeUses`, `MethodTypeUses`, `QualifiedUse`, …) are a real
improvement but are still Go-shaped extraction results, not a general
"declaration carries its full signature" model — e.g. there is still no
`MethodDeclaration` kind at all; methods are dropped by the Go builder.

**Requirement.** `DeclarationKind` and the `Declaration` hierarchy grow to
represent the constructs every target language needs a home for at minimum:
methods (as distinct from free functions), classes/records, enums, fields
with types, parameters with types, return types, and a generic "type
reference" that downstream layers can resolve without re-reading syntax.

**Acceptance test.** A new language frontend can populate 100% of what its
semantic layer needs by constructing `Declaration` subclasses — it never
needs `references`, `types`, or `analysis` to special-case it.

### 3.2 Introduce a neutral `Visibility` model (replace `is_exported: bool`)

**Why it's biased today.** `is_exported: bool` is still present three times
in `rig/ir/model.py` (`FunctionDeclaration`, `TypeDeclaration`,
`VariableDeclaration`), and it encodes exactly one rule: Go's
"capitalized ⇒ exported." It propagates into `symbols/builder.py` and is
re-derived again independently in `analysis/dependency.py`. Python has no
export keyword (only the `_prefix` convention), C uses `static`/linkage,
C++ adds access specifiers + namespaces, Java has four visibility levels,
Rust has `pub`/`pub(crate)`/`pub(super)`. None of these are a bool.

**Requirement.** Replace `is_exported: bool` with a `Visibility` value
(`PUBLIC | PRIVATE | PROTECTED | PACKAGE | CRATE | MODULE | INTERNAL |
UNKNOWN`, or an equivalent small value object) owned by `rig/ir/model.py`
and populated per-frontend. Go's frontend maps capitalized → `PUBLIC`,
lowercase → `INTERNAL`/`MODULE` (whichever the model calls package-private),
trivially. Every other consumer of `is_exported` is updated to read
`Visibility` instead — `symbols/builder.py`, `analysis/dependency.py`.

**Acceptance test.** `grep -rn "is_exported" rig/` returns nothing outside
the Go frontend's construction of `Visibility` values (i.e. the boolean
itself no longer exists as a cross-language contract).

### 3.3 Generalize `Package` into a language-neutral grouping abstraction

**Why it's biased today.** `File.package_name: str | None` plus
"group repository by package name" (`RepositoryIRBuilder._build_packages`)
assumes Go/Java's flat-package model. C++ has namespaces *and* translation
units *and* headers; C has translation units + linkage; Python has
modules/packages; Rust has modules + crates — none map 1:1 onto "package."
The audit also flags (`ARCHITECTURE_AUDIT.md` §4.4) that "last import-path
segment = package name" is a Go convention independently re-encoded in both
the IR builder and `analysis/dependency.py`.

**Requirement.** Introduce a grouping abstraction general enough for
module/namespace/compilation-unit/crate (naming TBD — e.g. `Module` or
`CompilationUnit`), owned by the neutral IR, with `Package` as Go's
particular instance of it. The import-path→package-name convention moves
into the Go frontend as the *only* place that encodes it.

**Acceptance test.** `grep -rn "package_name\|last.*segment" rig/analysis/
rig/ir/repository.py` shows no Go-specific path convention outside
`rig/frontends/go/`.

### 3.4 Make analyses honest about language support (resolve F2)

**Why it's biased today.** Verified against current code:
`rig/analysis/interface.py` defines `supported_languages` on the `Analysis`
contract, but `grep -n "supported_languages" rig/analysis/*.py` shows it is
declared and never consulted anywhere in `manager.py`. `TypeRelationshipAnalysis`
and `DependencyAnalysis` have language-neutral ids
(`"type-relationships"`, `"dependency-analysis"`) and neutral class names,
but internally they are 100% Go-shaped (they read the Go-populated fact
carriers). Point RIG at a Python-only repo today and these two analyses
return a **green, empty result** — no error, no "unsupported language"
diagnostic. That is a silent-failure trap, and it's still live.

**Requirement.** Pick one of:
  - **(a)** Rename to `GoTypeRelationshipAnalysis` /
    `GoDependencyAnalysis`, and have `AnalysisManager` filter dispatch by
    `supported_languages`, emitting an explicit "unsupported language"
    diagnostic (not silence) for files it skips; or
  - **(b) — preferred, and the direction 3.1 sets up** — rewrite them to
    consume the now-complete neutral IR (3.1) so one implementation serves
    every language whose frontend populates the fact carriers correctly.

Either way: **a repository containing an unsupported language must never
produce a silent, green, empty analysis result.**

**Acceptance test.** Run each analysis against a fixture repo containing only
an unsupported language. Either the analysis is skipped with a visible
diagnostic, or it runs and produces a correct (possibly empty, but
*intentionally* empty) result — never a silent green pass presented as if it
had analyzed the code.

### 3.5 Replace hardcoded Go composition with a language-binding registry

**Why it's biased today.** `rig/cli/pipeline.py` still directly constructs
`GoIRBuilder()`, `GoSymbolTableBuilder()`, `GoReferenceResolver(...)`
(alias), `GoTypeBuilder()`, and the three analyses. `build_repository` wraps
a single `GoIRBuilder` in an `IRBuilderRegistry`, using the registry as a
one-entry container rather than resolving by detected language. Adding
Python today means editing `pipeline.py`, not registering a new binding.

**Requirement.** `cli/pipeline.py` resolves, per language detected in the
repository, the tuple `(parser, ir_builder, reference_resolver, type_builder,
analyses)` from a registry keyed by language — never by constructing a
language-named class directly in the composition root.

**Acceptance test.** Adding a language end-to-end touches zero lines in
`rig/cli/pipeline.py` (or whatever the composition root becomes) — only new
frontend code plus one registration call.

---

## 4. Tier 2 — Should land before a second language's quality is trusted

### 4.1 Centralize per-language knowledge (currently scattered 3+ places)

**Why it's biased today.** Go-specific knowledge is independently duplicated:
`_is_exported`-equivalent logic; Go predeclared identifiers
(`rig/frontends/go/predeclared.py` — already centralized, good); but builtin
*type* names and the package-name-from-import-path convention are still
implicitly encoded wherever `analysis/dependency.py` and
`ir/repository.py`/frontend construct them. Verify per-item before closing.

**Requirement.** One Go-language module (already started by
`rig/frontends/go/predeclared.py`) owns *all* Go-specific constants and
rules — predeclared identifiers, builtin types, export-rule mapping,
import-path convention. Every other package imports from it; none
re-declares it.

**Acceptance test.** No `_GO_*`-style constant or Go-specific string literal
(`"struct"`, node-type names, capitalization checks) exists outside
`rig/frontends/go/` and `rig/parsers/treesitter/**`.

### 4.2 Generalize the symbol-scope model beyond Go/Java

**Why it's biased today.** `rig/symbols/scope.py::ScopeKind` is still exactly
`REPOSITORY | PACKAGE | FILE` (verified). `SymbolResolver` walks a strictly
vertical file→package→repository chain and cannot do cross-package or
import-bound resolution. Python needs module+class+function scope; C++ needs
namespace+class+block; Rust needs module+block. None of these are
representable today.

**Requirement.** Add block/class/namespace/module `ScopeKind` members and
support non-vertical, import-bound resolution (a name resolves via an
explicit import binding, not just lexical nesting).

**Acceptance test.** A Python fixture with `from pkg.mod import name` and a
nested `class`/`def` resolves `name` and a class-body reference correctly
through the resolver, without special-casing in `analysis/`.

### 4.3 Generalize the type taxonomy beyond Go's

**Why it's biased today.** `rig/types/model.py::TypeKind` is still exactly
`STRUCT | INTERFACE | ALIAS | NAMED` (verified). Classes, enums, unions,
traits, records, generics/templates have no representation.
`GoTypeBuilder`/`GoSymbolTableBuilder` are still named `Go*` while their own
docstrings claim language neutrality — true today only because the IR is
thin (audit L1); once other languages arrive, that tension resolves one way
or the other and the current naming is misleading either way.

**Requirement.** Extend `TypeKind` (or make it open, mirroring `Node.type`'s
already-open-string design in `graph/model.py`) to cover class/enum/
union/trait/record at minimum. Resolve the `Go*` builder naming — either
rename to neutral names once genuinely neutral, or accept per-language
builders and name them consistently (`GoTypeBuilder`, `PythonTypeBuilder`,
…).

**Acceptance test.** A struct-only language (Go) and a class-based language
(Python/Java) both produce a correctly-kinded `TypeIndex` without either
`TypeKind` growing Go-only or class-only members that the other ignores.

### 4.4 Decide the extension mechanism — one, not two

**Why it's biased today.** `rig/plugins/` is a complete, well-tested
manifest/discovery/lifecycle/registry framework. Verified: its only caller
is `rig/cli/commands.py:140`, `plugin_manager.load_all([], plugin_context)`
— an empty list, always. Nothing registers a parser, grammar, IR builder, or
analysis through it. Meanwhile there are **two unrelated `Capability`
types** with the same name: `rig.plugins.capability.Capability` (a
provides/consumes/produces dataclass) and `rig.analysis.capability.Capability`
(an ir/symbol_table/… enum) — confirmed still both present.

**Requirement.** Either (a) wire `plugins/` into real registration — a
language plugin contributes its grammar + IR builder + resolver + analyses
through the plugin manager into the per-subsystem registries — and that
becomes the mechanism 3.5's language-binding registry is built from; or (b)
park/remove `plugins/` and formalize the lightweight registry from 3.5 as
the one mechanism. Either way, rename one `Capability` type to end the
collision.

**Acceptance test.** `grep -rn "class Capability" rig/` returns exactly one
class, or two classes with unambiguous, non-colliding names. Language
registration happens through exactly one mechanism, documented as such.

### 4.5 Build the type index once, not per-analysis

**Why it's biased today.** Verified: `rig/cli/pipeline.py:110` calls
`GoTypeBuilder().build(repository, symbols)`, and
`rig/analysis/typerelationships.py:325` calls
`GoTypeBuilder().build(repository, symbols)` again, independently, inside
`execute()`. Every added language multiplies this redundant build.

**Requirement.** `AnalysisContext` carries `TypeIndex` as an optional
capability (like symbols/references/graph already are), built once in the
pipeline and passed in; no analysis rebuilds it.

**Acceptance test.** `grep -rn "TypeBuilder()" rig/` shows exactly one build
call per pipeline run (verifiable via a call-count test/log, not just source
grep, since the source-level fix could still be called twice at runtime).

### 4.6 Fix graph-enrichment full-rebuild cost

**Why it's biased today.** Not language-bias per se, but it's the item the
audit flags as scaling from Medium to Critical as more languages (=more
enrichers = more full graph copies) are added. `ImportGraphBuilder`,
`ReferenceGraphBuilder`, and each analysis each construct a fresh
`GraphAccumulator`, copy every existing node/edge, add their own, and
re-sort — O(N·k) copying + k full sorts for k enrichers in sequence.
`Properties.get`/`__getitem__`/`__contains__` are still O(n) linear scans
over a sorted tuple (verified: `rig/graph/properties.py` is tuple-backed,
`_items: tuple[tuple[str, PropertyValue], ...]`).

**Requirement.** A single accumulator threaded through all enrichers
(materialize/sort once, not once per enricher). `Properties` backed by a
frozen mapping for O(1) access while staying hashable.

**Acceptance test.** A large-repo enrichment benchmark shows enrichment cost
scaling with graph size once, not with (graph size × enricher count).

### 4.7 Open (or registry-own) `RelationshipType`

**Why it's biased today.** Verified: `rig/graph/model.py::RelationshipType`
is still a closed enum with Go-shaped members (`EMBEDS`,
`DECLARES_METHOD_PARAMETER`, `DECLARES_METHOD_RETURNING`) alongside reserved
but unused ones (`EXTENDS`, `IMPLEMENTS`, `OWNS`). New relationship kinds
(Rust `IMPLEMENTS_TRAIT`, C++ `INHERITS`) require a core-model edit per
language, unlike `Node.type` which is already deliberately open.

**Requirement.** Either open `RelationshipType` to a registry-owned string
set (mirroring `Node.type`) or explicitly document it as the one closed
vocabulary every language frontend must map onto, and enumerate the mapping
up front for all six target languages so gaps are caught before they're
needed.

**Acceptance test.** Adding a language-specific relationship (e.g. Rust
trait implementation) requires no edit to `rig/graph/model.py`, only a
registration.

### 4.8 Consolidate graph-enricher placement

**Why it's biased today.** "Project X into graph edges" logic is split
across `graph/builders/{structural,imports}.py` and
`references/builder.py::ReferenceGraphBuilder`, plus enrichment embedded
inside the three analyses. Same *kind* of responsibility, three locations.

**Requirement.** One consistent home (e.g. `graph/builders/` or an
`enrichers/` module) and one contract for all "turn X into graph
edges/nodes" logic.

**Acceptance test.** `ReferenceGraphBuilder` (or its successor) lives beside
`StructuralGraphBuilder`/`ImportGraphBuilder`, not in `references/`.

### 4.9 Move `build_repository_ir` and the Go builder fully out of `ir/`

**Why it's biased today.** Stage 2.0 already moved `ir/builders/go.py` →
`rig/frontends/go/ir_builder.py` — good. What remains (documented as
intentional in the migration report, §6.1): `rig/ir/repository.py` still
imports `rig.parsers.pipeline.ParsedFile` to dispatch parse results to a
registered `IRBuilder`. This is Tree-sitter-free and not currently harmful,
but it means `ir/` still isn't dependency-free of `parsers`.

**Requirement.** Relocate `build_repository_ir` orchestration one layer
above `ir/` (e.g. into a thin orchestration module or `cli/pipeline.py`
itself) so `ir/` is model + abstract `IRBuilder` + registry only, with zero
imports from `parsers`.

**Acceptance test.** `grep -rn "^from rig.parsers\|^import rig.parsers"
rig/ir/*.py` returns nothing.

---

## 5. Tier 3 — Opportunistic (do when convenient, not blocking)

These don't block adding languages but should be picked up when touching
nearby code, per the audit's Low-severity list:

- **Content-based language detection** for ambiguous extensions (`.h` C vs
  C++, shell shebangs) — `rig/languages/detector.py` is currently
  extension/filename-only.
- **Remove the Python special-case** in
  `rig/parsers/treesitter/factory.py` (it adds a stub specifically for
  `"python"`) once a real Python grammar/frontend exists — otherwise it's a
  second, inconsistent place Python is special-cased.
- **Type `RepositorySnapshot.metadata`** (`Any | None` today) instead of
  leaving it an untyped escape hatch.
- **Formalize the accidental SDK** — `cli/pipeline.py`'s helper functions
  (`build_snapshot`, `build_repository`, `build_symbol_table`, …) already
  work as a de facto SDK; make that a designed `rig.sdk` surface rather than
  an accident of the CLI's composition root.
- **Wire up or remove placeholders** — `CancellationToken`, `AnalysisLogger`
  in `rig/analysis/context.py` exist but nothing uses them.
- **Add graph deserialization** (`from_dict`/`from_json`) — serialization is
  one-way today (`graph_to_dict`/`graph_to_json`), so there's no persistence
  or round-trip boundary despite the spec's "Graph Store" goal.

---

## 6. Acceptance test for "RIG is language-neutral"

Borrowing the audit's own framing directly, because it's the sharpest
version of the bar: **add Python end-to-end — grammar, frontend/IR builder,
reference resolver, analyses — without editing any core package (`ir/`,
`symbols/`, `types/`, `references/`, `analysis/`, `graph/`) or the CLI
composition root, only adding new frontend code plus registrations.**

If that holds, Tier 1 + Tier 2 are done. Until then, "language-neutral" is
aspirational, not actual — however much the current package/class *names*
already say otherwise.

---

## 7. Suggested language order once Tier 1 is done

Unchanged from the audit's reasoning — each one stress-tests a specific
requirement above, so doing them in this order surfaces gaps earliest:

1. **Python** (done: none — currently Go only) — dynamic, module system, no
   visibility keyword. Stress-tests 3.2 (Visibility) and 4.2 (scope model).
2. **Java** — packages, access modifiers, generics. Closest to Go's shape;
   cheapest confirmation that Tier 1 actually generalized.
3. **Rust** — modules/crates, traits, `pub(...)`, `impl`. Stress-tests 3.2
   (visibility granularity) and 4.7 (relationship kinds).
4. **C** — preprocessor, translation units, headers, linkage. Stress-tests
   3.3 (grouping abstraction).
5. **C++** — namespaces, templates, multiple inheritance, headers. The
   hardest; validates everything above at once.

---

*This document should be updated (not left stale) as each Tier item lands —
treat unchecked items here as the source of truth for "is RIG language-
neutral yet," not the audit, which is a point-in-time snapshot from before
Stage 2.0.*
