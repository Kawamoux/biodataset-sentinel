"""Audit support for MicroTrace-style report directories."""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median
from typing import Any

from .io import DataFormatError, duplicated_values, read_table_records
from .models import AuditReport, Issue
from .privacy import scan_headers, scan_records

SUMMARY_FILE = "summary.csv"
OBJECTS_FILE = "objects.csv"
STATISTICS_FILE = "statistics.csv"

SUMMARY_REQUIRED = [
    "image",
    "condition",
    "threshold",
    "object_count",
    "total_area_px",
    "median_area_px",
    "mean_circularity",
    "mean_elongation",
    "mean_intensity",
]

OBJECTS_REQUIRED = [
    "image",
    "condition",
    "object_id",
    "area_px",
    "perimeter_px",
    "circularity",
    "elongation",
    "centroid_x",
    "centroid_y",
    "bbox_x",
    "bbox_y",
    "bbox_width",
    "bbox_height",
    "mean_intensity",
    "integrated_intensity",
]

STATISTICS_REQUIRED = [
    "condition",
    "object_count",
    "mean_area_px",
    "median_area_px",
    "mean_perimeter_px",
    "mean_circularity",
    "mean_elongation",
    "mean_intensity",
    "mean_integrated_intensity",
]

SUMMARY_NUMERIC = [
    "threshold",
    "object_count",
    "total_area_px",
    "median_area_px",
    "mean_circularity",
    "mean_elongation",
    "mean_intensity",
]

OBJECT_NUMERIC = [
    "object_id",
    "area_px",
    "perimeter_px",
    "circularity",
    "elongation",
    "centroid_x",
    "centroid_y",
    "bbox_x",
    "bbox_y",
    "bbox_width",
    "bbox_height",
    "mean_intensity",
    "integrated_intensity",
]

STATISTICS_NUMERIC = [column for column in STATISTICS_REQUIRED if column != "condition"]


def audit_microtrace_report(
    report_dir: str | Path,
    *,
    dataset_name: str = "microtrace report",
    min_images_per_condition: int = 2,
) -> AuditReport:
    """Audit a MicroTrace report directory containing CSV outputs."""

    root = Path(report_dir)
    summary_headers, summary_records = _required_records(root, SUMMARY_FILE)
    object_headers, object_records = _required_records(root, OBJECTS_FILE)
    statistics_headers, statistics_records = _optional_records(root, STATISTICS_FILE)

    issues: list[Issue] = []
    issues.extend(_required_column_checks(summary_headers, SUMMARY_REQUIRED, table_name=SUMMARY_FILE))
    issues.extend(_required_column_checks(object_headers, OBJECTS_REQUIRED, table_name=OBJECTS_FILE))
    if statistics_headers:
        issues.extend(_required_column_checks(statistics_headers, STATISTICS_REQUIRED, table_name=STATISTICS_FILE))

    issues.extend(scan_headers(summary_headers, table_name=SUMMARY_FILE))
    issues.extend(scan_records(_privacy_records(summary_records, ["image", "condition"]), table_name=SUMMARY_FILE))
    issues.extend(scan_headers(object_headers, table_name=OBJECTS_FILE))
    issues.extend(scan_records(_privacy_records(object_records, ["image", "condition"]), table_name=OBJECTS_FILE))
    if statistics_headers:
        issues.extend(scan_headers(statistics_headers, table_name=STATISTICS_FILE))
        issues.extend(scan_records(_privacy_records(statistics_records, ["condition"]), table_name=STATISTICS_FILE))

    parsed = _parse_microtrace_tables(
        summary_records=summary_records,
        object_records=object_records,
        statistics_records=statistics_records,
    )
    issues.extend(parsed["issues"])

    if not summary_records:
        issues.append(
            Issue(
                code="microtrace_empty_summary",
                severity="error",
                message="MicroTrace summary.csv contains no image rows.",
                recommendation="Re-run MicroTrace and confirm at least one input image was analyzed.",
            )
        )
    if not object_records:
        issues.append(
            Issue(
                code="microtrace_empty_objects",
                severity="warning",
                message="MicroTrace objects.csv contains no object measurements.",
                recommendation="Confirm whether no objects were expected, or adjust segmentation parameters.",
            )
        )

    issues.extend(
        _consistency_checks(
            summary_records=summary_records,
            object_records=object_records,
            statistics_records=statistics_records,
            parsed=parsed,
            min_images_per_condition=min_images_per_condition,
        )
    )

    metrics = _metrics(summary_records=summary_records, object_records=object_records, parsed=parsed)
    object_count = len(object_records)
    measurement_count = object_count * len(OBJECT_NUMERIC)

    return AuditReport.build(
        dataset_name=dataset_name,
        sample_count=len(summary_records),
        feature_count=object_count,
        measurement_count=measurement_count,
        issues=_sort_issues(issues),
        metrics=metrics,
    )


def _required_records(root: Path, filename: str) -> tuple[list[str], list[dict[str, str]]]:
    path = root / filename
    if not path.exists():
        raise FileNotFoundError(filename)
    return read_table_records(path)


def _optional_records(root: Path, filename: str) -> tuple[list[str], list[dict[str, str]]]:
    path = root / filename
    if not path.exists():
        return [], []
    return read_table_records(path)


def _required_column_checks(headers: list[str], required: list[str], *, table_name: str) -> list[Issue]:
    issues: list[Issue] = []
    missing = [column for column in required if column not in headers]
    if missing:
        issues.append(
            Issue(
                code=f"microtrace_{_table_code(table_name)}_missing_columns",
                severity="error",
                message=f"{table_name} is missing required MicroTrace columns.",
                recommendation="Regenerate the report with a compatible MicroTrace version or restore the missing columns.",
                context={"missing": missing},
            )
        )

    duplicates = duplicated_values(headers)
    if duplicates:
        issues.append(
            Issue(
                code=f"microtrace_{_table_code(table_name)}_duplicate_columns",
                severity="error",
                message=f"{table_name} contains duplicated column names.",
                recommendation="Ensure report tables have unique columns before auditing.",
                context={"duplicates": duplicates[:10]},
            )
        )
    return issues


def _privacy_records(records: list[dict[str, str]], columns: list[str]) -> list[dict[str, str]]:
    return [{column: record.get(column, "") for column in columns} for record in records]


def _parse_microtrace_tables(
    *,
    summary_records: list[dict[str, str]],
    object_records: list[dict[str, str]],
    statistics_records: list[dict[str, str]],
) -> dict[str, Any]:
    problems: list[dict[str, str]] = []
    summary_numeric = _parse_records(summary_records, SUMMARY_NUMERIC, table_name=SUMMARY_FILE, problems=problems)
    object_numeric = _parse_records(object_records, OBJECT_NUMERIC, table_name=OBJECTS_FILE, problems=problems)
    statistics_numeric = _parse_records(
        statistics_records,
        STATISTICS_NUMERIC,
        table_name=STATISTICS_FILE,
        problems=problems,
    )

    issues: list[Issue] = []
    if problems:
        issues.append(
            Issue(
                code="microtrace_numeric_parse_problems",
                severity="error",
                message="MicroTrace CSV outputs contain missing, non-numeric, or non-finite numeric values.",
                recommendation="Regenerate the report or correct the affected numeric cells before review.",
                context={"examples": problems[:20], "count": len(problems)},
            )
        )

    return {
        "issues": issues,
        "summary_numeric": summary_numeric,
        "object_numeric": object_numeric,
        "statistics_numeric": statistics_numeric,
    }


def _parse_records(
    records: list[dict[str, str]],
    numeric_columns: list[str],
    *,
    table_name: str,
    problems: list[dict[str, str]],
) -> list[dict[str, float | None]]:
    parsed: list[dict[str, float | None]] = []
    for row_number, record in enumerate(records, start=1):
        parsed_row: dict[str, float | None] = {}
        row_label = record.get("image") or record.get("condition") or str(row_number)
        for column in numeric_columns:
            raw_value = record.get(column, "")
            parsed_value = _parse_float(raw_value)
            parsed_row[column] = parsed_value
            if parsed_value is None:
                problems.append(
                    {
                        "table": table_name,
                        "row": row_label,
                        "column": column,
                        "problem": "invalid_numeric",
                    }
                )
        parsed.append(parsed_row)
    return parsed


def _consistency_checks(
    *,
    summary_records: list[dict[str, str]],
    object_records: list[dict[str, str]],
    statistics_records: list[dict[str, str]],
    parsed: dict[str, Any],
    min_images_per_condition: int,
) -> list[Issue]:
    issues: list[Issue] = []
    issues.extend(_image_identity_checks(summary_records, object_records))
    issues.extend(_object_identity_checks(object_records))
    issues.extend(_summary_object_checks(summary_records, object_records, parsed["summary_numeric"], parsed["object_numeric"]))
    issues.extend(_object_measurement_checks(object_records, parsed["object_numeric"]))
    issues.extend(_condition_replication_checks(summary_records, min_images_per_condition=min_images_per_condition))
    if statistics_records:
        issues.extend(_statistics_checks(statistics_records, object_records, parsed["statistics_numeric"]))
    return issues


def _image_identity_checks(
    summary_records: list[dict[str, str]],
    object_records: list[dict[str, str]],
) -> list[Issue]:
    issues: list[Issue] = []
    summary_images = [record.get("image", "") for record in summary_records]
    object_images = [record.get("image", "") for record in object_records]

    empty_summary_images = sum(1 for image in summary_images if not image)
    if empty_summary_images:
        issues.append(
            Issue(
                code="microtrace_empty_image_ids",
                severity="error",
                message="summary.csv contains empty image identifiers.",
                recommendation="Regenerate the report with stable image identifiers.",
                context={"count": empty_summary_images},
            )
        )

    duplicate_summary_images = duplicated_values([image for image in summary_images if image])
    if duplicate_summary_images:
        issues.append(
            Issue(
                code="microtrace_duplicate_summary_images",
                severity="error",
                message="summary.csv contains duplicated image identifiers.",
                recommendation="Use unique image identifiers so per-image summaries are unambiguous.",
                context={"images": duplicate_summary_images[:20], "count": len(duplicate_summary_images)},
            )
        )

    missing_from_summary = sorted({image for image in object_images if image} - {image for image in summary_images if image})
    if missing_from_summary:
        issues.append(
            Issue(
                code="microtrace_objects_missing_summary",
                severity="error",
                message="objects.csv contains measurements for images absent from summary.csv.",
                recommendation="Regenerate a complete report or remove unmatched object rows.",
                context={"images": missing_from_summary[:20], "count": len(missing_from_summary)},
            )
        )

    return issues


def _object_identity_checks(object_records: list[dict[str, str]]) -> list[Issue]:
    pairs = [(record.get("image", ""), record.get("object_id", "")) for record in object_records]
    duplicate_pairs = duplicated_values([f"{image}::{object_id}" for image, object_id in pairs if image and object_id])
    if not duplicate_pairs:
        return []
    return [
        Issue(
            code="microtrace_duplicate_object_ids",
            severity="error",
            message="objects.csv contains duplicated object identifiers within an image.",
            recommendation="Regenerate object measurements so each image/object_id pair is unique.",
            context={"object_keys": duplicate_pairs[:20], "count": len(duplicate_pairs)},
        )
    ]


def _summary_object_checks(
    summary_records: list[dict[str, str]],
    object_records: list[dict[str, str]],
    summary_numeric: list[dict[str, float | None]],
    object_numeric: list[dict[str, float | None]],
) -> list[Issue]:
    issues: list[Issue] = []
    objects_by_image: dict[str, list[tuple[dict[str, str], dict[str, float | None]]]] = defaultdict(list)
    for record, numeric in zip(object_records, object_numeric):
        objects_by_image[record.get("image", "")].append((record, numeric))

    count_mismatches: list[dict[str, Any]] = []
    area_mismatches: list[dict[str, Any]] = []
    median_mismatches: list[dict[str, Any]] = []
    mean_mismatches: list[dict[str, Any]] = []

    for record, numeric in zip(summary_records, summary_numeric):
        image = record.get("image", "")
        objects = objects_by_image.get(image, [])
        observed_count = len(objects)
        expected_count = _as_int(numeric.get("object_count"))
        if expected_count is not None and expected_count != observed_count:
            count_mismatches.append({"image": image, "summary": expected_count, "objects": observed_count})

        areas = _valid_numbers(objects, "area_px")
        circularities = _valid_numbers(objects, "circularity")
        elongations = _valid_numbers(objects, "elongation")
        intensities = _valid_numbers(objects, "mean_intensity")

        total_area = sum(areas)
        if areas and not _close(numeric.get("total_area_px"), total_area, abs_tol=1.0):
            area_mismatches.append({"image": image, "summary": numeric.get("total_area_px"), "computed": total_area})
        if areas and not _close(numeric.get("median_area_px"), median(areas), abs_tol=1e-3):
            median_mismatches.append({"image": image, "summary": numeric.get("median_area_px"), "computed": median(areas)})
        expected_means = {
            "mean_circularity": _mean(circularities),
            "mean_elongation": _mean(elongations),
            "mean_intensity": _mean(intensities),
        }
        for column, computed in expected_means.items():
            if computed is not None and not _close(numeric.get(column), computed, abs_tol=1e-4):
                mean_mismatches.append({"image": image, "column": column, "summary": numeric.get(column), "computed": computed})

    if count_mismatches:
        issues.append(
            Issue(
                code="microtrace_object_count_mismatch",
                severity="error",
                message="Per-image object counts do not match between summary.csv and objects.csv.",
                recommendation="Regenerate the report so summary and object tables describe the same analysis run.",
                context={"examples": count_mismatches[:20], "count": len(count_mismatches)},
            )
        )
    if area_mismatches:
        issues.append(
            Issue(
                code="microtrace_total_area_mismatch",
                severity="error",
                message="Per-image total area values do not match recalculated object measurements.",
                recommendation="Regenerate the report from a single consistent MicroTrace run.",
                context={"examples": area_mismatches[:20], "count": len(area_mismatches)},
            )
        )
    if median_mismatches or mean_mismatches:
        issues.append(
            Issue(
                code="microtrace_summary_statistic_mismatch",
                severity="warning",
                message="Some per-image summary statistics differ from recalculated object measurements.",
                recommendation="Review rounding, report version, and whether object rows were edited after generation.",
                context={
                    "median_examples": median_mismatches[:10],
                    "mean_examples": mean_mismatches[:10],
                    "count": len(median_mismatches) + len(mean_mismatches),
                },
            )
        )

    return issues


def _object_measurement_checks(
    object_records: list[dict[str, str]],
    object_numeric: list[dict[str, float | None]],
) -> list[Issue]:
    issues: list[Issue] = []
    nonpositive: list[dict[str, Any]] = []
    intensity_out_of_range: list[dict[str, Any]] = []
    shape_out_of_range: list[dict[str, Any]] = []
    integrated_mismatches: list[dict[str, Any]] = []
    edge_touching: list[dict[str, Any]] = []

    for record, numeric in zip(object_records, object_numeric):
        label = _object_label(record)
        for column in ["area_px", "perimeter_px", "bbox_width", "bbox_height"]:
            value = numeric.get(column)
            if value is not None and value <= 0:
                nonpositive.append({"object": label, "column": column, "value": value})

        mean_intensity = numeric.get("mean_intensity")
        if mean_intensity is not None and not 0.0 <= mean_intensity <= 1.0:
            intensity_out_of_range.append({"object": label, "column": "mean_intensity", "value": mean_intensity})

        circularity = numeric.get("circularity")
        elongation = numeric.get("elongation")
        if circularity is not None and not 0.0 <= circularity <= 1.2:
            shape_out_of_range.append({"object": label, "column": "circularity", "value": circularity})
        if elongation is not None and elongation < 1.0:
            shape_out_of_range.append({"object": label, "column": "elongation", "value": elongation})

        area = numeric.get("area_px")
        integrated = numeric.get("integrated_intensity")
        if area is not None and mean_intensity is not None and integrated is not None:
            expected = area * mean_intensity
            if abs(integrated - expected) > max(1e-3, abs(expected) * 0.002):
                integrated_mismatches.append({"object": label, "reported": integrated, "computed": expected})

        bbox_x = numeric.get("bbox_x")
        bbox_y = numeric.get("bbox_y")
        if bbox_x == 0 or bbox_y == 0:
            edge_touching.append({"object": label})

    if nonpositive:
        issues.append(
            Issue(
                code="microtrace_nonpositive_object_measurements",
                severity="error",
                message="Some object measurements have non-positive geometry values.",
                recommendation="Review segmentation output; valid objects need positive area, perimeter, width, and height.",
                context={"examples": nonpositive[:20], "count": len(nonpositive)},
            )
        )
    if intensity_out_of_range:
        issues.append(
            Issue(
                code="microtrace_intensity_out_of_range",
                severity="warning",
                message="Some object mean intensities fall outside the expected normalized range [0, 1].",
                recommendation="Confirm image normalization and report provenance before comparing intensity metrics.",
                context={"examples": intensity_out_of_range[:20], "count": len(intensity_out_of_range)},
            )
        )
    if shape_out_of_range:
        issues.append(
            Issue(
                code="microtrace_shape_metric_out_of_range",
                severity="warning",
                message="Some object shape metrics fall outside expected ranges.",
                recommendation="Review segmentation masks and object measurement calculations.",
                context={"examples": shape_out_of_range[:20], "count": len(shape_out_of_range)},
            )
        )
    if integrated_mismatches:
        issues.append(
            Issue(
                code="microtrace_integrated_intensity_mismatch",
                severity="warning",
                message="Some integrated intensity values differ from area times mean intensity.",
                recommendation="Regenerate measurements or confirm the report uses a different intensity definition.",
                context={"examples": integrated_mismatches[:20], "count": len(integrated_mismatches)},
            )
        )
    if edge_touching:
        issues.append(
            Issue(
                code="microtrace_edge_touching_objects",
                severity="warning",
                message="Some segmented objects touch the top or left image boundary.",
                recommendation="Review overlays for truncated objects before interpreting object size distributions.",
                context={"examples": edge_touching[:20], "count": len(edge_touching)},
            )
        )
    return issues


def _condition_replication_checks(
    summary_records: list[dict[str, str]],
    *,
    min_images_per_condition: int,
) -> list[Issue]:
    conditions = Counter(record.get("condition", "") or "unlabeled" for record in summary_records)
    if not conditions:
        return []
    if len(summary_records) == 1:
        return [
            Issue(
                code="microtrace_single_image_report",
                severity="info",
                message="The MicroTrace report contains a single analyzed image.",
                recommendation="Use this as a technical report; add biological or technical replicates for comparisons.",
                context={"condition_counts": dict(conditions)},
            )
        ]
    low = {condition: count for condition, count in conditions.items() if count < min_images_per_condition}
    if len(conditions) > 1 and low:
        return [
            Issue(
                code="microtrace_low_condition_replication",
                severity="warning",
                message="Some MicroTrace conditions have fewer images than the configured minimum.",
                recommendation="Avoid over-interpreting condition-level morphology differences without replication.",
                context={"condition_counts": low, "min_images_per_condition": min_images_per_condition},
            )
        ]
    return []


def _statistics_checks(
    statistics_records: list[dict[str, str]],
    object_records: list[dict[str, str]],
    statistics_numeric: list[dict[str, float | None]],
) -> list[Issue]:
    issues: list[Issue] = []
    object_counts = Counter(record.get("condition", "") for record in object_records)
    object_counts["all"] = len(object_records)
    mismatches: list[dict[str, Any]] = []
    for record, numeric in zip(statistics_records, statistics_numeric):
        condition = record.get("condition", "")
        expected = object_counts.get(condition, 0)
        reported = _as_int(numeric.get("object_count"))
        if reported is not None and reported != expected:
            mismatches.append({"condition": condition, "statistics": reported, "objects": expected})
    if mismatches:
        issues.append(
            Issue(
                code="microtrace_statistics_count_mismatch",
                severity="warning",
                message="statistics.csv object counts do not match objects.csv.",
                recommendation="Regenerate the report or remove stale statistics.csv output.",
                context={"examples": mismatches[:20], "count": len(mismatches)},
            )
        )
    return issues


def _metrics(
    *,
    summary_records: list[dict[str, str]],
    object_records: list[dict[str, str]],
    parsed: dict[str, Any],
) -> dict[str, Any]:
    object_numeric = parsed["object_numeric"]
    areas = [row["area_px"] for row in object_numeric if row.get("area_px") is not None]
    intensities = [row["mean_intensity"] for row in object_numeric if row.get("mean_intensity") is not None]
    conditions = Counter(record.get("condition", "") or "unlabeled" for record in summary_records)
    edge_touching_count = sum(1 for row in object_numeric if row.get("bbox_x") == 0 or row.get("bbox_y") == 0)
    return {
        "microtrace_image_count": len(summary_records),
        "microtrace_object_count": len(object_records),
        "microtrace_condition_count": len(conditions),
        "microtrace_condition_counts": dict(sorted(conditions.items())),
        "microtrace_area_median_px": median(areas) if areas else 0,
        "microtrace_area_min_px": min(areas) if areas else 0,
        "microtrace_area_max_px": max(areas) if areas else 0,
        "microtrace_mean_intensity": _mean(intensities) or 0,
        "microtrace_edge_touching_object_count": edge_touching_count,
    }


def _parse_float(raw_value: str) -> float | None:
    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def _valid_numbers(
    objects: list[tuple[dict[str, str], dict[str, float | None]]],
    column: str,
) -> list[float]:
    return [numeric[column] for _, numeric in objects if numeric.get(column) is not None]


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _close(value: float | None, expected: float | None, *, abs_tol: float) -> bool:
    if value is None or expected is None:
        return True
    return abs(value - expected) <= abs_tol


def _as_int(value: float | None) -> int | None:
    if value is None:
        return None
    if not value.is_integer():
        return None
    return int(value)


def _object_label(record: dict[str, str]) -> str:
    return f"{record.get('image', '')}::{record.get('object_id', '')}"


def _table_code(table_name: str) -> str:
    return table_name.replace(".", "_")


def _sort_issues(issues: list[Issue]) -> list[Issue]:
    severity_rank = {"error": 0, "warning": 1, "info": 2}
    return sorted(issues, key=lambda issue: (severity_rank[issue.severity], issue.code))
