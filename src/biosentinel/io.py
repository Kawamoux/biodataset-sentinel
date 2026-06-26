"""Delimited file readers used by the audit engine."""

from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Iterable

from .models import CellProblem, DataFormatError, FeatureTable, MeasurementMatrix, SampleTable

MISSING_VALUES = {"", "na", "n/a", "nan", "null", "none"}


def read_sample_table(path: str | Path, *, id_column: str = "sample_id") -> SampleTable:
    headers, rows = _read_delimited(path)
    return SampleTable(headers=headers, records=_records(headers, rows), id_column=id_column)


def read_feature_table(path: str | Path, *, id_column: str = "feature_id") -> FeatureTable:
    headers, rows = _read_delimited(path)
    return FeatureTable(headers=headers, records=_records(headers, rows), id_column=id_column)


def read_measurement_matrix(
    path: str | Path,
    *,
    feature_id_column: str = "feature_id",
) -> MeasurementMatrix:
    headers, rows = _read_delimited(path)
    if not headers:
        raise DataFormatError("matrix file has no header row")

    sample_ids = headers[1:]
    feature_ids: list[str] = []
    values: list[list[float | None]] = []
    cell_problems: list[CellProblem] = []

    for row in rows:
        padded = _pad(row, len(headers))
        feature_id = padded[0].strip()
        feature_ids.append(feature_id)
        numeric_row: list[float | None] = []
        for column_id, raw_value in zip(sample_ids, padded[1:]):
            parsed, problem = _parse_number(raw_value)
            numeric_row.append(parsed)
            if problem is not None:
                cell_problems.append(
                    CellProblem(
                        row_id=feature_id,
                        column_id=column_id,
                        raw_value=raw_value,
                        problem=problem,
                    )
                )
        values.append(numeric_row)

    return MeasurementMatrix(
        headers=headers,
        feature_ids=feature_ids,
        sample_ids=sample_ids,
        values=values,
        cell_problems=cell_problems,
        feature_id_column=feature_id_column,
    )


def duplicated_values(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: list[str] = []
    for value in values:
        if value in seen and value not in duplicates:
            duplicates.append(value)
        seen.add(value)
    return duplicates


def _read_delimited(path: str | Path) -> tuple[list[str], list[list[str]]]:
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        text = handle.read()
    if not text.strip():
        raise DataFormatError("input file is empty")

    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;")
    except csv.Error:
        dialect = csv.excel_tab if "\t" in sample and sample.count("\t") >= sample.count(",") else csv.excel

    rows = list(csv.reader(text.splitlines(), dialect))
    if not rows:
        raise DataFormatError("input file has no rows")

    headers = [header.strip() for header in rows[0]]
    data_rows = [[cell.strip() for cell in row] for row in rows[1:] if any(cell.strip() for cell in row)]
    return headers, data_rows


def _records(headers: list[str], rows: list[list[str]]) -> list[dict[str, str]]:
    keys = _unique_keys(headers)
    records: list[dict[str, str]] = []
    for row in rows:
        padded = _pad(row, len(keys))
        records.append({key: value.strip() for key, value in zip(keys, padded)})
    return records


def _unique_keys(headers: list[str]) -> list[str]:
    counts: dict[str, int] = {}
    keys: list[str] = []
    for header in headers:
        counts[header] = counts.get(header, 0) + 1
        if counts[header] == 1:
            keys.append(header)
        else:
            keys.append(f"{header}__duplicate_{counts[header]}")
    return keys


def _pad(row: list[str], width: int) -> list[str]:
    if len(row) >= width:
        return row[:width]
    return row + [""] * (width - len(row))


def _parse_number(raw_value: str) -> tuple[float | None, str | None]:
    stripped = raw_value.strip()
    if stripped.lower() in MISSING_VALUES:
        return None, "missing"
    try:
        value = float(stripped)
    except ValueError:
        return None, "non_numeric"
    if not math.isfinite(value):
        return None, "non_finite"
    return value, None
