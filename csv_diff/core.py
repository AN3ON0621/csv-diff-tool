from __future__ import annotations

import csv
import dataclasses
import difflib
import io
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


@dataclasses.dataclass(frozen=True)
class CellChange:
    column: str
    old: str | None
    new: str | None


@dataclasses.dataclass(frozen=True)
class RowChange:
    kind: str  # "added" | "removed" | "modified"
    key: Tuple[str, ...] | Tuple[int, ...]
    changes: Tuple[CellChange, ...] | tuple()
    row_old: Optional[Dict[str, str]]
    row_new: Optional[Dict[str, str]]


@dataclasses.dataclass(frozen=True)
class DiffResult:
    added: Tuple[RowChange, ...]
    removed: Tuple[RowChange, ...]
    modified: Tuple[RowChange, ...]
    raw_diff: Optional[str] = None


def _read_csv(
    path: Path,
    *,
    encoding: Optional[str] = None,
    delimiter: Optional[str] = None,
) -> Tuple[List[str], List[Dict[str, str]]]:
    text = path.read_bytes()
    if encoding is None:
        # Try utf-8 first, then fall back to latin1 to avoid decode errors
        try:
            s = text.decode("utf-8")
        except UnicodeDecodeError:
            s = text.decode("latin1")
    else:
        s = text.decode(encoding)

    buf = io.StringIO(s)
    if delimiter is None:
        try:
            dialect = csv.Sniffer().sniff(s[:5000])
            dialect.skipinitialspace = False
            reader = csv.DictReader(buf, dialect=dialect)
        except Exception:
            reader = csv.DictReader(buf)
    else:
        reader = csv.DictReader(buf, delimiter=delimiter)

    headers = reader.fieldnames or []
    rows: List[Dict[str, str]] = []
    for row in reader:
        # Preserve exact strings; None for missing columns becomes '' to be consistent
        normalized = {h: (row.get(h) if row.get(h) is not None else "") for h in headers}
        rows.append(normalized)
    return headers, rows


def _make_key(row: Dict[str, str], keys: Sequence[str]) -> Tuple[str, ...]:
    return tuple(row.get(k, "") for k in keys)


def _compare_unordered(
    headers1: List[str],
    rows1: List[Dict[str, str]],
    headers2: List[str],
    rows2: List[Dict[str, str]],
    *,
    keys: Sequence[str],
) -> Tuple[List[RowChange], List[RowChange], List[RowChange]]:
    # Build maps from key -> row
    map1: Dict[Tuple[str, ...], Dict[str, str]] = {_make_key(r, keys): r for r in rows1}
    map2: Dict[Tuple[str, ...], Dict[str, str]] = {_make_key(r, keys): r for r in rows2}

    added: List[RowChange] = []
    removed: List[RowChange] = []
    modified: List[RowChange] = []

    all_columns = list(dict.fromkeys([*headers1, *headers2]))

    for k in map1.keys() - map2.keys():
        removed.append(
            RowChange(kind="removed", key=k, changes=tuple(), row_old=map1[k], row_new=None)
        )
    for k in map2.keys() - map1.keys():
        added.append(
            RowChange(kind="added", key=k, changes=tuple(), row_old=None, row_new=map2[k])
        )
    for k in map1.keys() & map2.keys():
        r1 = map1[k]
        r2 = map2[k]
        changes: List[CellChange] = []
        for col in all_columns:
            v1 = r1.get(col, "")
            v2 = r2.get(col, "")
            if v1 != v2:
                changes.append(CellChange(column=col, old=v1, new=v2))
        if changes:
            modified.append(
                RowChange(kind="modified", key=k, changes=tuple(changes), row_old=r1, row_new=r2)
            )

    return added, removed, modified


def _compare_ordered(
    headers1: List[str],
    rows1: List[Dict[str, str]],
    headers2: List[str],
    rows2: List[Dict[str, str]],
) -> Tuple[List[RowChange], List[RowChange], List[RowChange]]:
    added: List[RowChange] = []
    removed: List[RowChange] = []
    modified: List[RowChange] = []

    all_columns = list(dict.fromkeys([*headers1, *headers2]))
    max_len = max(len(rows1), len(rows2))
    for idx in range(max_len):
        if idx >= len(rows1):
            added.append(
                RowChange(kind="added", key=(idx,), changes=tuple(), row_old=None, row_new=rows2[idx])
            )
            continue
        if idx >= len(rows2):
            removed.append(
                RowChange(kind="removed", key=(idx,), changes=tuple(), row_old=rows1[idx], row_new=None)
            )
            continue
        r1 = rows1[idx]
        r2 = rows2[idx]
        changes: List[CellChange] = []
        for col in all_columns:
            v1 = r1.get(col, "")
            v2 = r2.get(col, "")
            if v1 != v2:
                changes.append(CellChange(column=col, old=v1, new=v2))
        if changes:
            modified.append(
                RowChange(kind="modified", key=(idx,), changes=tuple(changes), row_old=r1, row_new=r2)
            )

    return added, removed, modified


def _raw_text_diff(path1: Path, path2: Path, encoding1: Optional[str], encoding2: Optional[str]) -> str:
    s1 = path1.read_bytes().decode(encoding1 or "utf-8", errors="replace").splitlines(keepends=False)
    s2 = path2.read_bytes().decode(encoding2 or "utf-8", errors="replace").splitlines(keepends=False)
    return "\n".join(
        difflib.unified_diff(
            s1,
            s2,
            fromfile=str(path1),
            tofile=str(path2),
            lineterm="",
            n=3,
        )
    )


def compare_csv_files(
    path1: Path | str,
    path2: Path | str,
    *,
    keys: Optional[Sequence[str]] = None,
    ordered: bool = False,
    include_raw_diff: bool = False,
    encoding1: Optional[str] = None,
    encoding2: Optional[str] = None,
    delimiter: Optional[str] = None,
) -> DiffResult:
    p1 = Path(path1)
    p2 = Path(path2)
    headers1, rows1 = _read_csv(p1, encoding=encoding1, delimiter=delimiter)
    headers2, rows2 = _read_csv(p2, encoding=encoding2, delimiter=delimiter)

    if ordered:
        added, removed, modified = _compare_ordered(headers1, rows1, headers2, rows2)
    elif keys and len(keys) > 0:
        added, removed, modified = _compare_unordered(headers1, rows1, headers2, rows2, keys=keys)
    else:
        # multiset compare by entire row tuples (unordered, no stable keys)
        tuple_headers = list(dict.fromkeys([*headers1, *headers2]))
        def to_tuple(r: Dict[str, str]) -> Tuple[str, ...]:
            return tuple(r.get(h, "") for h in tuple_headers)

        from collections import Counter

        c1 = Counter(to_tuple(r) for r in rows1)
        c2 = Counter(to_tuple(r) for r in rows2)

        # Differences in counts mean additions/removals; no cell-level modifications without keys
        added = []
        removed = []
        modified = []
        for t, count in (c2 - c1).items():
            for _ in range(count):
                row_new = {h: v for h, v in zip(tuple_headers, t)}
                added.append(RowChange(kind="added", key=t, changes=tuple(), row_old=None, row_new=row_new))
        for t, count in (c1 - c2).items():
            for _ in range(count):
                row_old = {h: v for h, v in zip(tuple_headers, t)}
                removed.append(RowChange(kind="removed", key=t, changes=tuple(), row_old=row_old, row_new=None))

    raw = _raw_text_diff(p1, p2, encoding1, encoding2) if include_raw_diff else None
    return DiffResult(
        added=tuple(added),
        removed=tuple(removed),
        modified=tuple(modified),
        raw_diff=raw,
    )


