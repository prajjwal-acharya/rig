from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from rig.cli.commands import (
    run_analyze,
    run_detect,
    run_graph,
    run_ir,
    run_parse,
    run_references,
    run_scan,
    run_stats,
    run_symbols,
    run_types,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rig", description="Repository Intelligence Graph CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser("scan", help="Scan a repository")
    scan_parser.add_argument("path", nargs="?", default=".", help="Path to the repository")
    scan_parser.add_argument("--verbose", "-v", action="store_true", help="Show per-file metadata")

    detect_parser = subparsers.add_parser("detect", help="Scan and detect languages")
    detect_parser.add_argument("path", nargs="?", default=".", help="Path to the repository")

    parse_parser = subparsers.add_parser("parse", help="Scan, detect, and parse")
    parse_parser.add_argument("path", nargs="?", default=".", help="Path to the repository")

    ir_parser = subparsers.add_parser("ir", help="Build the Repository IR")
    ir_parser.add_argument("path", nargs="?", default=".", help="Path to the repository")

    symbols_parser = subparsers.add_parser("symbols", help="Build the Symbol Table")
    symbols_parser.add_argument("path", nargs="?", default=".", help="Path to the repository")
    symbols_parser.add_argument("--verbose", "-v", action="store_true", help="Print every symbol")

    references_parser = subparsers.add_parser("references", help="Resolve References")
    references_parser.add_argument("path", nargs="?", default=".", help="Path to the repository")
    references_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Print every reference"
    )

    types_parser = subparsers.add_parser("types", help="Build the Type Index")
    types_parser.add_argument("path", nargs="?", default=".", help="Path to the repository")
    types_parser.add_argument("--verbose", "-v", action="store_true", help="Print every type")

    graph_parser = subparsers.add_parser("graph", help="Build the Knowledge Graph")
    graph_parser.add_argument("path", nargs="?", default=".", help="Path to the repository")
    graph_parser.add_argument("--verbose", "-v", action="store_true", help="Print graph contents")

    analyze_parser = subparsers.add_parser("analyze", help="Run the complete compiler")
    analyze_parser.add_argument("path", nargs="?", default=".", help="Path to the repository")

    stats_parser = subparsers.add_parser("stats", help="Print repository-wide statistics")
    stats_parser.add_argument("path", nargs="?", default=".", help="Path to the repository")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "scan":
        return run_scan(args.path, verbose=args.verbose)
    if args.command == "detect":
        return run_detect(args.path)
    if args.command == "parse":
        return run_parse(args.path)
    if args.command == "ir":
        return run_ir(args.path)
    if args.command == "symbols":
        return run_symbols(args.path, verbose=args.verbose)
    if args.command == "references":
        return run_references(args.path, verbose=args.verbose)
    if args.command == "types":
        return run_types(args.path, verbose=args.verbose)
    if args.command == "graph":
        return run_graph(args.path, verbose=args.verbose)
    if args.command == "analyze":
        return run_analyze(args.path)
    if args.command == "stats":
        return run_stats(args.path)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
