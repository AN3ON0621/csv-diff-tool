from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .core import compare_csv_files
from .formatting import format_json, format_markdown, format_summary, format_html


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="csv_diff",
        description="Strict, cell-level CSV comparison",
    )
    p.add_argument("old", help="Path to the old CSV file")
    p.add_argument("new", help="Path to the new CSV file")
    p.add_argument(
        "--key",
        help="Comma-separated column names to use as primary key (unordered)",
    )
    p.add_argument(
        "--ordered",
        action="store_true",
        help="Compare rows by index order (ignores --key)",
    )
    p.add_argument(
        "--format",
        choices=["markdown", "json", "summary", "html"],
        default="markdown",
        help="Output format",
    )
    p.add_argument("--output", default="-", help="Output file path or '-' for stdout")
    p.add_argument(
        "--include-raw-diff",
        action="store_true",
        help="Append a unified raw text diff of file contents",
    )
    p.add_argument("--encoding1", help="Encoding for first file (default: auto)")
    p.add_argument("--encoding2", help="Encoding for second file (default: auto)")
    p.add_argument("--delimiter", help="CSV delimiter (default: auto)")
    p.add_argument(
        "--max-print-rows",
        type=int,
        default=1000,
        help="Limit number of rows printed per section (markdown)",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    ns = parse_args(argv or sys.argv[1:])
    keys = tuple(k.strip() for k in ns.key.split(",")) if ns.key else None

    try:
        diff = compare_csv_files(
            Path(ns.old),
            Path(ns.new),
            keys=keys,
            ordered=ns.ordered,
            include_raw_diff=ns.include_raw_diff,
            encoding1=ns.encoding1,
            encoding2=ns.encoding2,
            delimiter=ns.delimiter,
        )
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    include_raw = bool(ns.include_raw_diff)
    if ns.format == "json":
        out = format_json(diff, include_raw=include_raw)
    elif ns.format == "summary":
        out = format_summary(diff)
    elif ns.format == "html":
        out = format_html(diff, include_raw=include_raw, max_rows=ns.max_print_rows)
    else:
        out = format_markdown(diff, max_rows=ns.max_print_rows, include_raw=include_raw)

    if ns.output == "-":
        print(out)
    else:
        Path(ns.output).write_text(out, encoding="utf-8")

    return 1 if (diff.added or diff.removed or diff.modified) else 0


if __name__ == "__main__":
    raise SystemExit(main())