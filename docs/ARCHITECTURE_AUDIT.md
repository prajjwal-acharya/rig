# ARCHITECTURE_AUDIT.md

> **Repository Intelligence Graph (RIG) — Stage 1 Architecture Audit**
>
> Status: Design Review
> Scope: Full-repository architectural evaluation prior to multi-language expansion
> Reviewer perspective: Production design review for an open-source developer-infrastructure
> project intended to be used by thousands of engineers.
> Constraint: **Analysis only.** No code was modified, no APIs changed, no features added.

---

## 0. How to read this document

This is an **engineering design review**, not a code review. It evaluates whether the
current abstractions can carry RIG to Go, Python, C, C++, Java, and Rust over a five-year
horizon without a fundamental redesign.

The audit is structured as:

1. **Executive summary** — the headline verdict and the five findings that matter.
2. **System model as-built** — what actually exists, versus what the specs describe.
3. **Per-package audit** — ten questions and a 1–10 scorecard for every major package.
4. **Cross-package review** — layering, cycles, data flow, ownership, semantic boundaries.
5. **Recommendations** — Critical / Medium / Low.
6. **Refactoring roadmap** — a phased plan (Stage 2.x).
7. **Five-year verdict.**

Throughout, findings are tagged `[C]` critical, `[M]` medium, `[L]` low so the roadmap can
reference them.

---

## 1. Executive Summary

RIG is, at the level of individual modules, an unusually well-built early-stage codebase.
The scanner, language detection, parser framework, tree-sitter backend, graph core model,
symbol table, and analysis *framework* are clean, deterministic, thread-aware, immutable by
default, and thoroughly tested (≈748 test functions across 86 files, a test-to-source LOC
ratio above 1.3:1). Identity is carefully namespaced. Registries are consistent. The
compiler-inspired pipeline shape is real and mostly honored.

**However, the architecture is not yet as language-independent as it presents itself, and
the gap is concentrated in exactly the layers that matter most for adding languages.** The
central problem is a single structural decision with cascading consequences:

> **The Intermediate Representation is under-modeled, so the semantic and analysis layers
> bypass it and reach directly into the Tree-sitter Go syntax tree.**

The IR captures top-level declaration *names* plus a handful of flags, but omits function
bodies, type annotations, struct fields, method receivers, parameter types, and expressions.
Every analysis that needs that information — reference resolution, type-relationship
analysis, dependency analysis — therefore re-opens the parse tree and walks **Go-specific
Tree-sitter node types** (`struct_type`, `qualified_type`, `type_alias`,
`method_declaration`, `selector_expression`, …). The IR, which the specifications call "the
compatibility layer" that "every graph builder consumes," is in practice bypassed by the
most important consumers.

This produces the five findings that define this audit:

| # | Finding | Severity |
|---|---------|----------|
| **F1** | IR under-modeling forces Tree-sitter/Go coupling into the `references`, `types`, and `analysis` layers. The canonical language-neutral layer is bypassed by its most important consumers. | **Critical** |
| **F2** | `TypeRelationshipAnalysis` and `DependencyAnalysis` carry language-neutral names and ids but are 100% Go syntax walkers. There is **no per-language dispatch**: for a Python/C/C++ file they silently produce nothing, with no error. | **Critical** |
| **F3** | Go's declaration and visibility model leaks into the neutral core: `is_exported: bool` (Go capitalization rule) on every `Declaration`/`Symbol`, and `Package` as the *sole* grouping concept. These do not map onto C/C++/Rust/Python/Java visibility and module models. | **Critical** |
| **F4** | The `plugins/` subsystem — a complete manifest/discovery/lifecycle/registry framework — is **decorative**. Nothing registers a parser, grammar, IR builder, or analysis through it; the CLI calls `load_all([], …)`. "Plugin-First" is unrealized; language support is added by editing `cli/pipeline.py`. | **Critical (for the stated vision)** |
| **F5** | Graph enrichment rebuilds the entire graph once per enricher (5+ full node/edge copies + re-sorts per run), `Properties` does O(n) linear-scan lookups on every node/edge, the type index is built twice, and each analysis re-walks the same syntax trees independently. These are *architectural*, not micro, bottlenecks. | **Medium (scales to Critical on monorepos)** |

None of these are fatal, and none require throwing the codebase away. But **F1–F3 must be
resolved before the second language is added**, because every language added on top of the
current shape multiplies the Go-specific tree-walking code rather than reusing a neutral
core. The good news: the framework abstractions (registries, `Analysis`/`Parser`/`IRBuilder`
contracts, the open-string `Node.type`, the capability model) are the *right* abstractions.
The work is to **complete the IR and route the semantic layer through it**, not to reinvent
the seams.

**Five-year answer (detailed in §7):** *Not without a bounded, well-scoped refactor first.*
The current architecture cannot absorb six languages as-is — but the required changes are
concentrated, identifiable, and can be staged. With the Stage 2 roadmap in §6 executed, the
answer becomes yes.

---

## 2. System Model As-Built

### 2.1 Actual pipeline

```
scan_repository            (scanner)        → RepositorySnapshot
detect_repository_languages(languages)      → RepositoryLanguageReport
parse_repository_files     (parsers)        → tuple[ParsedFile]      (Tree-sitter tree inside)
build_repository_ir        (ir)            → RepositoryIR
GoSymbolTableBuilder       (symbols)        → SymbolTable
GoReferenceResolver        (references)     → ReferenceIndex          ← re-reads Tree-sitter
GoTypeBuilder              (types)          → TypeIndex
StructuralGraphBuilder     (graph)          → Graph
  + ImportGraphBuilder / ReferenceGraphBuilder                        (graph enrichment)
CallGraphAnalysis / TypeRelationshipAnalysis / DependencyAnalysis (analysis) ← re-reads Tree-sitter
CLI                        (cli)            → formatted output
```

### 2.2 As-built vs. as-specified

The specs (`docs/specs/ARCHITECTURE.md`) describe a strict, one-directional compiler
pipeline where **IR is the sole compatibility boundary** and **every subsystem is a plugin**.
Reality diverges in two important places:

- **The IR is not the sole boundary.** Three downstream modules consume the raw Tree-sitter
  tree in addition to (or instead of) the IR. The IR is a boundary for *structure* (files,
  packages, top-level declarations) but not for *semantics* (bodies, types, references).
- **Plugins are not the extension mechanism.** Extension is by direct construction in
  `cli/pipeline.py` (`GoIRBuilder()`, `GoReferenceResolver(...)`, `GoTypeBuilder()`, the
  three analyses). The per-subsystem registries exist and are good, but they are populated
  by hand, not discovered.

Neither divergence is inherently wrong for an early stage — but both are load-bearing for
multi-language support, so both are called out below.

---

## 3. Per-Package Audit

Scoring key (1 = redesign required, 5 = works but limited/leaky, 8 = solid, 10 = exemplary).
Every score is justified inline.

---

### 3.1 `scanner/`

**Responsibility.** One clear responsibility: turn a filesystem path into a
`RepositorySnapshot` (locate root, walk, apply ignore rules, collect metadata). Cleanly
decomposed into `locator` / `walker` / `ignore` / `metadata` / `repository` orchestrator.
No leakage.

**Coupling.** Depends only on stdlib and its own `models`. `RepositoryLocator` is a
`Protocol`, and `scan_repository` takes injectable `locator`/`walker`/`ignore`/`metadata`
collaborators — textbook. No hidden, cyclic, or avoidable dependencies.

**Cohesion.** High. Every component is about file discovery; they evolve together.

**Public API.** `scan_repository`, `walk_repository`, `locate_repository`, plus the model
dataclasses. Minimal and honest. `RepositorySnapshot.metadata: Any | None` is a small
untyped escape hatch (reserved slot) — acceptable, but worth typing eventually `[L]`.

**Language neutrality.** Fully neutral. No language assumptions anywhere. `GitRepositoryLocator`
is the only VCS-specific piece and is correctly behind a `Protocol`.

**Extensibility.** Adding languages requires *nothing* here. Adding a Git-object scanner or a
watch-mode incremental scanner slots in behind the existing `Protocol`/injection seams.

**Replaceability.** Excellent. Filesystem scanner → Git-object scanner is a drop-in via
`RepositoryLocator`/`FileWalker` injection; higher layers consume `RepositorySnapshot` and
would not change.

**Performance.** `os.walk` with per-entry sorting is fine. Metadata collection (checksums)
is the cost center; it is opt-in-shaped and separable. No architectural bottleneck. One note:
metadata + checksum for every file is eager; incremental scanning will want to make hashing
lazy/cached `[L]`.

**Testing.** Strong — walker, ignore, locator, metadata, repository each tested. Missing: a
large-tree performance smoke test `[L]`.

**Future readiness.** Good for incremental (snapshot diffing is natural) and parallel
(stateless walk). No blockers.

| Resp | Coup | Cohes | API | Lang-Neutral | Extens | Replace | Perf | Test | **Overall** |
|---|---|---|---|---|---|---|---|---|---|
| 9 | 9 | 9 | 8 | 10 | 9 | 9 | 8 | 8 | **9** |

---

### 3.2 `languages/`

**Responsibility.** Map paths → `Language`, and aggregate language statistics. Single,
crisp responsibility.

**Coupling.** Depends on `scanner.models` (for `DiscoveredFile` in the pipeline helper) and
stdlib. `LanguageRegistry` validates duplicate extension/filename claims at construction —
good defensive design. No cycles.

**Cohesion.** High. Model, registry, detector, statistics, pipeline all cohere around
"what language is this file."

**Public API.** `Language`, `LanguageRegistry`, `LanguageDetector`, `DEFAULT_REGISTRY`,
`detect_repository_languages`. Minimal, immutable `Language` value object. Good.

**Language neutrality.** This package *is* the language table, so "neutrality" means "no
single language is privileged," which holds — 40+ languages are catalogued uniformly, Go has
no special status here.

**Extensibility.** Adding a language = one `Language(...)` row. Already contains Python, C,
C++, Java, Rust entries. Exemplary. Note the detector is extension/filename only — no content
sniffing (e.g. `.h` is C vs C++ ambiguous; shell shebangs) `[M]` for correctness later, not
architecture.

**Replaceability.** Detector is trivially swappable; registry is a value.

**Performance.** Dict lookups, `MappingProxyType` for immutability. O(1). Fine.

**Testing.** Detector, registry, catalog, statistics, pipeline all covered.

**Future readiness.** The `.h`/`.c`/`.cpp` ambiguity and per-file → per-language *parser*
selection will matter (C headers, multi-language files). The model supports it; the detector
policy will need enrichment.

| Resp | Coup | Cohes | API | Lang-Neutral | Extens | Replace | Perf | Test | **Overall** |
|---|---|---|---|---|---|---|---|---|---|
| 9 | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 8 | **9** |

---

### 3.3 `parsers/`

**Responsibility.** Define the language-agnostic `Parser` contract and the Tree-sitter
backend that implements it. Two concerns live here — the neutral framework (`interface`,
`model`, `registry`, `manager`, `pipeline`) and the Tree-sitter backend (`treesitter/`) —
but they are cleanly separated into sub-packages, and the framework never imports the backend.

**Coupling.** Framework depends on `languages`. `ParserManager` isolates parser failures (a
crashing parser becomes a failed `ParseResult`, never a process crash) — excellent
production instinct. `ParseResult.syntax_tree: Any` deliberately keeps the backend type out
of the neutral contract. The `treesitter` backend is the only place that imports
`tree_sitter`. `TreeSitterBackend` uses `threading.local` to reuse one parser per grammar
per thread (parsers aren't concurrency-safe) — a genuinely thoughtful detail.

**Cohesion.** The `SyntaxNode`/`SyntaxTree` wrapper (`treesitter/tree.py`) is a clean,
minimal facade over `tree_sitter.Node`. Good — it means alternate backends *could* present
the same node facade.

**Public API.** `Parser`, `ParseContext`, `ParseResult`, `ParserRegistry`, `ParserManager`,
`TreeSitterParser`, `Grammar`, `GrammarRegistry`, `build_default_registry`. Minimal and
correct. `TreeSitterParser` is generic — bound to a language+grammar at construction, with no
per-language logic. The factory turns "add a grammar to the catalog" into "a parser appears."
That is the right shape.

**Language neutrality.** The framework is neutral. `stubs.py` privileges Go/Python by name,
but only as stubs, and `factory.build_default_registry` special-cases `"python"` to add a
stub — a small, temporary wart `[L]`.

**Extensibility.** Adding a *parseable* language = add a `Grammar` (like
`treesitter/grammars/go.py`) to the catalog. This is genuinely easy and the strongest
extensibility story in the codebase. **Caveat:** having a syntax tree is necessary but far
from sufficient — see F1/F2; the hard part is downstream, not here.

**Replaceability.** Tree-sitter → ANTLR is *partially* clean: a new backend could implement
`Parser` and even present a `SyntaxNode`-shaped facade. **But** because `ir/builders/go.py`,
`references/resolver.py`, `analysis/typerelationships.py`, and `analysis/dependency.py`
import `rig.parsers.treesitter.tree` *concretely* and walk Tree-sitter's *Go node-type
strings*, a backend swap would break all four. So replaceability is good *at the parser
boundary* and poor *in practice* because downstream code punched through the boundary. This
is a symptom of F1, not a fault of this package.

**Performance.** Parser reuse per thread is good. `SyntaxNode.named_children()` allocates a
fresh tuple of fresh wrappers on every call; downstream code calls it repeatedly across
multiple independent tree walks (F5). The backend itself is fine; the cost is in how often
downstream re-walks.

**Testing.** Backend, parser, tree, grammar, and a Go-grammar integration test. Solid.

| Resp | Coup | Cohes | API | Lang-Neutral | Extens | Replace | Perf | Test | **Overall** |
|---|---|---|---|---|---|---|---|---|---|
| 8 | 8 | 8 | 9 | 8 | 9 | 6 | 7 | 8 | **8** |

Replaceability scored 6 despite a clean contract, because downstream leakage has already
compromised the boundary the contract was meant to protect.

---

### 3.4 `ir/` — the pivot of this audit

**Responsibility.** Define the canonical, language-independent representation and build it
from parse results. Here the responsibility is **too narrow in scope and too broad in
dependency** at the same time:

- *Too narrow in what it models.* `Declaration` is `FunctionDeclaration` (name, param count,
  exported), `TypeDeclaration` (name, `underlying_kind` string, exported),
  `VariableDeclaration` (name, const, exported), `ImportDeclaration` (path, alias). No bodies,
  no parameter/field/receiver/return types, no expressions, no nesting, no members. The IR
  describes a *table of contents*, not the *semantics*. This is the root cause of F1: anything
  richer than a name must go back to the syntax tree.
- *Too broad in dependency.* `ir/repository.py` imports `rig.parsers.pipeline.ParsedFile`, and
  `ir/builders/go.py` imports `rig.parsers.treesitter.tree`. So the "canonical
  backend-neutral IR package" imports the Tree-sitter parser package. The *model*
  (`ir/model.py`) is clean; the *build orchestration and the Go builder* drag `parsers` into
  the package. Ideally `ir/` holds the model + the abstract `IRBuilder` + registry, and the
  Go builder and `build_repository_ir` orchestration live one layer up.

**Coupling.** `ir.model` → stdlib only (good). `ir.repository` → `parsers.pipeline` `[M]`.
`ir.builders.go` → `parsers.treesitter.tree` (necessary for a Go builder, but it means the
Go builder should not live *inside* the neutral `ir` package — a placement/cohesion issue).

**Cohesion.** Mixed. The neutral model and the Go builder are two different rates of change
living together. When Python/C/C++ builders arrive, `ir/builders/` becomes a bag of
language-specific walkers inside the neutral package.

**Public API.** `SourceLocation`, `Declaration` hierarchy, `File`, `Package`, `RepositoryIR`,
`IRBuilder`, `IRBuilderRegistry`, `build_repository_ir`. The `IRBuilder` abstraction
(`tree: Any`) is correct. The **model is where neutrality breaks**:

- `is_exported` on `FunctionDeclaration`/`TypeDeclaration`/`VariableDeclaration` (F3). This is
  the Go rule "capitalized ⇒ exported." Python has no export concept (convention `_`); C uses
  `static`/external linkage; C++ adds access specifiers + `namespace` + anonymous namespaces;
  Java has `public/private/protected/package-private`; Rust has `pub`, `pub(crate)`,
  `pub(super)`. A single boolean is a Go/Java-shaped abstraction. This should become a
  richer `Visibility` (enum or small value object) owned by the neutral model but *populated*
  per language, or a language-scoped attribute bag.
- `Package` as the only grouping. Go and Java have packages; Python has modules/packages; C++
  has namespaces *and* translation units *and* headers; C has translation units + linkage;
  Rust has modules + crates. `File.package_name: str | None` plus "group repository by package
  name" is a Go/Java assumption baked into `RepositoryIRBuilder._build_packages`. Other
  languages need a more general "module/namespace/compilation-unit" grouping abstraction.
- `TypeDeclaration.underlying_kind: str` with values `"struct"|"interface"|"alias"|...` is
  Go's type taxonomy as a stringly-typed field. Classes, enums, unions, traits, records don't
  fit cleanly.
- `DeclarationKind` is a closed 4-member enum (function/type/variable/import). Classes,
  methods, fields, enums, macros, namespaces, modules, traits, interfaces have no home. Method
  declarations are explicitly dropped by the Go builder today.

**Language neutrality.** This is the least neutral of the "neutral" packages, precisely
because it's the one that claims neutrality most strongly. The identity scheme
(`ir/identifiers.py`) *is* neutral and well-designed. The declaration model is not.

**Extensibility.** Adding Python/C/C++ to the IR means: (a) new `DeclarationKind` members and
new `Declaration` subclasses (class, method, field, enum, macro, namespace/module), (b) a
neutral visibility model, (c) a neutral grouping model beyond `Package`, and (d) actually
carrying type/param/field/body information so downstream stops needing the syntax tree. This
is real design work, and it is the single highest-leverage change in the whole system.

**Replaceability.** The IR *model* could back an ANTLR frontend fine; the *builder* is
Tree-sitter-bound (expected). The concern is the package boundary, not swap-ability per se.

**Performance.** Building the IR is a single pass; fine. The under-modeling *causes* the
downstream re-traversal cost (F5) — an IR that carried type/field info would let semantic
layers consume it once instead of re-walking trees three times.

**Testing.** IR model, builder, Go builder, repository, visitor, identifiers, diagnostics,
integration — well covered *for what it models*. The gap is that the model itself is thin, so
the tests validate a thin thing thoroughly.

| Resp | Coup | Cohes | API | Lang-Neutral | Extens | Replace | Perf | Test | **Overall** |
|---|---|---|---|---|---|---|---|---|---|
| 5 | 5 | 5 | 6 | 4 | 4 | 6 | 6 | 8 | **5** |

The IR is the fulcrum. Its scores are the reason this audit exists.

---

### 3.5 `graph/`

**Responsibility.** Define the knowledge-graph value model (`Node`, `Edge`, `Graph`,
`Properties`, `GraphMetadata`), a `GraphIndex` lookup view, the `GraphBuilder` contract, an
accumulator, a registry, structural/import builders, and JSON serialization. That's arguably
two responsibilities (the core value model + the concrete Go-agnostic structural/import
builders), but the split into `graph/model.py` vs `graph/builders/` is clean.

**Coupling.** Core model → stdlib + `graph.properties` only. Builders → `ir`. `GraphBuilder`
consumes `RepositoryIR` and nothing lower. Good downward flow. **But** note that
`references/builder.py` (a graph *enricher*) lives in `references/`, while
`graph/builders/imports.py` and `structural.py` live here — inconsistent placement of the
same *kind* of thing (F: cohesion, see §4.5).

**Cohesion.** The decision to make `Node.type` a **deliberately open string** ("the set of
node kinds is owned by whichever GraphBuilder produces them") is exactly right and future-
proof. It stands in contrast to `RelationshipType`, a **closed enum** — new relationship
kinds (Rust `IMPLEMENTS_TRAIT`, C++ `INHERITS`, Java `THROWS`) require editing the core
model `[M]`. Two adjacent decisions, opposite philosophies.

**Public API.** `Node`/`Edge`/`Graph`/`GraphMetadata`/`Properties`/`GraphIndex`/`GraphBuilder`
/`GraphAccumulator`/serialization. Minimal, immutable, `slots=True`. `GraphIndex` correctly
separates "cheap value object" from "built-once lookup index." Very good.

**Language neutrality.** The core is neutral. Node *types* ("Function", "Package") are strings
produced by builders, so language-specific node kinds don't touch the core. `RelationshipType`
is the one closed, partly-Go-shaped surface (`EMBEDS`, `DECLARES_METHOD_*` are Go-ish; `EXTENDS`,
`IMPLEMENTS`, `OWNS` are declared but unused, presumably reserved).

**Extensibility.** New node kinds: free (open string). New relationship kinds: requires a core
edit (closed enum). New graph builders: register one. Mostly good; the enum is the friction.

**Replaceability.** Serialization is **one-way** (`graph_to_dict`/`graph_to_json`, no
`from_dict`). There is no persistence/store layer despite the spec's "Graph Store" and
"incremental updates" goals. Swapping in a real graph database, or round-tripping to disk, is
unimplemented surface, not just unwired `[M]`.

**Performance — the big one (F5).** Enrichment is implemented as *full rebuild*:
`ImportGraphBuilder`, `ReferenceGraphBuilder`, `CallGraphAnalysis`, `TypeRelationshipAnalysis`,
and `DependencyAnalysis` each construct a fresh `GraphAccumulator`, **copy every existing node
and edge into it**, add their new ones, and re-sort the whole thing at `build()`. In the
default pipeline the graph is fully rebuilt ~5 times in sequence. On a Kubernetes-scale graph
(hundreds of thousands of nodes/edges) this is O(N·k) copying + k full sorts for k enrichers —
a genuine architectural bottleneck, not a micro-op. Additionally, `Properties.get`,
`__getitem__`, and `__contains__` are **O(n) linear scans over a sorted tuple**, and every
node/edge carries a `Properties`; property access in hot loops is therefore quadratic-ish.
`Properties` chose tuple-backing for hashability, but a frozen dict-backed design would keep
hashability with O(1) access `[M]`.

**Testing.** Model, builder, structural, imports, serialization, properties, registry,
identifiers, visitor, plus structural/imports integration. Strong. Missing: a large-graph
enrichment performance test to catch the rebuild cost `[M]`.

| Resp | Coup | Cohes | API | Lang-Neutral | Extens | Replace | Perf | Test | **Overall** |
|---|---|---|---|---|---|---|---|---|---|
| 8 | 8 | 7 | 8 | 8 | 7 | 6 | 5 | 8 | **7** |

---

### 3.6 `symbols/`

**Responsibility.** Build and hold a `SymbolTable` (symbols + scopes) from `RepositoryIR`,
and resolve names through the scope chain. Clear responsibility, well separated (model / scope
/ table / builder / resolver / identifiers).

**Coupling.** `builder` → `ir`. `table`/`resolver`/`model`/`scope`/`identifiers` are
self-contained. The docstring's deliberate note that symbol identity is its own namespace
(never a graph-node id, never an IR id) is careful and correct.

**Cohesion.** High.

**Public API.** `Symbol` hierarchy, `Scope` hierarchy, `SymbolTable`, `SymbolResolver`,
`GoSymbolTableBuilder`. Thread-safe table with deterministic sorted iteration. Good.

**Language neutrality.** Mixed, and subtly so:
- The **scope model is Go/Java-shaped**: `ScopeKind = REPOSITORY | PACKAGE | FILE`. There is
  no function/block/namespace/class scope. Python needs module + class + function scopes; C++
  needs namespace + class + block; Rust needs module + block. `SymbolResolver` walks a strictly
  vertical file→package→repository chain and explicitly "can never perform cross-package
  resolution" — fine for Go's package-global model, insufficient for languages with imports
  that bind names into a file's scope, or nested lexical scopes.
- `is_exported` propagates from IR into `Symbol` (F3 again).
- The class is named `GoSymbolTableBuilder` but its docstring insists it "contains no
  Go-specific logic." Both can't stay true: today it's neutral *because the IR is thin*; the
  moment the IR carries classes/methods/nested scopes, this builder either stays neutral (good)
  or fragments per language. The Go-prefixed name is misleading either way `[L]`.

**Extensibility.** Adding block/class/namespace scopes and non-vertical (import-based)
resolution is a real extension. The `Scope` base with `symbol_ids` and `parent_id` is a
reasonable foundation, but the closed `ScopeKind` and vertical-only resolver will need to
grow. Manageable, not free.

**Replaceability.** Table and resolver are cleanly separable.

**Performance.** `Scope.lookup_local` is a linear scan over `symbol_ids` tuples; per-scope
symbol counts are usually small, so acceptable. Table is dict-backed O(1). Fine.

**Testing.** model, scope, table, builder, resolver, integration, identifiers — thorough.

| Resp | Coup | Cohes | API | Lang-Neutral | Extens | Replace | Perf | Test | **Overall** |
|---|---|---|---|---|---|---|---|---|---|
| 8 | 8 | 8 | 7 | 5 | 6 | 8 | 7 | 8 | **7** |

---

### 3.7 `references/`

**Responsibility.** Two responsibilities are bundled here: (a) *produce* a `ReferenceIndex`
by resolving identifiers (`resolver.py`, `index.py`, `model.py`), and (b) *project* references
into graph edges (`builder.py`, `ReferenceGraphBuilder`). (b) is a graph builder that happens
to live in `references/` — a cohesion/placement inconsistency versus `graph/builders/`
(§4.5) `[M]`.

**Coupling.** `resolver.py` imports `parsers.treesitter.tree` (F1) and walks **Go node types**
(`selector_expression`, `short_var_declaration`, `call_expression`, `type_identifier`,
`var_spec`, …) and hardcodes `_GO_PREDECLARED` (Go builtins). `builder.py` imports `rig.graph`.
So this package reaches *down* to the raw parser and *sideways/forward* to graph. It is one of
the four Tree-sitter-coupled modules.

**Cohesion.** The index/model are neutral; the resolver is entirely Go-specific; the graph
builder is a different concern. Three rates of change in one package.

**Public API.** `Reference`/`ResolvedReference`/`UnresolvedReference`, `ReferenceIndex`,
`ReferenceResolver` (abstract, neutral), `GoReferenceResolver`, `ReferenceGraphBuilder`. The
abstract `ReferenceResolver` contract is neutral and correct; the concrete resolver is honestly
named `GoReferenceResolver` and honestly documents its Tree-sitter dependence — commendable
transparency. `ReferenceIndex` is a nicely built inverted index (by symbol/file/identifier).

**Language neutrality.** The *contract* is neutral; the *only implementation* is Go-only and
tree-coupled. `ReferenceKind` (type/function/variable/constant/package) is reasonably neutral
but omits fields/methods/labels/macros.

**Extensibility.** Because the resolver is behind an abstract contract, a `PythonReferenceResolver`
*could* be added — but it would again reach into Tree-sitter Python node types, duplicating the
walking machinery per language. Worse, resolution quality is low (selector expressions, imports,
and methods are all skipped), so the reference layer today resolves only unqualified intra-file/
package names. For Python/C++/Java where most references are qualified or method calls, the
current resolver shape yields little.

**Replaceability.** Resolver is swappable by contract; index is standalone.

**Performance.** Full independent tree walk per file (F5), plus this is *another* full-tree
traversal on top of the IR builder's and the analyses'.

**Testing.** model, index, resolver, visitor, graph_builder, integration, identifiers,
diagnostics — thorough for Go.

| Resp | Coup | Cohes | API | Lang-Neutral | Extens | Replace | Perf | Test | **Overall** |
|---|---|---|---|---|---|---|---|---|---|
| 5 | 4 | 5 | 7 | 4 | 5 | 6 | 6 | 8 | **5** |

---

### 3.8 `types/`

**Responsibility.** Build and hold a `TypeIndex` of declared types, and resolve type names.
Clean and small.

**Coupling.** `builder` → `ir` + `symbols`. `index`/`model`/`resolver` self-contained. No
Tree-sitter here (the type *relationships* that need syntax live in `analysis/`, correctly not
here). Good separation.

**Cohesion.** High.

**Public API.** `Type` hierarchy, `TypeIndex`, `TypeResolver`, `GoTypeBuilder`. Immutable,
thread-safe, incremental per-kind counts for O(1) stats. Nicely done.

**Language neutrality.** `TypeKind = STRUCT | INTERFACE | ALIAS | NAMED` is Go's type
taxonomy. Classes, enums, unions, traits, records, templates, generics have no representation
`[M]`. `Type.package: str | None` inherits the Go grouping assumption (F3). `GoTypeBuilder` is
Go-named but claims neutrality — same tension as the symbol builder `[L]`.

**Extensibility.** Adding class/enum/union/trait kinds is a closed-enum edit plus new
subclasses. The index/resolver machinery is neutral and would carry them. Moderate effort.

**Replaceability.** Index and resolver are cleanly separable.

**Performance.** Dict-backed O(1) by id/symbol/declaration; `by_name` returns sorted. Fine.
**But** `GoTypeBuilder().build()` is invoked in *both* `cli/pipeline.build_type_index` *and*
inside `TypeRelationshipAnalysis.execute` — the type index is built twice per run (F5,
duplicate indexing) `[M]`.

**Testing.** model, index, builder, resolver, visitor, integration, identifiers, diagnostics.
Strong.

| Resp | Coup | Cohes | API | Lang-Neutral | Extens | Replace | Perf | Test | **Overall** |
|---|---|---|---|---|---|---|---|---|---|
| 8 | 8 | 8 | 8 | 5 | 6 | 8 | 6 | 8 | **7** |

---

### 3.9 `analysis/`

This package must be scored in two halves, because they diverge sharply.

**The framework** (`interface`, `context`, `result`, `manager`, `registry`, `capability`,
`diagnostics`) is excellent:
- `Analysis` is a clean contract with `required_capabilities` and (informational)
  `supported_languages`.
- `AnalysisContext` passes everything explicitly — no global state — and marks
  symbols/references/graph optional so capability validation is meaningful.
- `AnalysisManager` validates capabilities before dispatch, times execution, and **isolates
  failures** (one analysis raising never stops the others). It correctly owns identity/timing/
  version on results, leaving analyses to report only success/diagnostics/artifacts/metadata.
- `AnalysisResult` is immutable with `MappingProxyType`-wrapped artifacts/metadata.
- Determinism is enforced (registry sorts by id).

This is production-grade framework design. Framework sub-score: **8**.

**The implementations** are the problem (F2):
- `CallGraphAnalysis` consumes only IR + SymbolTable + ReferenceIndex — no Tree-sitter — and
  is *structurally* the most neutral analysis. But it depends on the `ReferenceIndex`, which is
  produced only by the Go resolver, so it is Go-only in practice, and it only sees unqualified
  direct calls (selector calls were never resolved upstream).
- `TypeRelationshipAnalysis` and `DependencyAnalysis` **import `parsers.treesitter.tree` and
  walk Go node-type strings directly** (`struct_type`, `field_declaration_list`,
  `qualified_type`, `pointer_type`, `type_alias`, `type_spec`, `method_declaration`,
  `parameter_declaration`, `selector_expression`, …), hardcode `_GO_BUILTIN_TYPES`, and apply
  Go's `_is_exported` capitalization rule. They also re-run `GoTypeBuilder` internally.

The critical architectural defect: **these two analyses have language-neutral ids
(`"type-relationships"`, `"dependency-analysis"`) and neutral class names, are registered in a
neutral registry, and yet are entirely Go implementations — with no per-language dispatch.**
When a Python or C++ file flows through, `child.type == "type_declaration"` (a Go node type)
never matches, so the analysis **silently emits nothing** for that file. No error, no
diagnostic, no "unsupported language." A user pointing RIG at a Python repo would get an empty
type-relationship graph and a green success result. That is a correctness-and-trust failure
waiting to happen at the exact moment the project's headline feature (multi-language) ships.

The right shape: either (a) these become `GoTypeRelationshipAnalysis` etc. gated by
`supported_languages` with the manager filtering by language, or (b) — far better — they are
rewritten to consume a *complete* IR (F1) so a single neutral analysis works across all
languages. `supported_languages` already exists in the contract but **the manager does not
consult it** for dispatch — a latent hook that is defined but unused `[M]`.

**Coupling.** Framework: `graph`, `ir`, `references`, `symbols` — all downward, fine.
Implementations additionally: `parsers.treesitter` (F1), `types.builder` (duplicate build).

**Language neutrality.** Framework neutral; two of three implementations Go-only while
presenting as neutral. This is the most dangerous neutrality gap because it's *disguised*.

**Extensibility / Replaceability / Performance / Testing.** Framework extensible and testable
(manager, registry, capability, context, result, interface all covered). Implementations:
each re-walks trees (F5), rebuilds the graph (F5), rebuilds the type index (F5). Integration
tests exist and are Go-focused.

| Resp | Coup | Cohes | API | Lang-Neutral | Extens | Replace | Perf | Test | **Overall** |
|---|---|---|---|---|---|---|---|---|---|
| 6 | 5 | 6 | 8 | 3 | 5 | 6 | 5 | 7 | **5** |

(Framework alone would score ~8; the disguised-Go implementations pull the package to 5.)

---

### 3.10 `cli/`

**Responsibility.** Command dispatch, pipeline wiring, and human-readable formatting. Two
concerns (orchestration vs. formatting) cleanly split into `pipeline.py` vs `formatting.py`.

**Coupling.** `pipeline.py` is the **integration seam of the whole system** and imports nearly
everything. That is expected of a top-level composition root. The concern is *how* it composes:
it **hardcodes the Go stack** — `GoIRBuilder()`, `GoSymbolTableBuilder()`,
`GoReferenceResolver(...)`, `GoTypeBuilder()`, and the three analyses — rather than resolving
implementations from registries keyed by language. `build_repository` even wraps a single
`GoIRBuilder` in an `IRBuilderRegistry`, using the registry as a container of one hardcoded
entry. So the registries exist but the composition root bypasses their purpose `[M]`.

**Cohesion.** Good. `SemanticAnalysisResult` and the sequential graph-threading in
`run_semantic_analyses` are clear.

**Public API.** CLI commands + pipeline helper functions. The helper functions
(`build_snapshot`, `build_repository`, `build_symbol_table`, …) form a de-facto SDK — which is
consistent with the spec's "CLI is built on APIs" principle, and a nice property. But it is an
*accidental* SDK, not a designed one `[L]`.

**Language neutrality.** The pipeline is Go-wired end to end. Adding Python means editing
`pipeline.py` to branch on language and construct Python builders/resolvers/analyses — the
opposite of the "add a plugin / add a catalog row" story the parser layer achieves.

**Extensibility.** Poor as-is: each new language edits the composition root. This is the
concrete, user-visible cost of F1/F2/F4 converging.

**Replaceability.** The pipeline functions are individually swappable; the wiring is the issue.

**Performance.** Sequential; recomputes some artifacts (type index) redundantly (F5). For a CLI
this is acceptable now, and the pipeline is where parallelism would later be introduced.

**Testing.** `test_cli.py`, `test_cli_pipeline.py`. Covered at the command/pipeline level.

| Resp | Coup | Cohes | API | Lang-Neutral | Extens | Replace | Perf | Test | **Overall** |
|---|---|---|---|---|---|---|---|---|---|
| 7 | 6 | 7 | 7 | 4 | 5 | 6 | 6 | 7 | **6** |

---

### 3.11 `plugins/` (audited though outside the required list — it is load-bearing for the vision)

**Responsibility.** A complete plugin subsystem: `manifest`, `discovery` (static + entry-point
sources), `registry`, `manager` (lifecycle + load report), `context`, `capability`, `types`,
`errors`, `interface`.

**Coupling.** Self-contained; depends only on stdlib and its own modules. Clean.

**Cohesion.** Internally cohesive and, in isolation, a nicely designed lifecycle framework.

**Public API.** Broad and well-formed (`Plugin`, `PluginManifest`, `PluginManager`,
`PluginRegistry`, discovery sources, capability, state/type enums).

**The finding (F4).** **Nothing uses it to extend anything.** The only consumer is
`cli/commands.run_scan`, which calls `plugin_manager.load_all([], plugin_context)` — an empty
list — and prints "Plugins: (None)". No parser, grammar, IR builder, resolver, or analysis is
registered *through* the plugin system. The actual extension points (the per-subsystem
registries) are populated by direct construction in `cli/pipeline.py`. So RIG has **two
unrelated extensibility mechanisms**: a real-but-manual one (subsystem registries) and a
polished-but-inert one (`plugins/`). The spec's flagship "Plugin-First" principle is
therefore not implemented.

Additionally, there are **two different `Capability` types** with the same name:
`rig.plugins.capability.Capability` (a dataclass of provides/consumes/produces) and
`rig.analysis.capability.Capability` (an enum of ir/symbol_table/…). Same word, unrelated
concepts, guaranteed to confuse contributors `[M]`.

**Language neutrality / Extensibility / Replaceability.** N/A in practice because it is
disconnected. As-designed it *could* be the unification point (see roadmap).

**Performance.** N/A.

**Testing.** Registry, manifest, discovery, manager, interface all tested — so a well-tested
subsystem that isn't wired in. This is effort spent ahead of integration.

| Resp | Coup | Cohes | API | Lang-Neutral | Extens | Replace | Perf | Test | **Overall** |
|---|---|---|---|---|---|---|---|---|---|
| 7 | 8 | 7 | 7 | n/a | 3 | 4 | n/a | 7 | **4** (as integrated) / 7 (in isolation) |

---

### 3.12 Scorecard summary

| Package | Overall | Headline concern |
|---|---|---|
| `scanner/` | **9** | None material; type the metadata slot |
| `languages/` | **9** | Content-based detection later |
| `parsers/` | **8** | Boundary is clean but already punched through downstream |
| `ir/` | **5** | **Under-modeled + Go visibility/package assumptions (F1, F3)** |
| `graph/` | **7** | Full-rebuild enrichment + O(n) Properties + closed `RelationshipType` (F5) |
| `symbols/` | **7** | Go/Java-shaped scope model; vertical-only resolution |
| `references/` | **5** | Tree-sitter-coupled Go-only resolver; misplaced graph builder (F1) |
| `types/` | **7** | Go type taxonomy; built twice (F5) |
| `analysis/` | **5** | **Neutral-named, Go-only implementations, no dispatch (F2)** |
| `cli/` | **6** | Hardcoded Go composition root; bypasses registries + plugins |
| `plugins/` | **4** | Built but disconnected (F4) |

---

## 4. Cross-Package Review

### 4.1 Layering — does every dependency point downward?

Intended layering (bottom → top): `scanner → languages → parsers → ir → {symbols, types} →
references → graph → analysis → cli`.

Mostly honored, with these deviations:

- **`ir → parsers` (downward-but-wrong-direction conceptually).** The "canonical
  language-independent IR" imports the Tree-sitter parser package (`ir/repository.py` →
  `parsers.pipeline`; `ir/builders/go.py` → `parsers.treesitter.tree`). Since parsing precedes
  IR in the data flow this isn't a *cycle*, but it means the neutral IR package contains a
  backend-specific builder. Cleaner: keep `ir/` as pure model + abstract builder + registry;
  move `build_repository_ir` and `builders/go.py` into an orchestration layer above `ir/` `[M]`.
- **Semantic/analysis layers skip the IR straight to the parser (F1).**
  `references/resolver.py`, `analysis/typerelationships.py`, `analysis/dependency.py` import
  `parsers.treesitter.tree`. This is a **layer-skipping dependency**: the pipeline says
  `IR → semantic → analysis`, but these modules bypass IR back down to the raw syntax layer.
  This is the most important layering violation and the concrete form of F1.
- **`references → graph`.** `references/builder.py` (a graph enricher) depends on `graph`.
  Since graph is downstream, this is forward/downward — acceptable direction — but it puts a
  graph-building concern in the references package (cohesion, §4.5).

### 4.2 Circular dependencies

**No import cycles were found.** The registries, identity modules, and value objects are
deliberately self-contained (each `identifiers.py` re-implements its own digest rather than
importing a sibling — a conscious choice documented in comments to keep identity namespaces
independent). This is a real strength: the coupling problems here are about *direction and
placement*, not *cycles*. The system is acyclic today; the risk is that ad-hoc per-language
wiring in `cli/pipeline.py` plus Tree-sitter reach-through could grow into cycles as languages
are added if a shared "language binding" module isn't introduced first.

### 4.3 Data flow

The pipeline (`scan → detect → parse → IR → symbols/references/types → graph → analysis → CLI`)
is clean, deterministic, and each stage is independently testable — the compiler-inspired
design goal is genuinely met for *structure*. Two simplifications are available:

1. **Collapse the redundant traversals.** IR building, reference resolution, type-relationship
   analysis, and dependency analysis each independently walk every file's syntax tree. A single
   richer IR pass (F1) would let symbols/references/types/analyses consume the IR, turning four
   tree walks into one. This both simplifies the flow and removes the F5 cost.
2. **Deduplicate the type index.** It is built in the CLI pipeline and again inside
   `TypeRelationshipAnalysis`. The `AnalysisContext` should carry the `TypeIndex` as an optional
   capability (like symbols/references/graph) so it's built once and passed in.

### 4.4 Ownership — canonical owner of each concept

| Concept | Intended owner | Actual owner(s) | Verdict |
|---|---|---|---|
| Files / packages / declarations | IR | IR | ✅ single owner |
| Symbols / scopes | Symbol Table | Symbol Table | ✅ |
| Types | Type Index | Type Index — **but built twice** | ⚠️ duplicated construction (F5) |
| References | Reference Index | Reference Index | ✅ |
| Calls | Call Graph | Call Graph (artifact) + CALLS edges (graph) | ✅ (graph is a projection) |
| Type relationships | TypeRelationshipGraph | artifact + graph edges | ✅ projection |
| Dependencies | Dependency Graph | artifact + DEPENDS_ON edges | ✅ projection |
| **Visibility** | (should be IR) | **re-derived ad hoc** via `_is_exported` in `ir/builders/go.py`, `symbols/builder.py` (via IR), and `analysis/dependency.py` | ❌ **`_is_exported` logic exists in multiple places** (F3) |
| **Go builtins/predeclared** | (should be one Go language module) | duplicated: `_GO_PREDECLARED` in `references/resolver.py`, `_GO_BUILTIN_TYPES` in `analysis/typerelationships.py` | ❌ **duplicated Go knowledge** |
| **Grouping (package) semantics** | IR | IR builder + dependency analysis both encode "last import path segment = package name" | ❌ Go convention duplicated |

The projections into the graph are handled well (single-source artifacts, graph as a
derived view). The **language-specific knowledge is what's scattered**: export rules, builtin
lists, and import-path→package conventions appear in multiple modules. When a second language
arrives, this scattering multiplies.

### 4.5 Semantic boundaries — syntax in parser, semantics in semantic layer, graph as projection

| Rule | Status |
|---|---|
| Syntax stays in the parser layer | ❌ **Violated.** `references`, `types`-relationships, and `dependency` analysis all consume raw Tree-sitter syntax (F1). Syntax has leaked two layers up. |
| Semantics stay in the semantic layer | ⚠️ Partially. Semantic *facts* are computed in the right places, but they are computed *from syntax re-read there*, not from a semantic IR. |
| Analyses consume semantic indexes | ⚠️ CallGraph does (consumes ReferenceIndex/SymbolTable). TypeRelationship/Dependency do **not** — they consume syntax directly. |
| Graph is a projection | ✅ **Honored.** The graph is consistently a derived view; artifacts (CallGraph, TypeRelationshipGraph, DependencyGraph) are the sources of truth and edges are projections. This part is done right. |

Also a **component-placement inconsistency**: graph enrichers live in two places —
`graph/builders/{structural,imports}.py` versus `references/builder.py` (ReferenceGraphBuilder)
and the enrichment logic embedded *inside* the three analyses. "Turn X into graph edges" should
be one consistent role in one place (see roadmap Stage 2.5).

---

## 5. Recommendations

### 5.1 Critical (must be fixed before adding new languages)

- **C1 — Complete the IR (resolves F1).** Extend the IR to carry the semantic detail the
  downstream layers currently re-derive from syntax: parameter types, return types, struct/class
  fields and their types, method receivers, type references within declarations, and (at least a
  normalized handle to) call targets. Once the IR carries this, `references`, `types`, and the
  three analyses can consume the IR instead of `parsers.treesitter.tree`. This is the linchpin —
  most other critical items become easy once it lands.

- **C2 — Introduce a neutral visibility and grouping model (resolves F3).** Replace
  `is_exported: bool` with a `Visibility` value (e.g. `PUBLIC | PRIVATE | PROTECTED |
  PACKAGE | CRATE | MODULE | INTERNAL | UNKNOWN`, or a small language-tagged struct) owned by the
  neutral model and populated per language. Generalize `Package` into a
  `Module`/`CompilationUnit`/`Namespace` grouping abstraction so C/C++ (translation units,
  namespaces, headers) and Rust (modules/crates) are representable. Keep Go mapping trivial
  (capitalized → PUBLIC; package → module).

- **C3 — Make analyses language-aware and honest (resolves F2).** Either (a) rename the Go
  implementations (`GoTypeRelationshipAnalysis`, `GoDependencyAnalysis`), have the
  `AnalysisManager` **consult `supported_languages`** and skip/emit an explicit
  "unsupported language" diagnostic instead of silently producing nothing; or (b) preferably,
  rewrite them against the completed IR (C1) so one neutral analysis serves all languages. Until
  one of these lands, RIG must never present a green, empty result for an unsupported language.

- **C4 — Decide the extension mechanism and use exactly one (resolves F4).** Either wire the
  `plugins/` system into real registration (a language plugin contributes a grammar + IR builder
  + resolver + analyses via the plugin manager into the subsystem registries) **or** delete/park
  `plugins/` and formalize a lightweight "language binding" registry that `cli/pipeline.py`
  resolves per detected language. Having two mechanisms, one inert, is worse than either alone.
  Also **rename one of the two `Capability` types** to end the name collision.

- **C5 — Replace hardcoded Go wiring with a language-binding registry.** `cli/pipeline.py`
  should resolve, per language present in the repo, the tuple `(parser, ir_builder,
  reference_resolver, type_builder, analyses)` from a registry — so adding a language never
  edits the composition root. This is the concrete acceptance test for "can we add a language
  without touching core?"

### 5.2 Medium (should be improved before scale / second-language quality matters)

- **M1 — Fix graph-enrichment rebuild cost (F5).** Provide an append/enrich path on the graph
  (mutable builder handed through the pipeline, or a single accumulator threaded through all
  enrichers) so the graph is sorted/materialized once, not once per enricher.
- **M2 — Make `Properties` O(1).** Back it with a frozen mapping (hashable + fast lookup)
  instead of linear scans over a sorted tuple.
- **M3 — Build the type index once.** Add `TypeIndex` to `AnalysisContext`/capabilities; stop
  rebuilding it inside `TypeRelationshipAnalysis`.
- **M4 — Open the `RelationshipType` model or make it registry-owned**, mirroring the
  open-string `Node.type`, so language-specific edge kinds don't require core edits.
- **M5 — Generalize the scope model** (`symbols/scope.py`): add block/class/namespace/module
  scope kinds and non-vertical (import-bound) resolution, needed by every non-Go language.
- **M6 — Centralize per-language knowledge.** One Go module owns predeclared identifiers,
  builtin types, export rules, and import-path conventions; other packages import from it rather
  than re-declaring (`_GO_PREDECLARED`, `_GO_BUILTIN_TYPES`, `_is_exported` appear in 3+ places).
- **M7 — Move `ir/builders/go.py` and `build_repository_ir` out of the neutral `ir/` package**
  into an orchestration layer, keeping `ir/` dependency-free of `parsers`.
- **M8 — Consolidate graph-enricher placement** (§4.5): all "project X into edges" logic lives
  under `graph/builders/` (or an `enrichers/` module) with a consistent contract, not spread
  across `references/` and inside analyses.
- **M9 — Add `from_dict`/`from_json` graph deserialization** and a persistence boundary, to make
  the "Graph Store," export, and incremental-update goals reachable.

### 5.3 Low (opportunistic)

- **L1 — Rename `GoSymbolTableBuilder`/`GoTypeBuilder`** to neutral names if they truly stay
  neutral, or accept they'll fragment per language and keep the prefix consistently.
- **L2 — Type `RepositorySnapshot.metadata`** instead of `Any | None`.
- **L3 — Content-based language detection** for ambiguous cases (`.h`, shebangs).
- **L4 — Remove the Python special-case** in `parsers/treesitter/factory.py` once a real Python
  grammar exists.
- **L5 — Formalize the accidental SDK** (the `cli/pipeline.py` helper functions) into a real
  `rig.sdk` surface, per the "API-First" principle.
- **L6 — Wire up the placeholders** (`CancellationToken`, `AnalysisLogger`) or remove until
  needed.
- **L7 — Add architecture tests** (import-linter/contract tests) that *enforce* layering — e.g.
  "nothing outside `parsers/` and `ir/builders/` may import `parsers.treesitter`." This would
  have caught F1 automatically and will prevent regression during the refactor.

---

## 6. Refactoring Roadmap (Stage 2.x)

Ordered so each stage unblocks the next; every stage ships independently and keeps Go working.

- **Stage 2.0 — Guardrails first.** Add architecture/contract tests (L7) encoding the intended
  layering, and a large-repository performance smoke test (M1 baseline). These lock in behavior
  before refactoring and make regressions visible. *Low risk, high leverage.*

- **Stage 2.1 — IR normalization & completion (C1, C2, M7).** The keystone. Extend the
  declaration model (fields, params, receivers, return/param type references, call targets);
  introduce neutral `Visibility` and a general grouping abstraction; move the Go builder and
  `build_repository_ir` out of `ir/`. Keep Go green throughout. Everything downstream depends on
  this.

- **Stage 2.2 — Route the semantic layer through the IR (C1 cont., F1).** Rewrite
  `GoReferenceResolver` and the type-relationship/dependency logic to consume the completed IR
  instead of `parsers.treesitter`. After this, `grep -rl parsers.treesitter rig/` should return
  only `parsers/` and `ir/builders/`. This removes the layer-skipping and restores the semantic
  boundary.

- **Stage 2.3 — Analysis neutrality & dispatch (C3, M3, M6).** With analyses reading the IR,
  make them genuinely language-neutral (or explicitly language-gated via `supported_languages`
  honored by the manager). Build the type index once and pass it via context. Centralize Go
  builtins/export rules into one Go language module.

- **Stage 2.4 — Extension unification (C4, C5).** Introduce the language-binding registry that
  maps a language to its `(grammar, ir_builder, resolver, type_builder, analyses)`; make
  `cli/pipeline.py` resolve it per detected language. Decide plugins-vs-registry and remove the
  redundant path; fix the `Capability` name collision.

- **Stage 2.5 — Graph performance & consistency (M1, M2, M4, M8).** Single-materialization
  enrichment, O(1) `Properties`, open/registry-owned relationship kinds, and consolidated
  enricher placement.

- **Stage 2.6 — Scope generalization (M5).** Block/class/namespace/module scopes and
  import-bound resolution — the last structural prerequisite for high-quality Python/C++/Java
  reference resolution.

- **Stage 2.7 — Persistence & store boundary (M9).** Graph (de)serialization round-trip and a
  storage abstraction, enabling incremental analysis, export, and the query engine.

- **Stage 2.8 — First non-Go language as the acceptance test.** Add Python end-to-end
  (grammar → IR builder → resolver → analyses) *without editing any core package or the
  composition root*. If that holds, the architecture has been proven multi-language.

**Suggested order to add the six languages afterward**, by architectural stress applied:
Go (done) → **Python** (dynamic, module system, no visibility keyword — exercises C2/M5) →
**Java** (packages, access modifiers, generics — closest to Go's shape) → **Rust** (modules/
crates, traits, `pub(...)`, `impl` — exercises visibility + relationship kinds) → **C**
(preprocessor, translation units, headers, linkage — exercises grouping) → **C++** (namespaces,
templates, multiple inheritance, headers — the hardest, validates everything).

---

## 7. Five-Year Verdict

> **"Can RIG support Go, Python, C, C++, Java, and Rust for the next five years without a
> fundamental architectural redesign?"**

**Not in its current shape — but yes after a bounded, well-scoped refactor that does not
require redesigning the system's fundamentals.**

The distinction matters. A *fundamental* redesign would mean the core seams are wrong: the
pipeline shape, the registry pattern, the immutable value model, the capability/analysis
framework, the open-string node model, the identity scheme. **None of those are wrong.** They
are, in fact, the parts that will carry RIG for five years. The framework instincts here are
consistently good.

What is wrong is **localized and identifiable**: the IR was modeled for a proof-of-concept
depth (names + flags) and the semantic/analysis layers compensated by reaching into the Go
syntax tree, while Go's visibility and package model leaked into the "neutral" core, and the
advertised plugin mechanism was never connected. Each of these is a *filling-in* or a
*re-routing*, not a teardown:

- Completing the IR is additive to a model that already has the right identity and shape.
- Re-routing the semantic layer through the IR removes coupling; it doesn't invert any
  dependency direction (there are no cycles to break).
- Generalizing visibility/grouping/scopes extends existing enums and value objects.
- Unifying the extension mechanism uses registries that already exist.

If the Stage 2 roadmap in §6 is executed — with **Stage 2.1 (IR) and Stage 2.2 (route semantic
layer through IR) treated as prerequisites for the second language** — RIG can absorb all six
target languages incrementally, each new language adding a grammar + IR builder + a small amount
of language-specific mapping, without touching the core or the composition root. That is the
definition of an architecture that lasts.

**The single most important sentence of this audit:** *do not add the second language until the
IR is complete enough that no analysis needs to import `parsers.treesitter`.* Every language
added before that point pays the Go-tree-walking tax again and makes the eventual refactor
larger. Every language added after it is cheap.

The honest current state is a **7/10 architecture wearing a 5/10 IR and a disconnected plugin
system**. Fix those two things — nothing more fundamental is required — and RIG is genuinely
ready to become the multi-language engineering-intelligence layer its specifications describe.

---

*End of Stage 1 Architecture Audit.*
