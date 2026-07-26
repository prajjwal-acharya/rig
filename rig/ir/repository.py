from __future__ import annotations

import threading
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from rig.ir.builder import IRBuilderRegistry
from rig.ir.diagnostics import IRDiagnostic, IRDiagnosticSeverity
from rig.ir.identifiers import package_id
from rig.ir.identifiers import repository_id as compute_repository_id
from rig.ir.model import DeclarationKind, File, Package
from rig.parsers.pipeline import ParsedFile


@dataclass(frozen=True, kw_only=True)
class RepositoryIR:
    id: str
    root: Path
    files: tuple[File, ...] = ()
    packages: tuple[Package, ...] = ()
    diagnostics: tuple[IRDiagnostic, ...] = ()


class RepositoryIRBuilder:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.repository_id = compute_repository_id(root)
        self._lock = threading.Lock()
        self._files: list[File] = []
        self._diagnostics: list[IRDiagnostic] = []

    def add_file(self, file: File, diagnostics: Sequence[IRDiagnostic] = ()) -> None:
        with self._lock:
            self._files.append(file)
            self._diagnostics.extend(diagnostics)

    def build(self) -> RepositoryIR:
        with self._lock:
            files = tuple(sorted(self._files, key=lambda f: f.relative_path.as_posix()))
            diagnostics = list(self._diagnostics)

        packages = self._build_packages(files)
        diagnostics.extend(self._duplicate_declaration_diagnostics(packages, files))

        return RepositoryIR(
            id=self.repository_id,
            root=self.root,
            files=files,
            packages=packages,
            diagnostics=tuple(diagnostics),
        )

    def _build_packages(self, files: tuple[File, ...]) -> tuple[Package, ...]:
        file_ids_by_package: dict[str, list[str]] = {}
        for file in files:
            if file.package_name is None:
                continue
            file_ids_by_package.setdefault(file.package_name, []).append(file.id)

        return tuple(
            Package(
                id=package_id(self.repository_id, name),
                name=name,
                file_ids=tuple(sorted(file_ids_by_package[name])),
            )
            for name in sorted(file_ids_by_package)
        )

    @staticmethod
    def _duplicate_declaration_diagnostics(
        packages: tuple[Package, ...], files: tuple[File, ...]
    ) -> list[IRDiagnostic]:
        files_by_id = {file.id: file for file in files}
        diagnostics: list[IRDiagnostic] = []

        for package in packages:
            seen: Counter[tuple[str, str]] = Counter()
            for file_id_ in package.file_ids:
                for declaration in files_by_id[file_id_].declarations:
                    # Imports legitimately repeat the same name across many
                    # files in a package - only structural declarations are
                    # meaningful duplicates here.
                    if declaration.kind == DeclarationKind.IMPORT:
                        continue

                    key = (declaration.kind.value, declaration.name)
                    seen[key] += 1
                    if seen[key] > 1:
                        diagnostics.append(
                            IRDiagnostic(
                                message=(
                                    f"duplicate {declaration.kind.value} declaration "
                                    f"{declaration.name!r} in package {package.name!r}"
                                ),
                                severity=IRDiagnosticSeverity.WARNING,
                                location=declaration.location,
                            )
                        )

        return diagnostics


def build_repository_ir(
    root: Path,
    parsed_files: Sequence[ParsedFile],
    builder_registry: IRBuilderRegistry,
) -> RepositoryIR:
    repository_builder = RepositoryIRBuilder(root)

    for parsed_file in parsed_files:
        if not parsed_file.result.success or parsed_file.result.syntax_tree is None:
            continue

        builder = builder_registry.lookup(parsed_file.language.id)
        if builder is None:
            continue

        result = builder.build_file(
            repository_builder.repository_id,
            parsed_file.file.relative_path,
            parsed_file.result.syntax_tree,
        )
        repository_builder.add_file(result.file, result.diagnostics)

    return repository_builder.build()
