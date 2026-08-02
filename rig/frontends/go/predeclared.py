from __future__ import annotations

# Go's predeclared identifiers and builtin type names. These are language
# knowledge, owned here by the Go frontend rather than by any semantic or
# analysis package: the frontend filters them out while extracting semantic
# facts, so downstream (language-neutral) layers never need to know them.

# Predeclared identifiers (builtin functions, types, and constants). A use of
# any of these is never a repository declaration, so the frontend drops it
# instead of emitting a reference the resolver would only fail to resolve.
GO_PREDECLARED_IDENTIFIERS = frozenset(
    {
        "any",
        "bool",
        "byte",
        "complex64",
        "complex128",
        "error",
        "float32",
        "float64",
        "int",
        "int8",
        "int16",
        "int32",
        "int64",
        "rune",
        "string",
        "uint",
        "uint8",
        "uint16",
        "uint32",
        "uint64",
        "uintptr",
        "true",
        "false",
        "iota",
        "nil",
        "append",
        "cap",
        "close",
        "complex",
        "copy",
        "delete",
        "imag",
        "len",
        "make",
        "new",
        "panic",
        "print",
        "println",
        "real",
        "recover",
        "min",
        "max",
        "clear",
    }
)

# Predeclared type names - never repository type declarations, so a field/
# parameter/return/alias reference to one yields no type relationship (and no
# diagnostic). Filtered out here so the type-relationship analysis need not
# know Go's builtin types.
GO_BUILTIN_TYPES = frozenset(
    {
        "any",
        "bool",
        "byte",
        "complex64",
        "complex128",
        "error",
        "float32",
        "float64",
        "int",
        "int8",
        "int16",
        "int32",
        "int64",
        "rune",
        "string",
        "uint",
        "uint8",
        "uint16",
        "uint32",
        "uint64",
        "uintptr",
    }
)
