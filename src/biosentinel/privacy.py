"""Conservative privacy pattern checks for metadata values."""

from __future__ import annotations

import re
from collections.abc import Iterable

from .models import Issue

EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
WINDOWS_PATH_RE = re.compile(r"\b[A-Z]:\\[^\s,;]+", re.IGNORECASE)
UNC_PATH_RE = re.compile(r"\\\\[A-Za-z0-9_.-]+\\[^\s,;]+")
UNIX_USER_PATH_RE = re.compile(r"(?<!\w)/(?:Users|home|mnt|Volumes)/[^\s,;]+")
PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\d .()/-]{7,}\d)(?!\d)")
LONG_TOKEN_RE = re.compile(r"\b[A-Za-z0-9_-]{32,}\b")


def scan_records(
    records: Iterable[dict[str, str]],
    *,
    table_name: str,
    max_examples: int = 5,
) -> list[Issue]:
    findings: dict[str, list[dict[str, str]]] = {
        "email": [],
        "path": [],
        "phone": [],
        "long_token": [],
    }

    for row_number, record in enumerate(records, start=1):
        for column, value in record.items():
            if not value:
                continue
            matched = _classify(value)
            if matched and len(findings[matched]) < max_examples:
                findings[matched].append(
                    {
                        "table": table_name,
                        "row_number": str(row_number),
                        "column": column,
                        "pattern": matched,
                    }
                )

    issues: list[Issue] = []
    for pattern, examples in findings.items():
        if not examples:
            continue
        issues.append(
            Issue(
                code=f"privacy_{pattern}",
                severity="warning",
                message=f"Potentially sensitive {pattern.replace('_', ' ')} pattern found in {table_name}.",
                recommendation=(
                    "Review the flagged metadata fields before sharing reports or datasets. "
                    "Replace local identifiers with study-safe identifiers when possible."
                ),
                context={"examples": examples},
            )
        )
    return issues


def scan_headers(headers: Iterable[str], *, table_name: str) -> list[Issue]:
    examples = [
        {"table": table_name, "column": header, "pattern": "path"}
        for header in headers
        if _looks_like_path(header)
    ]
    if not examples:
        return []
    return [
        Issue(
            code="privacy_header_path",
            severity="warning",
            message=f"Column names in {table_name} look like file paths.",
            recommendation="Rename columns before sharing the dataset or report.",
            context={"examples": examples[:5]},
        )
    ]


def _classify(value: str) -> str | None:
    if EMAIL_RE.search(value):
        return "email"
    if _looks_like_path(value):
        return "path"
    if PHONE_RE.search(value):
        return "phone"
    if LONG_TOKEN_RE.search(value):
        return "long_token"
    return None


def _looks_like_path(value: str) -> bool:
    return bool(
        WINDOWS_PATH_RE.search(value)
        or UNC_PATH_RE.search(value)
        or UNIX_USER_PATH_RE.search(value)
    )
