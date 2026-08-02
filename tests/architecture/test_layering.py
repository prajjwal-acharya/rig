"""Architecture tests that enforce RIG's compiler-pipeline layering.

These are guardrails, not behavior tests: they parse the import graph of the
`rig` package and assert the structural rules the Stage 2.0 refactor restored,
so a future change that quietly reintroduces a boundary violation fails here
instead of silently rotting the architecture.

The central invariant: **Tree-sitter is an implementation detail of parsing.**
Only the parser package and the language frontends may depend on it; every
semantic, analysis, graph, and CLI package must consume the language-neutral
IR instead.
"""

from __future__ import annotations

import ast
from pathlib import Path

import rig

RIG_ROOT = Path(rig.__file__).resolve().parent

# Packages that own / are allowed to touch Tree-sitter: the parser package
# (which wraps the backend) and the language frontends (which turn a syntax
# tree into neutral IR). Everything else must be Tree-sitter-free.
TREE_SITTER_OWNERS = ("rig.parsers", "rig.frontends")

# Packages that must never depend on a concrete parser backend. These are the
# neutral IR boundary and everything downstream of it.
TREE_SITTER_FORBIDDEN_PACKAGES = (
    "rig.ir",
    "rig.symbols",
    "rig.references",
    "rig.types",
    "rig.graph",
    "rig.analysis",
    "rig.cli",
    "rig.languages",
    "rig.scanner",
    "rig.plugins",
)


def _module_name(path: Path) -> str:
    relative = path.relative_to(RIG_ROOT.parent).with_suffix("")
    parts = list(relative.parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _imported_modules(path: Path) -> set[str]:
    """Every module string imported by a file (both `import x` and
    `from x import y`, the latter recorded as `x`)."""

    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module is not None:
            imported.add(node.module)
    return imported


def _iter_python_files() -> list[Path]:
    return sorted(p for p in RIG_ROOT.rglob("*.py") if "__pycache__" not in p.parts)


def _touches_tree_sitter(module: str) -> bool:
    return (
        module == "tree_sitter"
        or module.startswith("tree_sitter.")
        or (module == "rig.parsers.treesitter" or module.startswith("rig.parsers.treesitter."))
    )


def _in_package(module: str, package: str) -> bool:
    return module == package or module.startswith(package + ".")


def test_semantic_and_downstream_packages_do_not_import_tree_sitter() -> None:
    """No neutral / semantic / analysis / CLI module may name Tree-sitter.

    This is the concrete form of "the IR is the canonical semantic boundary":
    once a file is past the parser, it works with neutral IR, never syntax.
    """

    violations: list[str] = []
    for path in _iter_python_files():
        module = _module_name(path)
        if not any(_in_package(module, pkg) for pkg in TREE_SITTER_FORBIDDEN_PACKAGES):
            continue
        for imported in _imported_modules(path):
            if _touches_tree_sitter(imported):
                violations.append(f"{module} imports {imported}")

    assert not violations, "Tree-sitter leaked past the parser boundary:\n" + "\n".join(
        sorted(violations)
    )


def test_tree_sitter_is_confined_to_parser_and_frontend_packages() -> None:
    """Every Tree-sitter import in the whole codebase lives in an owner
    package. This proves the boundary has an owner (the test above could pass
    vacuously if Tree-sitter were simply unused)."""

    owners_using_tree_sitter: set[str] = set()
    stray: list[str] = []
    for path in _iter_python_files():
        module = _module_name(path)
        if not any(_touches_tree_sitter(imported) for imported in _imported_modules(path)):
            continue
        if any(_in_package(module, owner) for owner in TREE_SITTER_OWNERS):
            owners_using_tree_sitter.add(module)
        else:
            stray.append(module)

    assert not stray, "Tree-sitter imported outside owner packages:\n" + "\n".join(sorted(stray))
    assert owners_using_tree_sitter, "expected the parser/frontend packages to own Tree-sitter"


def test_neutral_ir_package_has_no_language_specific_builder() -> None:
    """The neutral IR package holds only models / identifiers / interfaces /
    registry / diagnostics / visitor - never a concrete language builder. The
    Go builder lives in the Go frontend."""

    ir_dir = RIG_ROOT / "ir"
    assert not (ir_dir / "builders").exists(), (
        "rig/ir/builders/ reintroduces language-specific implementations into the neutral IR"
    )
    for path in ir_dir.rglob("*.py"):
        for imported in _imported_modules(path):
            assert not _in_package(imported, "rig.frontends"), (
                f"neutral IR module {_module_name(path)} imports a language frontend "
                f"({imported}); the dependency must point frontend -> IR, never the reverse"
            )


def test_analysis_package_consumes_ir_not_parser() -> None:
    """Analyses depend on the IR (and semantic indexes), never on the parser
    package - they consume neutral facts, not parse results."""

    analysis_dir = RIG_ROOT / "analysis"
    violations: list[str] = []
    for path in analysis_dir.rglob("*.py"):
        module = _module_name(path)
        for imported in _imported_modules(path):
            if _in_package(imported, "rig.parsers"):
                violations.append(f"{module} imports {imported}")
    assert not violations, "analysis reached into the parser layer:\n" + "\n".join(
        sorted(violations)
    )


def test_references_package_does_not_import_parser_layer() -> None:
    """Reference resolution consumes IR reference-use facts, not parse
    results."""

    references_dir = RIG_ROOT / "references"
    violations: list[str] = []
    for path in references_dir.rglob("*.py"):
        module = _module_name(path)
        for imported in _imported_modules(path):
            if _in_package(imported, "rig.parsers"):
                violations.append(f"{module} imports {imported}")
    assert not violations, "references reached into the parser layer:\n" + "\n".join(
        sorted(violations)
    )
