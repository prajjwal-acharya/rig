from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from rig.graph.builder import GraphAccumulator, GraphBuilder
from rig.graph.identifiers import edge_id
from rig.graph.model import Edge, Graph, GraphMetadata, Node, RelationshipType
from rig.graph.properties import Properties
from rig.graph.registry import GraphBuilderRegistry
from rig.ir.model import (
    Declaration,
    File,
    FunctionDeclaration,
    ImportDeclaration,
    Package,
    TypeDeclaration,
    VariableDeclaration,
)
from rig.ir.repository import RepositoryIR

STRUCTURAL_GRAPH_VERSION = "1.0.0"
BUILDER_ID = "structural"


def _location_properties(declaration: Declaration) -> dict[str, Any]:
    location = declaration.location
    properties: dict[str, Any] = {
        "location_file": location.relative_path.as_posix(),
        "location_start_line": location.start_line,
        "location_start_column": location.start_column,
        "location_end_line": location.end_line,
        "location_end_column": location.end_column,
    }
    if location.start_byte is not None:
        properties["location_start_byte"] = location.start_byte
    if location.end_byte is not None:
        properties["location_end_byte"] = location.end_byte
    return properties


def _declaration_node_type(declaration: Declaration) -> str:
    if isinstance(declaration, FunctionDeclaration):
        return "Function"
    if isinstance(declaration, TypeDeclaration):
        return "Type"
    if isinstance(declaration, VariableDeclaration):
        return "Constant" if declaration.is_constant else "Variable"
    raise TypeError(f"unsupported declaration type: {type(declaration).__name__}")


def _structural_declarations(file: File) -> list[Declaration]:
    # Imports are excluded from the structural graph entirely, so counts
    # must exclude them too - otherwise a File/Package's declaration_count
    # property would disagree with the DECLARES edges actually present.
    return [d for d in file.declarations if not isinstance(d, ImportDeclaration)]


def _declaration_properties(declaration: Declaration) -> Properties:
    values: dict[str, Any] = {"name": declaration.name, **_location_properties(declaration)}

    if isinstance(declaration, FunctionDeclaration):
        values["parameter_count"] = declaration.parameter_count
        values["is_exported"] = declaration.is_exported
    elif isinstance(declaration, TypeDeclaration):
        values["underlying_kind"] = declaration.underlying_kind
        values["is_exported"] = declaration.is_exported
    elif isinstance(declaration, VariableDeclaration):
        values["is_exported"] = declaration.is_exported

    return Properties.from_mapping(values)


class StructuralGraphBuilder(GraphBuilder):
    """Converts a RepositoryIR into a purely hierarchical (CONTAINS/DECLARES)
    graph. Consumes only `rig.ir` types - no Tree-sitter or parser internals.
    """

    def __init__(self, *, now: Callable[[], datetime] | None = None) -> None:
        self._now = now or (lambda: datetime.now(timezone.utc))

    @property
    def builder_id(self) -> str:
        return BUILDER_ID

    def build(self, repository: RepositoryIR) -> Graph:
        language_ids = tuple(sorted({file.language_id for file in repository.files}))
        total_declarations = sum(len(_structural_declarations(file)) for file in repository.files)

        metadata = GraphMetadata(
            repository_id=repository.id,
            language_ids=language_ids,
            generator=BUILDER_ID,
            generator_version=STRUCTURAL_GRAPH_VERSION,
            created_at=self._now(),
            statistics=Properties.of(
                package_count=len(repository.packages),
                file_count=len(repository.files),
                declaration_count=total_declarations,
            ),
        )
        accumulator = GraphAccumulator(metadata=metadata)

        accumulator.add_node(
            Node(
                id=repository.id,
                type="Repository",
                properties=Properties.of(
                    name=repository.root.name,
                    root_path=str(repository.root),
                    languages=language_ids,
                    graph_version=STRUCTURAL_GRAPH_VERSION,
                ),
            )
        )

        files_by_id = {file.id: file for file in repository.files}
        packaged_file_ids: set[str] = set()

        for package in repository.packages:
            self._add_package(accumulator, repository.id, package, files_by_id)
            packaged_file_ids.update(package.file_ids)

        for file in repository.files:
            if file.id in packaged_file_ids:
                continue
            # A file with no resolvable package is still part of the
            # repository - attach it directly rather than dropping it.
            self._add_file(accumulator, source_node_id=repository.id, file=file)

        return accumulator.build()

    @staticmethod
    def _add_package(
        accumulator: GraphAccumulator,
        repository_id: str,
        package: Package,
        files_by_id: dict[str, File],
    ) -> None:
        member_files = [files_by_id[file_id] for file_id in package.file_ids]
        declaration_count = sum(len(_structural_declarations(file)) for file in member_files)

        accumulator.add_node(
            Node(
                id=package.id,
                type="Package",
                properties=Properties.of(
                    name=package.name,
                    language=member_files[0].language_id,
                    declaration_count=declaration_count,
                ),
            )
        )
        accumulator.add_edge(
            Edge(
                id=edge_id(repository_id, package.id, RelationshipType.CONTAINS.value),
                source=repository_id,
                target=package.id,
                relationship=RelationshipType.CONTAINS,
            )
        )

        for file in member_files:
            StructuralGraphBuilder._add_file(accumulator, source_node_id=package.id, file=file)

    @staticmethod
    def _add_file(accumulator: GraphAccumulator, *, source_node_id: str, file: File) -> None:
        declarations = _structural_declarations(file)

        accumulator.add_node(
            Node(
                id=file.id,
                type="File",
                properties=Properties.of(
                    relative_path=file.relative_path.as_posix(),
                    language=file.language_id,
                    declaration_count=len(declarations),
                ),
            )
        )
        accumulator.add_edge(
            Edge(
                id=edge_id(source_node_id, file.id, RelationshipType.CONTAINS.value),
                source=source_node_id,
                target=file.id,
                relationship=RelationshipType.CONTAINS,
            )
        )

        for declaration in declarations:
            StructuralGraphBuilder._add_declaration(
                accumulator, file_id=file.id, declaration=declaration
            )

    @staticmethod
    def _add_declaration(
        accumulator: GraphAccumulator, *, file_id: str, declaration: Declaration
    ) -> None:
        accumulator.add_node(
            Node(
                id=declaration.id,
                type=_declaration_node_type(declaration),
                properties=_declaration_properties(declaration),
            )
        )
        accumulator.add_edge(
            Edge(
                id=edge_id(file_id, declaration.id, RelationshipType.DECLARES.value),
                source=file_id,
                target=declaration.id,
                relationship=RelationshipType.DECLARES,
            )
        )


def build_default_registry() -> GraphBuilderRegistry:
    return GraphBuilderRegistry([StructuralGraphBuilder()])
