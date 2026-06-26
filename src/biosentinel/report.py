"""Report rendering helpers."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any

from .models import AuditReport, Issue


def write_json_report(report: AuditReport, path: str | Path) -> None:
    Path(path).write_text(
        json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_html_report(report: AuditReport, path: str | Path) -> None:
    Path(path).write_text(render_html_report(report), encoding="utf-8")


def render_html_report(report: AuditReport) -> str:
    issue_rows = "\n".join(_issue_row(issue) for issue in report.issues)
    metric_rows = "\n".join(
        f"<tr><th>{escape(str(key))}</th><td>{escape(_format_value(value))}</td></tr>"
        for key, value in sorted(report.metrics.items())
    )
    if not issue_rows:
        issue_rows = (
            "<tr><td colspan=\"5\" class=\"empty\">No issues were detected by the configured checks.</td></tr>"
        )
    if not metric_rows:
        metric_rows = "<tr><td colspan=\"2\" class=\"empty\">No metrics available.</td></tr>"

    summary = report.summary
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>BioDataset Sentinel Report</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #17202a;
      --muted: #5c6975;
      --line: #d9e2ea;
      --panel: #f7fafc;
      --ok: #167a4a;
      --review: #9a6700;
      --fail: #b42318;
    }}
    body {{
      margin: 0;
      font: 16px/1.5 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--ink);
      background: white;
    }}
    main {{
      max-width: 1120px;
      margin: 0 auto;
      padding: 40px 24px 56px;
    }}
    header {{
      border-bottom: 1px solid var(--line);
      margin-bottom: 28px;
      padding-bottom: 20px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 2rem;
      letter-spacing: 0;
    }}
    h2 {{
      margin-top: 34px;
      font-size: 1.25rem;
    }}
    .muted {{
      color: var(--muted);
      margin: 0;
    }}
    .summary {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 12px;
      margin: 24px 0;
    }}
    .tile {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px 16px;
      background: var(--panel);
    }}
    .tile span {{
      display: block;
      color: var(--muted);
      font-size: 0.85rem;
    }}
    .tile strong {{
      display: block;
      margin-top: 4px;
      font-size: 1.35rem;
    }}
    .status {{
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 4px 10px;
      font-weight: 700;
      text-transform: uppercase;
      font-size: 0.8rem;
      letter-spacing: 0.04em;
    }}
    .status.pass {{ color: var(--ok); background: #e8f6ef; }}
    .status.review {{ color: var(--review); background: #fff4d6; }}
    .status.fail {{ color: var(--fail); background: #fde8e5; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      border: 1px solid var(--line);
      overflow-wrap: anywhere;
    }}
    th, td {{
      border-bottom: 1px solid var(--line);
      padding: 10px 12px;
      text-align: left;
      vertical-align: top;
    }}
    th {{
      background: var(--panel);
      font-size: 0.88rem;
    }}
    tr:last-child td, tr:last-child th {{
      border-bottom: 0;
    }}
    code {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 0.9em;
    }}
    .severity {{
      font-weight: 700;
      text-transform: uppercase;
      font-size: 0.8rem;
    }}
    .severity.error {{ color: var(--fail); }}
    .severity.warning {{ color: var(--review); }}
    .severity.info {{ color: var(--muted); }}
    .empty {{
      color: var(--muted);
      text-align: center;
      padding: 24px;
    }}
  </style>
</head>
<body>
<main>
  <header>
    <h1>BioDataset Sentinel Report</h1>
    <p class="muted">Dataset: {escape(report.dataset_name)} · Created: {escape(report.created_at_utc)}</p>
  </header>

  <section class="summary" aria-label="Audit summary">
    <div class="tile"><span>Status</span><strong><span class="status {escape(summary.status)}">{escape(summary.status)}</span></strong></div>
    <div class="tile"><span>Samples</span><strong>{summary.sample_count}</strong></div>
    <div class="tile"><span>Features</span><strong>{summary.feature_count}</strong></div>
    <div class="tile"><span>Measurements</span><strong>{summary.measurement_count}</strong></div>
    <div class="tile"><span>Errors</span><strong>{summary.issue_counts["error"]}</strong></div>
    <div class="tile"><span>Warnings</span><strong>{summary.issue_counts["warning"]}</strong></div>
  </section>

  <section>
    <h2>Findings</h2>
    <table>
      <thead>
        <tr>
          <th>Severity</th>
          <th>Code</th>
          <th>Message</th>
          <th>Recommendation</th>
          <th>Context</th>
        </tr>
      </thead>
      <tbody>
        {issue_rows}
      </tbody>
    </table>
  </section>

  <section>
    <h2>Metrics</h2>
    <table>
      <tbody>
        {metric_rows}
      </tbody>
    </table>
  </section>
</main>
</body>
</html>
"""


def _issue_row(issue: Issue) -> str:
    return (
        "<tr>"
        f"<td><span class=\"severity {escape(issue.severity)}\">{escape(issue.severity)}</span></td>"
        f"<td><code>{escape(issue.code)}</code></td>"
        f"<td>{escape(issue.message)}</td>"
        f"<td>{escape(issue.recommendation)}</td>"
        f"<td><code>{escape(_format_value(issue.context))}</code></td>"
        "</tr>"
    )


def _format_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.6g}"
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, sort_keys=True)
    return str(value)
