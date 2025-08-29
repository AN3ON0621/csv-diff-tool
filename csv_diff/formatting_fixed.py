from __future__ import annotations

import json
from typing import Iterable
import html as _html

from .core import CellChange, DiffResult, RowChange


def _format_row_change_markdown(change: RowChange, max_rows: int | None, index: int) -> str:
    if change.kind in ("added", "removed"):
        head = f"- {change.kind.upper()} key={change.key}"
        row = change.row_new if change.kind == "added" else change.row_old
        if not row:
            return head
        kv = ", ".join(f"{k}={json.dumps(v)}" for k, v in row.items())
        return f"{head}: {kv}"
    else:
        parts = [f"- MODIFIED key={change.key}"]
        for c in change.changes:
            parts.append(f"  - {c.column}: {json.dumps(c.old)} -> {json.dumps(c.new)}")
        return "\n".join(parts)


def format_markdown(diff: DiffResult, *, max_rows: int = 1000, include_raw: bool = False) -> str:
    lines: list[str] = []
    def section(title: str, changes: Iterable[RowChange]):
        lines.append(f"### {title}")
        count = 0
        for idx, ch in enumerate(changes):
            if count >= max_rows:
                lines.append(f"- ... and more ({title.lower()})")
                break
            lines.append(_format_row_change_markdown(ch, max_rows, idx))
            count += 1
        if count == 0:
            lines.append("- None")

    section("Added", diff.added)
    section("Removed", diff.removed)
    section("Modified", diff.modified)

    if include_raw and diff.raw_diff:
        lines.append("\n### Raw unified diff")
        lines.append("```diff")
        lines.append(diff.raw_diff)
        lines.append("```")

    return "\n".join(lines)


def format_json(diff: DiffResult, *, include_raw: bool = False) -> str:
    def serialize_row_change(ch: RowChange):
        return {
            "kind": ch.kind,
            "key": list(ch.key),
            "changes": [
                {"column": c.column, "old": c.old, "new": c.new} for c in ch.changes
            ],
            "row_old": ch.row_old,
            "row_new": ch.row_new,
        }

    obj = {
        "added": [serialize_row_change(c) for c in diff.added],
        "removed": [serialize_row_change(c) for c in diff.removed],
        "modified": [serialize_row_change(c) for c in diff.modified],
    }
    if include_raw and diff.raw_diff:
        obj["raw_diff"] = diff.raw_diff
    return json.dumps(obj, indent=2, ensure_ascii=False)


def format_summary(diff: DiffResult) -> str:
    return (
        f"added={len(diff.added)} removed={len(diff.removed)} modified={len(diff.modified)}"
    )


def _escape(value: str | None) -> str:
    return _html.escape(value if value is not None else "")


def _collect_columns(changes: Iterable[RowChange]) -> list[str]:
    columns: list[str] = []
    seen: set[str] = set()
    for ch in changes:
        # Prefer explicit changed columns for modified; else union of row keys
        if ch.kind == "modified":
            for c in ch.changes:
                if c.column not in seen:
                    columns.append(c.column)
                    seen.add(c.column)
        else:
            source = ch.row_new if ch.kind == "added" else ch.row_old
            if source:
                for col in source.keys():
                    if col not in seen:
                        columns.append(col)
                        seen.add(col)
    return columns


def format_html(diff: DiffResult, *, include_raw: bool = False, max_rows: int = 5000) -> str:
    css = """
    <style>
      :root {
        --primary-color: #2563eb;
        --success-color: #059669;
        --warning-color: #d97706;
        --danger-color: #dc2626;
        --gray-50: #f9fafb;
        --gray-100: #f3f4f6;
        --gray-200: #e5e7eb;
        --gray-300: #d1d5db;
        --gray-400: #9ca3af;
        --gray-500: #6b7280;
        --gray-600: #4b5563;
        --gray-700: #374151;
        --gray-800: #1f2937;
        --gray-900: #111827;
        --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
        --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
        --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
        --border-radius: 8px;
        --border-radius-lg: 12px;
      }
      
      * {
        box-sizing: border-box;
      }
      
      body { 
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; 
        margin: 0; 
        padding: 24px;
        background: linear-gradient(135deg, var(--gray-50) 0%, #ffffff 100%);
        color: var(--gray-800);
        line-height: 1.6;
        min-height: 100vh;
      }
      
      .container {
        max-width: 1400px;
        margin: 0 auto;
      }
      
      h1 { 
        font-size: 2.5rem;
        font-weight: 700;
        color: var(--gray-900);
        margin: 0 0 32px 0;
        text-align: center;
        background: linear-gradient(135deg, var(--primary-color), var(--success-color));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
      }
      
      h2 { 
        font-size: 1.5rem;
        font-weight: 600;
        margin: 32px 0 16px 0;
        color: var(--gray-800);
        display: flex;
        align-items: center;
        gap: 12px;
      }
      
      .summary-cards {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 20px;
        margin-bottom: 32px;
      }
      
      .summary-card {
        background: white;
        border-radius: var(--border-radius-lg);
        padding: 24px;
        box-shadow: var(--shadow-md);
        border: 1px solid var(--gray-200);
        text-align: center;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
      }
      
      .summary-card:hover {
        transform: translateY(-2px);
        box-shadow: var(--shadow-lg);
      }
      
      .summary-card .number {
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 8px;
        display: block;
      }
      
      .summary-card .label {
        font-size: 0.875rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--gray-600);
      }
      
      .summary-card.added .number { color: var(--success-color); }
      .summary-card.removed .number { color: var(--danger-color); }
      .summary-card.modified .number { color: var(--warning-color); }
      
      .controls { 
        background: white;
        border-radius: var(--border-radius);
        padding: 20px;
        margin-bottom: 24px;
        box-shadow: var(--shadow-sm);
        border: 1px solid var(--gray-200);
      }
      
      .controls input { 
        width: 100%;
        max-width: 400px;
        padding: 12px 16px;
        border: 2px solid var(--gray-200);
        border-radius: var(--border-radius);
        font-size: 1rem;
        transition: border-color 0.2s ease, box-shadow 0.2s ease;
        background: var(--gray-50);
      }
      
      .controls input:focus {
        outline: none;
        border-color: var(--primary-color);
        box-shadow: 0 0 0 3px rgb(37 99 235 / 0.1);
        background: white;
      }
      
      .section-wrapper {
        background: white;
        border-radius: var(--border-radius-lg);
        margin-bottom: 24px;
        box-shadow: var(--shadow-md);
        border: 1px solid var(--gray-200);
        overflow: hidden;
      }
      
      .section-header {
        padding: 20px 24px;
        background: var(--gray-50);
        border-bottom: 1px solid var(--gray-200);
        display: flex;
        justify-content: space-between;
        align-items: center;
      }
      
      .section-title {
        margin: 0;
        display: flex;
        align-items: center;
        gap: 12px;
      }
      
      .section-badge {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 24px;
        height: 24px;
        border-radius: 50%;
        font-size: 0.75rem;
        font-weight: 600;
        color: white;
      }
      
      .section-badge.added { background: var(--success-color); }
      .section-badge.removed { background: var(--danger-color); }
      .section-badge.modified { background: var(--warning-color); }
      
      .section-meta {
        color: var(--gray-600);
        font-size: 0.875rem;
        display: flex;
        align-items: center;
        gap: 8px;
      }
      
      .match-count {
        background: var(--primary-color);
        color: white;
        padding: 4px 8px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 500;
      }
      
      .overflow { 
        max-height: 600px; 
        overflow: auto; 
        position: relative;
      }
      
      table { 
        border-collapse: collapse; 
        width: 100%; 
        font-size: 0.875rem;
      }
      
      th, td { 
        padding: 12px 16px; 
        text-align: left; 
        border-bottom: 1px solid var(--gray-200);
        vertical-align: top;
      }
      
      th { 
        background: var(--gray-50);
        position: sticky; 
        top: 0; 
        z-index: 10;
        font-weight: 600;
        color: var(--gray-700);
        border-bottom: 2px solid var(--gray-300);
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
      }
      
      tr:hover { 
        background: var(--gray-50);
      }
      
      .added { 
        background: rgb(34 197 94 / 0.1);
        border-left: 4px solid var(--success-color);
      }
      
      .removed { 
        background: rgb(239 68 68 / 0.1);
        border-left: 4px solid var(--danger-color);
      }
      
      .changed-old { 
        background: rgb(239 68 68 / 0.1);
        text-decoration: line-through; 
        color: var(--danger-color);
        padding: 4px 8px;
        border-radius: 4px;
        margin-bottom: 4px;
        display: block;
        font-weight: 500;
      }
      
      .changed-new { 
        background: rgb(34 197 94 / 0.1);
        color: var(--success-color);
        padding: 4px 8px;
        border-radius: 4px;
        display: block;
        font-weight: 500;
      }
      
      code { 
        background: var(--gray-100);
        padding: 2px 6px; 
        border-radius: 4px;
        font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
        font-size: 0.875em;
        color: var(--gray-800);
      }
      
      .key { 
        white-space: nowrap;
        font-weight: 600;
        color: var(--gray-700);
      }
      
      .key code {
        background: var(--primary-color);
        color: white;
        font-weight: 500;
      }
      
      .mono { 
        font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
      }
      
      .small { 
        color: var(--gray-500); 
        font-size: 0.75rem;
        font-weight: 500;
      }
      
      .rawdiff { 
        white-space: pre; 
        overflow: auto; 
        border: 1px solid var(--gray-200); 
        padding: 20px; 
        background: var(--gray-50);
        border-radius: var(--border-radius);
        font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
        font-size: 0.875rem;
        line-height: 1.5;
      }
      
      .hidden { display: none; }
      
      /* Empty state */
      .empty-state {
        text-align: center;
        padding: 48px 24px;
        color: var(--gray-500);
      }
      
      .empty-state-icon {
        font-size: 3rem;
        margin-bottom: 16px;
        opacity: 0.5;
      }
      
      /* Responsive design */
      @media (max-width: 768px) {
        body {
          padding: 16px;
        }
        
        h1 {
          font-size: 2rem;
        }
        
        .summary-cards {
          grid-template-columns: 1fr;
        }
        
        .summary-card {
          padding: 20px;
        }
        
        .section-header {
          padding: 16px 20px;
          flex-direction: column;
          align-items: flex-start;
          gap: 12px;
        }
        
        th, td {
          padding: 8px 12px;
          font-size: 0.8rem;
        }
        
        .overflow {
          max-height: 400px;
        }
        
        .controls input {
          max-width: 100%;
        }
      }
      
      /* Scrollbar styling */
      .overflow::-webkit-scrollbar {
        width: 8px;
        height: 8px;
      }
      
      .overflow::-webkit-scrollbar-track {
        background: var(--gray-100);
        border-radius: 4px;
      }
      
      .overflow::-webkit-scrollbar-thumb {
        background: var(--gray-300);
        border-radius: 4px;
      }
      
      .overflow::-webkit-scrollbar-thumb:hover {
        background: var(--gray-400);
      }
      
      /* Loading and animation states */
      @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
      }
      
      .section-wrapper {
        animation: fadeIn 0.3s ease-out;
      }
      
      /* Improved focus states */
      .controls input:focus-visible,
      button:focus-visible {
        outline: 2px solid var(--primary-color);
        outline-offset: 2px;
      }
      
      /* Better table cell content handling */
      td code {
        max-width: 300px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        display: inline-block;
        vertical-align: top;
      }
      
      td:hover code {
        max-width: none;
        white-space: normal;
        word-break: break-all;
      }
    </style>
    """
    
    js = """
    <script>
      let debounceTimer;
      
      function filterTables() {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
          const q = document.getElementById('filterQuery').value.toLowerCase().trim();
          
          for (const wrapper of document.querySelectorAll('.section-wrapper')) {
            let shown = 0;
            const rows = wrapper.querySelectorAll('tbody tr');
            
            rows.forEach((tr) => {
              const text = tr.textContent.toLowerCase();
              const match = !q || text.includes(q);
              tr.style.display = match ? '' : 'none';
              if (match) shown++;
            });
            
            const counter = wrapper.querySelector('.match-count');
            if (counter) {
              if (q) {
                counter.textContent = shown + ' match' + (shown === 1 ? '' : 'es');
                counter.style.display = 'inline-block';
              } else {
                counter.style.display = 'none';
              }
            }
            
            // Hide/show entire section if no matches
            const hasMatches = shown > 0 || !q;
            wrapper.style.display = hasMatches ? 'block' : 'none';
          }
          
          // Update summary cards based on visible rows
          updateSummaryHighlight(q);
        }, 150);
      }
      
      function updateSummaryHighlight(query) {
        const cards = document.querySelectorAll('.summary-card');
        cards.forEach(card => {
          if (query) {
            card.style.opacity = '0.6';
          } else {
            card.style.opacity = '1';
          }
        });
      }
      
      // Enhanced keyboard navigation
      document.addEventListener('DOMContentLoaded', function() {
        const searchInput = document.getElementById('filterQuery');
        
        // Focus search on Ctrl/Cmd + F
        document.addEventListener('keydown', function(e) {
          if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
            e.preventDefault();
            searchInput.focus();
          }
          
          // Clear search on Escape
          if (e.key === 'Escape' && document.activeElement === searchInput) {
            searchInput.value = '';
            filterTables();
          }
        });
        
        // Auto-focus search input
        searchInput.focus();
        
        // Add loading state simulation
        document.body.style.opacity = '0';
        setTimeout(() => {
          document.body.style.transition = 'opacity 0.3s ease';
          document.body.style.opacity = '1';
        }, 50);
      });
      
      // Smooth scrolling for long tables
      document.addEventListener('DOMContentLoaded', function() {
        const overflowContainers = document.querySelectorAll('.overflow');
        overflowContainers.forEach(container => {
          container.style.scrollBehavior = 'smooth';
        });
      });
    </script>
    """

    def key_to_str(key: list[str] | tuple) -> str:
        return ", ".join(_escape(str(k)) for k in key)

    parts: list[str] = []
    parts.append("<!DOCTYPE html>")
    parts.append("<html lang=\"en\">")
    parts.append("<head>")
    parts.append("<meta charset=\"utf-8\">")
    parts.append("<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">")
    parts.append("<title>CSV Diff Report</title>")
    parts.append(css)
    parts.append("</head>")
    parts.append("<body>")
    parts.append("<div class=\"container\">")
    parts.append("<h1>CSV Diff Report</h1>")
    
    # Add summary cards
    parts.append("<div class=\"summary-cards\">")
    parts.append(f"<div class=\"summary-card added\"><span class=\"number\">{len(diff.added)}</span><span class=\"label\">Added Rows</span></div>")
    parts.append(f"<div class=\"summary-card removed\"><span class=\"number\">{len(diff.removed)}</span><span class=\"label\">Removed Rows</span></div>")
    parts.append(f"<div class=\"summary-card modified\"><span class=\"number\">{len(diff.modified)}</span><span class=\"label\">Modified Rows</span></div>")
    total_changes = len(diff.added) + len(diff.removed) + len(diff.modified)
    parts.append(f"<div class=\"summary-card\"><span class=\"number\" style=\"color: var(--primary-color);\">{total_changes}</span><span class=\"label\">Total Changes</span></div>")
    parts.append("</div>")
    
    parts.append(
        "<div class=\"controls\"><input id=\"filterQuery\" placeholder=\"🔍 Search rows, names, departments, or any content...\" oninput=\"filterTables()\"></div>"
    )

    def section_html(title: str, changes: Iterable[RowChange], kind: str) -> None:
        changes_list = list(changes)
        
        # Get appropriate icon for section type
        icons = {
            "added": "➕",
            "removed": "➖", 
            "modified": "✏️"
        }
        icon = icons.get(kind, "📄")
        
        parts.append(f"<div class=\"section-wrapper\">")
        parts.append(f"<div class=\"section-header\">")
        parts.append(f"<h2 class=\"section-title\">{icon} {_escape(title)} <span class=\"section-badge {kind}\">{len(changes_list)}</span></h2>")
        parts.append(f"<div class=\"section-meta\">")
        parts.append(f"<span>Showing up to {max_rows:,} rows</span>")
        parts.append(f"<span class=\"match-count\"></span>")
        parts.append(f"</div>")
        parts.append(f"</div>")
        
        if len(changes_list) == 0:
            parts.append("<div class=\"empty-state\">")
            parts.append("<div class=\"empty-state-icon\">📭</div>")
            parts.append(f"<p>No {kind} rows found</p>")
            parts.append("</div>")
        else:
            columns = _collect_columns(changes_list)
            parts.append("<div class=\"overflow\"><table>")
            # Header
            parts.append("<thead><tr><th class=\"key\">Key</th>")
            for col in columns:
                parts.append(f"<th>{_escape(col)}</th>")
            parts.append("</tr></thead><tbody>")

            count = 0
            for ch in changes_list:
                if count >= max_rows:
                    break
                key_html = f'<td class="key mono"><code>{key_to_str(ch.key)}</code></td>'
                if ch.kind == "added":
                    row = ch.row_new or {}
                    row_tds = "".join(
                        f'<td class="added"><code>{_escape(row.get(c, ""))}</code></td>' for c in columns
                    )
                    parts.append(f"<tr>{key_html}{row_tds}</tr>")
                elif ch.kind == "removed":
                    row = ch.row_old or {}
                    row_tds = "".join(
                        f'<td class="removed"><code>{_escape(row.get(c, ""))}</code></td>' for c in columns
                    )
                    parts.append(f"<tr>{key_html}{row_tds}</tr>")
                else:
                    old_map = {c.column: c.old for c in ch.changes}
                    new_map = {c.column: c.new for c in ch.changes}
                    tds = []
                    for c in columns:
                        if c in old_map or c in new_map:
                            old_v = _escape(old_map.get(c, ""))
                            new_v = _escape(new_map.get(c, ""))
                            tds.append(
                                f'<td><div class="changed-old"><code>{old_v}</code></div><div class="changed-new"><code>{new_v}</code></div></td>'
                            )
                        else:
                            tds.append("<td></td>")
                    parts.append(f"<tr>{key_html}{''.join(tds)}</tr>")
                count += 1

            parts.append("</tbody></table></div>")
        
        parts.append("</div>") # Close section-wrapper

    section_html("Added", diff.added, "added")
    section_html("Removed", diff.removed, "removed")
    section_html("Modified", diff.modified, "modified")

    if include_raw and diff.raw_diff:
        parts.append("<div class=\"section-wrapper\">")
        parts.append("<div class=\"section-header\">")
        parts.append("<h2 class=\"section-title\">📄 Raw Unified Diff</h2>")
        parts.append("</div>")
        parts.append(f"<div class=\"rawdiff\">{_escape(diff.raw_diff)}</div>")
        parts.append("</div>")

    parts.append("</div>") # Close container
    parts.append(js)
    parts.append("</body>")
    parts.append("</html>")
    return "\n".join(parts)

