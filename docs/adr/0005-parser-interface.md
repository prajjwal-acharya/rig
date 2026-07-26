# ADR-005: Parser Interface

## Status

Accepted

## Date

2026-07-27

## Context

Each supported language needs a parser, but downstream stages should not depend
on parser-specific APIs. The parser layer must handle unsupported languages,
partial or invalid source files, parser diagnostics, timing information, and
future backend diversity.

The current implementation includes parser contracts in `rig.parsers`, language
detection in `rig.languages`, and Tree-sitter support in
`rig.parsers.treesitter`.

## Decision

Define a language-agnostic parser interface that accepts a `ParseContext` and
returns a `ParseResult`.

The current parser interface and pipeline include:

- `Parser` as the abstract parser contract.
- `ParseContext` containing file path, language metadata, source text, and
  parser configuration.
- `ParseResult` containing success status, parser ID, language, diagnostics,
  elapsed time, and an optional syntax tree.
- `Diagnostic` and `DiagnosticSeverity` for parser diagnostics.
- `ParserRegistry` and `ParserManager` for language-to-parser lookup and
  execution.
- `parse_repository_files` to parse language-annotated repository files.
- Stub parsers for early language coverage where a real parser is not present.
- Tree-sitter grammar, backend, parser, factory, syntax tree, syntax node, and
  traversal helpers.
- A concrete Go Tree-sitter grammar adapter using `tree-sitter-go`.

Parser output is intentionally not the IR. Parsers produce syntax trees and
diagnostics; language-specific IR builders convert successful parse results
into repository IR.

## Alternatives Considered

### Parser directly returns IR

Returning IR directly would simplify the pipeline, but it would merge parsing
and extraction. Keeping parsing separate allows syntax-tree consumers such as
reference resolution, call graph analysis, type relationship analysis, and
dependency analysis to reuse parser output.

### One parser interface per language

Language-specific parser interfaces would expose more native syntax details,
but they would make parser management and repository-wide parsing inconsistent.

### Tree-sitter-only contract

A Tree-sitter-only contract would match the first real parser backend, but it
would make future native parsers or external parser services harder to add.

## Consequences

The parser interface lets rig add parser backends without changing downstream
pipeline orchestration. Tree-sitter Go parsing can coexist with stubs and future
parsers behind the same registry and manager.

The tradeoff is an extra conversion step from syntax tree to IR. That boundary
is intentional: syntax trees preserve parser detail, while IR preserves the
cross-language contract that graph builders and semantic stages consume.

Incremental parsing is not implemented yet. The parser interface leaves room
for future incremental behavior through parse configuration, stable file
identity, syntax tree reuse, and repository snapshot metadata.
