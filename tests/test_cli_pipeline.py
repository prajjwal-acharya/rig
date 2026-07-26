from __future__ import annotations

from pathlib import Path

import pytest

from rig.cli import main


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def _write_go_repo(root: Path) -> None:
    _write(
        root / "api" / "handler.go",
        (
            'package api\n\nimport "myrepo/service"\n\n'
            "type Handler struct {\n\tSvc service.Service\n}\n\n"
            "func (h Handler) Run() {\n\tservice.Start()\n}\n"
        ),
    )
    _write(
        root / "service" / "service.go",
        (
            "package service\n\ntype Service struct{}\n\n"
            "func Start() {\n\thelper()\n}\n\nfunc helper() {}\n"
        ),
    )


# --- detect ------------------------------------------------------------------


def test_detect_reports_repository_and_language_percentages(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_go_repo(tmp_path)

    exit_code = main(["detect", str(tmp_path)])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Repository" in output
    assert "Files: 2" in output
    assert "Go" in output
    assert "100.0%" in output
    assert "Detect completed in" in output


def test_detect_invalid_path_reports_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    missing = tmp_path / "does-not-exist"

    exit_code = main(["detect", str(missing)])
    output = capsys.readouterr()

    assert exit_code == 1
    assert "error:" in output.err


def test_detect_empty_repository(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["detect", str(tmp_path)])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Files: 0" in output
    assert "(None)" in output


# --- parse ---------------------------------------------------------------


def test_parse_reports_files_parsed_and_no_errors(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_go_repo(tmp_path)

    exit_code = main(["parse", str(tmp_path)])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Files parsed: 2" in output
    assert "Syntax errors: 0" in output
    assert "tree-sitter-go" in output
    assert "Parse completed in" in output


def test_parse_reports_syntax_errors(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write(tmp_path / "broken.go", "package p\n\nfunc Foo( {\n")

    exit_code = main(["parse", str(tmp_path)])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Files parsed: 1" in output
    assert "Syntax errors: 1" in output


def test_parse_invalid_path_reports_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    missing = tmp_path / "does-not-exist"

    exit_code = main(["parse", str(missing)])
    output = capsys.readouterr()

    assert exit_code == 1
    assert "error:" in output.err


def test_parse_empty_repository(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["parse", str(tmp_path)])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Files parsed: 0" in output


# --- ir ------------------------------------------------------------------


def test_ir_reports_packages_files_and_declarations(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_go_repo(tmp_path)

    exit_code = main(["ir", str(tmp_path)])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Packages: 2" in output
    assert "Files: 2" in output
    assert "Functions" in output
    assert "Types" in output
    assert "Imports" in output
    assert "IR build completed in" in output


def test_ir_invalid_path_reports_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    missing = tmp_path / "does-not-exist"

    exit_code = main(["ir", str(missing)])
    output = capsys.readouterr()

    assert exit_code == 1
    assert "error:" in output.err


def test_ir_empty_repository(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["ir", str(tmp_path)])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Packages: 0" in output
    assert "Files: 0" in output


# --- symbols ---------------------------------------------------------------


def test_symbols_reports_counts(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write_go_repo(tmp_path)

    exit_code = main(["symbols", str(tmp_path)])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Total: 6" in output
    assert "function" in output
    assert "package" in output
    assert "type" in output
    assert "Symbol build completed in" in output
    assert "Every Symbol" not in output


def test_symbols_verbose_prints_every_symbol(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_go_repo(tmp_path)

    exit_code = main(["symbols", str(tmp_path), "--verbose"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Every Symbol" in output
    assert "Handler" in output
    assert "Service" in output
    assert "Start" in output
    assert "helper" in output


def test_symbols_invalid_path_reports_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    missing = tmp_path / "does-not-exist"

    exit_code = main(["symbols", str(missing)])
    output = capsys.readouterr()

    assert exit_code == 1
    assert "error:" in output.err


# --- references --------------------------------------------------------------


def test_references_reports_resolution_rate(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_go_repo(tmp_path)

    exit_code = main(["references", str(tmp_path)])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Total: 4" in output
    assert "Resolved: 3" in output
    assert "Unresolved: 1" in output
    assert "Resolution rate: 75.0%" in output
    assert "Reference resolution completed in" in output


def test_references_verbose_prints_every_reference(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_go_repo(tmp_path)

    exit_code = main(["references", str(tmp_path), "--verbose"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Every Reference" in output
    assert "[resolved]" in output
    assert "[unresolved]" in output


def test_references_invalid_path_reports_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    missing = tmp_path / "does-not-exist"

    exit_code = main(["references", str(missing)])
    output = capsys.readouterr()

    assert exit_code == 1
    assert "error:" in output.err


# --- types -------------------------------------------------------------------


def test_types_reports_kind_counts(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write_go_repo(tmp_path)

    exit_code = main(["types", str(tmp_path)])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Structs" in output
    assert "Interfaces" in output
    assert "Aliases" in output
    assert "Named" in output
    assert "Total" in output
    assert "Type build completed in" in output


def test_types_verbose_prints_every_type(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_go_repo(tmp_path)

    exit_code = main(["types", str(tmp_path), "--verbose"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Every Type" in output
    assert "Handler" in output
    assert "Service" in output
    assert "package=api" in output
    assert "package=service" in output


def test_types_invalid_path_reports_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    missing = tmp_path / "does-not-exist"

    exit_code = main(["types", str(missing)])
    output = capsys.readouterr()

    assert exit_code == 1
    assert "error:" in output.err


# --- graph -------------------------------------------------------------------


def test_graph_reports_nodes_edges_and_relationships(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_go_repo(tmp_path)

    exit_code = main(["graph", str(tmp_path)])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Nodes: 10" in output
    assert "Edges: 16" in output
    assert "CALLS" in output
    assert "CONTAINS" in output
    assert "DECLARES" in output
    assert "IMPORTS" in output
    assert "REFERENCES" in output
    assert "DEPENDS_ON" in output
    assert "Graph build completed in" in output


def test_graph_verbose_prints_nodes_and_edges(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_go_repo(tmp_path)

    exit_code = main(["graph", str(tmp_path), "--verbose"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Nodes" in output
    assert "Edges" in output
    assert "-->" in output


def test_graph_invalid_path_reports_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    missing = tmp_path / "does-not-exist"

    exit_code = main(["graph", str(missing)])
    output = capsys.readouterr()

    assert exit_code == 1
    assert "error:" in output.err


def test_graph_empty_repository_still_has_repository_node(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(["graph", str(tmp_path)])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Nodes: 1" in output
    assert "Edges: 0" in output


# --- analyze -------------------------------------------------------------------


def test_analyze_reports_full_execution_summary(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_go_repo(tmp_path)

    exit_code = main(["analyze", str(tmp_path)])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Repository" in output
    assert f"Name: {tmp_path.name}" in output
    assert "Languages" in output
    assert "IR" in output
    assert "Knowledge Graph" in output
    assert "Analysis" in output
    assert "Call Graph" in output
    assert "Type Relationships" in output
    assert "Dependency Analysis" in output
    assert "✓" in output
    assert "Completed in:" in output
    assert "Done." in output


def test_analyze_invalid_path_reports_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    missing = tmp_path / "does-not-exist"

    exit_code = main(["analyze", str(missing)])
    output = capsys.readouterr()

    assert exit_code == 1
    assert "error:" in output.err


def test_analyze_empty_repository(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["analyze", str(tmp_path)])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Files: 0" in output
    assert "✓" in output


def test_analyze_repository_with_syntax_errors_still_completes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write(tmp_path / "broken.go", "package p\n\nfunc Foo( {\n")

    exit_code = main(["analyze", str(tmp_path)])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Completed in:" in output


# --- stats -------------------------------------------------------------------


def test_stats_reports_human_readable_summary(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_go_repo(tmp_path)

    exit_code = main(["stats", str(tmp_path)])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Repository Statistics" in output
    assert "Packages" in output
    assert "Declarations" in output
    assert "Functions" in output
    assert "Symbols" in output
    assert "References" in output
    assert "Structs" in output
    assert "Interfaces" in output
    assert "Call graph edges" in output
    assert "Dependencies" in output


def test_stats_invalid_path_reports_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    missing = tmp_path / "does-not-exist"

    exit_code = main(["stats", str(missing)])
    output = capsys.readouterr()

    assert exit_code == 1
    assert "error:" in output.err


def test_stats_empty_repository(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["stats", str(tmp_path)])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Packages" in output


# --- determinism -------------------------------------------------------------


@pytest.mark.parametrize(
    "command",
    ["detect", "parse", "ir", "symbols", "references", "types", "graph", "analyze", "stats"],
)
def test_output_is_deterministic_across_repeated_runs(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], command: str
) -> None:
    _write_go_repo(tmp_path)

    main([command, str(tmp_path)])
    first = capsys.readouterr().out
    main([command, str(tmp_path)])
    second = capsys.readouterr().out

    # Timing lines vary run to run - strip them before comparing.
    def _strip_timing(text: str) -> str:
        return "\n".join(
            line
            for line in text.splitlines()
            if "completed in" not in line.lower() and "Completed in:" not in line
        )

    assert _strip_timing(first) == _strip_timing(second)


# --- exit codes ----------------------------------------------------------------


@pytest.mark.parametrize(
    "command",
    ["detect", "parse", "ir", "symbols", "references", "types", "graph", "analyze", "stats"],
)
def test_every_command_succeeds_on_a_valid_repository(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], command: str
) -> None:
    _write_go_repo(tmp_path)

    exit_code = main([command, str(tmp_path)])

    assert exit_code == 0


@pytest.mark.parametrize(
    "command",
    ["detect", "parse", "ir", "symbols", "references", "types", "graph", "analyze", "stats"],
)
def test_every_command_fails_on_an_invalid_path(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], command: str
) -> None:
    missing = tmp_path / "does-not-exist"

    exit_code = main([command, str(missing)])

    assert exit_code == 1


def test_invalid_cli_arguments_exit_nonzero(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["not-a-real-command"])

    assert exc_info.value.code != 0


def test_no_command_prints_help_and_exits_nonzero() -> None:
    with pytest.raises(SystemExit) as exc_info:
        main([])

    assert exc_info.value.code != 0
