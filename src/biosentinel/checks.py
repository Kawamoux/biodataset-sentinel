"""Audit checks for biological dataset preflight validation."""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from statistics import median
from typing import Any

from .io import duplicated_values
from .models import FeatureTable, Issue, MeasurementMatrix, SampleTable
from .privacy import scan_headers, scan_records


def run_checks(
    *,
    samples: SampleTable,
    matrix: MeasurementMatrix,
    features: FeatureTable | None = None,
    outcome_column: str | None = None,
    batch_column: str | None = None,
    allow_negative: bool = False,
    min_replicates: int = 3,
) -> tuple[list[Issue], dict[str, Any]]:
    issues: list[Issue] = []
    metrics: dict[str, Any] = {}

    issues.extend(_schema_checks(samples=samples, matrix=matrix, features=features))
    issues.extend(_alignment_checks(samples=samples, matrix=matrix, features=features))
    numeric_metrics, numeric_issues = _numeric_checks(matrix, allow_negative=allow_negative)
    signal_metrics, signal_issues = _signal_checks(matrix)

    issues.extend(numeric_issues)
    issues.extend(signal_issues)
    metrics.update(numeric_metrics)
    metrics.update(signal_metrics)

    if outcome_column:
        issues.extend(
            _outcome_checks(
                samples=samples,
                outcome_column=outcome_column,
                batch_column=batch_column,
                min_replicates=min_replicates,
            )
        )

    issues.extend(scan_headers(samples.headers, table_name="samples"))
    issues.extend(scan_records(samples.records, table_name="samples"))
    if features is not None:
        issues.extend(scan_headers(features.headers, table_name="features"))
        issues.extend(scan_records(features.records, table_name="features"))

    return _sort_issues(issues), metrics


def _schema_checks(
    *,
    samples: SampleTable,
    matrix: MeasurementMatrix,
    features: FeatureTable | None,
) -> list[Issue]:
    issues: list[Issue] = []

    issues.extend(_header_checks(samples.headers, table_name="samples", required=samples.id_column))
    issues.extend(
        _header_checks(
            matrix.headers,
            table_name="matrix",
            required=matrix.feature_id_column,
            required_position=0,
        )
    )
    if features is not None:
        issues.extend(_header_checks(features.headers, table_name="features", required=features.id_column))

    issues.extend(
        _identifier_checks(
            values=samples.sample_ids,
            table_name="samples",
            id_column=samples.id_column,
            code_prefix="sample",
        )
    )
    issues.extend(
        _identifier_checks(
            values=matrix.sample_ids,
            table_name="matrix columns",
            id_column="sample columns",
            code_prefix="matrix_sample",
        )
    )
    issues.extend(
        _identifier_checks(
            values=matrix.feature_ids,
            table_name="matrix rows",
            id_column=matrix.feature_id_column,
            code_prefix="feature",
        )
    )

    if features is not None:
        issues.extend(
            _identifier_checks(
                values=features.feature_ids,
                table_name="features",
                id_column=features.id_column,
                code_prefix="feature_table",
            )
        )

    if not matrix.sample_ids:
        issues.append(
            Issue(
                code="matrix_has_no_samples",
                severity="error",
                message="The measurement matrix has no sample columns.",
                recommendation="Provide one numeric column per sample after the feature identifier column.",
            )
        )
    if not matrix.feature_ids:
        issues.append(
            Issue(
                code="matrix_has_no_features",
                severity="error",
                message="The measurement matrix has no feature rows.",
                recommendation="Provide at least one measured feature.",
            )
        )

    return issues


def _header_checks(
    headers: list[str],
    *,
    table_name: str,
    required: str,
    required_position: int | None = None,
) -> list[Issue]:
    issues: list[Issue] = []
    if any(not header for header in headers):
        issues.append(
            Issue(
                code=f"{table_name}_empty_header",
                severity="error",
                message=f"{table_name} contains an empty column name.",
                recommendation="Rename empty columns before running downstream analyses.",
            )
        )

    duplicates = duplicated_values(headers)
    if duplicates:
        issues.append(
            Issue(
                code=f"{table_name}_duplicate_headers",
                severity="error",
                message=f"{table_name} contains duplicated column names.",
                recommendation="Make every column name unique so joins and filters are deterministic.",
                context={"duplicates": duplicates[:10]},
            )
        )

    if required not in headers:
        issues.append(
            Issue(
                code=f"{table_name}_missing_required_column",
                severity="error",
                message=f"{table_name} is missing required column {required}.",
                recommendation=f"Add a {required} column with stable identifiers.",
                context={"required": required},
            )
        )
    elif required_position is not None and headers[required_position] != required:
        issues.append(
            Issue(
                code=f"{table_name}_required_column_position",
                severity="error",
                message=f"{table_name} must use {required} as the first column.",
                recommendation=f"Move {required} to the first column of the matrix.",
                context={"expected": required, "found": headers[required_position]},
            )
        )

    return issues


def _identifier_checks(
    *,
    values: list[str],
    table_name: str,
    id_column: str,
    code_prefix: str,
) -> list[Issue]:
    issues: list[Issue] = []
    empty_count = sum(1 for value in values if not value)
    if empty_count:
        issues.append(
            Issue(
                code=f"{code_prefix}_empty_ids",
                severity="error",
                message=f"{table_name} contains empty identifiers.",
                recommendation=f"Fill every value in {id_column} with a stable, non-empty identifier.",
                context={"empty_count": empty_count},
            )
        )

    duplicates = duplicated_values([value for value in values if value])
    if duplicates:
        issues.append(
            Issue(
                code=f"{code_prefix}_duplicate_ids",
                severity="error",
                message=f"{table_name} contains duplicated identifiers.",
                recommendation="Deduplicate records before analysis; duplicated identifiers make joins ambiguous.",
                context={"duplicates": duplicates[:10]},
            )
        )
    return issues


def _alignment_checks(
    *,
    samples: SampleTable,
    matrix: MeasurementMatrix,
    features: FeatureTable | None,
) -> list[Issue]:
    issues: list[Issue] = []
    sample_ids = {value for value in samples.sample_ids if value}
    matrix_sample_ids = {value for value in matrix.sample_ids if value}

    missing_from_matrix = sorted(sample_ids - matrix_sample_ids)
    missing_from_samples = sorted(matrix_sample_ids - sample_ids)
    if missing_from_matrix:
        issues.append(
            Issue(
                code="samples_missing_from_matrix",
                severity="error",
                message="Some sample metadata rows are absent from the measurement matrix.",
                recommendation="Align sample metadata and matrix columns before analysis.",
                context={"sample_ids": missing_from_matrix[:20], "count": len(missing_from_matrix)},
            )
        )
    if missing_from_samples:
        issues.append(
            Issue(
                code="matrix_samples_missing_metadata",
                severity="error",
                message="Some matrix columns are absent from the sample metadata table.",
                recommendation="Add metadata rows for every matrix column or remove unmatched matrix columns.",
                context={"sample_ids": missing_from_samples[:20], "count": len(missing_from_samples)},
            )
        )

    if features is not None:
        feature_ids = {value for value in features.feature_ids if value}
        matrix_feature_ids = {value for value in matrix.feature_ids if value}
        missing_feature_annotations = sorted(matrix_feature_ids - feature_ids)
        unused_feature_annotations = sorted(feature_ids - matrix_feature_ids)
        if missing_feature_annotations:
            issues.append(
                Issue(
                    code="matrix_features_missing_annotations",
                    severity="warning",
                    message="Some matrix features are absent from the feature annotation table.",
                    recommendation="Add feature annotations or document why annotation is incomplete.",
                    context={"feature_ids": missing_feature_annotations[:20], "count": len(missing_feature_annotations)},
                )
            )
        if unused_feature_annotations:
            issues.append(
                Issue(
                    code="unused_feature_annotations",
                    severity="info",
                    message="Some feature annotations do not correspond to matrix rows.",
                    recommendation="Remove unused annotations if they are not part of the intended release.",
                    context={"feature_ids": unused_feature_annotations[:20], "count": len(unused_feature_annotations)},
                )
            )

    return issues


def _numeric_checks(matrix: MeasurementMatrix, *, allow_negative: bool) -> tuple[dict[str, Any], list[Issue]]:
    issues: list[Issue] = []
    metrics: dict[str, Any] = {
        "cell_problem_count": len(matrix.cell_problems),
    }

    if matrix.cell_problems:
        counts = Counter(problem.problem for problem in matrix.cell_problems)
        issues.append(
            Issue(
                code="matrix_cell_parse_problems",
                severity="error",
                message="The measurement matrix contains missing, non-numeric, or non-finite values.",
                recommendation="Replace invalid cells with numeric values or remove affected rows and columns.",
                context={
                    "counts": dict(counts),
                    "examples": [problem.to_dict() for problem in matrix.cell_problems[:10]],
                },
            )
        )

    negative_examples: list[dict[str, Any]] = []
    negative_count = 0
    for feature_id, row in zip(matrix.feature_ids, matrix.values):
        for sample_id, value in zip(matrix.sample_ids, row):
            if value is not None and value < 0:
                negative_count += 1
                if len(negative_examples) < 10:
                    negative_examples.append({"feature_id": feature_id, "sample_id": sample_id, "value": value})

    metrics["negative_value_count"] = negative_count
    if negative_count and not allow_negative:
        issues.append(
            Issue(
                code="matrix_negative_values",
                severity="error",
                message="The measurement matrix contains negative values while negative values are disabled.",
                recommendation="Use non-negative counts or pass allow_negative=True for signed expression-like data.",
                context={"count": negative_count, "examples": negative_examples},
            )
        )

    return metrics, issues


def _signal_checks(matrix: MeasurementMatrix) -> tuple[dict[str, Any], list[Issue]]:
    issues: list[Issue] = []
    metrics: dict[str, Any] = {}

    numeric_values = [value for row in matrix.values for value in row if value is not None]
    zero_count = sum(1 for value in numeric_values if value == 0)
    zero_fraction = zero_count / len(numeric_values) if numeric_values else 0.0
    metrics["zero_fraction"] = round(zero_fraction, 6)

    sample_totals = _sample_totals(matrix)
    feature_totals = _feature_totals(matrix)
    metrics["sample_total_min"] = min(sample_totals.values()) if sample_totals else 0
    metrics["sample_total_median"] = median(sample_totals.values()) if sample_totals else 0
    metrics["sample_total_max"] = max(sample_totals.values()) if sample_totals else 0
    metrics["all_zero_feature_count"] = sum(1 for total in feature_totals.values() if total == 0)

    all_zero_samples = [sample_id for sample_id, total in sample_totals.items() if total == 0]
    if all_zero_samples:
        issues.append(
            Issue(
                code="all_zero_samples",
                severity="warning",
                message="Some samples have zero total signal across all features.",
                recommendation="Confirm whether these samples failed measurement or should be excluded.",
                context={"sample_ids": all_zero_samples[:20], "count": len(all_zero_samples)},
            )
        )

    all_zero_features = [feature_id for feature_id, total in feature_totals.items() if total == 0]
    if all_zero_features:
        issues.append(
            Issue(
                code="all_zero_features",
                severity="info",
                message="Some features have zero signal across all samples.",
                recommendation="Consider filtering all-zero features before downstream analysis.",
                context={"feature_ids": all_zero_features[:20], "count": len(all_zero_features)},
            )
        )

    constant_features = _constant_features(matrix)
    metrics["constant_feature_count"] = len(constant_features)
    if constant_features:
        issues.append(
            Issue(
                code="constant_features",
                severity="info",
                message="Some features are constant across all samples.",
                recommendation="Consider filtering constant features before modeling or clustering.",
                context={"feature_ids": constant_features[:20], "count": len(constant_features)},
            )
        )

    if zero_fraction >= 0.95 and numeric_values:
        issues.append(
            Issue(
                code="very_sparse_matrix",
                severity="warning",
                message="The matrix is more than 95% zero.",
                recommendation="Confirm that the matrix type and filtering strategy match the intended analysis.",
                context={"zero_fraction": round(zero_fraction, 6)},
            )
        )

    outliers = _library_size_outliers(sample_totals)
    if outliers:
        issues.append(
            Issue(
                code="sample_total_outliers",
                severity="warning",
                message="Some samples have atypical total signal compared with the cohort.",
                recommendation="Review library size, acquisition quality, or normalization assumptions for these samples.",
                context={"sample_ids": outliers[:20], "count": len(outliers)},
            )
        )

    return metrics, issues


def _outcome_checks(
    *,
    samples: SampleTable,
    outcome_column: str,
    batch_column: str | None,
    min_replicates: int,
) -> list[Issue]:
    issues: list[Issue] = []
    if outcome_column not in samples.headers:
        return [
            Issue(
                code="outcome_column_missing",
                severity="error",
                message=f"Outcome column {outcome_column} is absent from the sample table.",
                recommendation="Use an existing sample metadata column or add the intended outcome column.",
                context={"outcome_column": outcome_column},
            )
        ]

    outcome_values = [record.get(outcome_column, "") for record in samples.records]
    missing_outcome_count = sum(1 for value in outcome_values if not value)
    if missing_outcome_count:
        issues.append(
            Issue(
                code="missing_outcome_values",
                severity="error",
                message="Some samples have empty outcome values.",
                recommendation="Fill or exclude samples with missing outcome labels before supervised analysis.",
                context={"count": missing_outcome_count},
            )
        )

    counts = Counter(value for value in outcome_values if value)
    small_groups = {group: count for group, count in counts.items() if count < min_replicates}
    if small_groups:
        issues.append(
            Issue(
                code="low_replicate_groups",
                severity="warning",
                message="Some outcome groups have fewer replicates than the configured minimum.",
                recommendation="Review statistical power and avoid over-interpreting under-replicated contrasts.",
                context={"groups": small_groups, "min_replicates": min_replicates},
            )
        )

    if len(counts) < 2 and counts:
        issues.append(
            Issue(
                code="single_outcome_group",
                severity="warning",
                message="Only one non-empty outcome group is present.",
                recommendation="Confirm that the dataset is intended for quality review rather than comparative analysis.",
            )
        )

    if batch_column:
        issues.extend(_batch_confounding_checks(samples, outcome_column=outcome_column, batch_column=batch_column))

    issues.extend(_label_leakage_checks(samples, outcome_column=outcome_column, batch_column=batch_column))
    return issues


def _batch_confounding_checks(
    samples: SampleTable,
    *,
    outcome_column: str,
    batch_column: str,
) -> list[Issue]:
    if batch_column not in samples.headers:
        return [
            Issue(
                code="batch_column_missing",
                severity="error",
                message=f"Batch column {batch_column} is absent from the sample table.",
                recommendation="Use an existing batch column or remove the batch-column option.",
                context={"batch_column": batch_column},
            )
        ]

    pairs = [
        (record.get(outcome_column, ""), record.get(batch_column, ""))
        for record in samples.records
        if record.get(outcome_column, "") and record.get(batch_column, "")
    ]
    association = _cramers_v(pairs)
    if association >= 0.85 and len(pairs) >= 4:
        return [
            Issue(
                code="batch_outcome_confounding",
                severity="warning",
                message="Batch and outcome are strongly associated.",
                recommendation=(
                    "Review the experimental design before attributing differences to biology. "
                    "Consider balanced designs, blocking, or explicit batch-aware models."
                ),
                context={"cramers_v": round(association, 4), "complete_pairs": len(pairs)},
            )
        ]
    return []


def _label_leakage_checks(
    samples: SampleTable,
    *,
    outcome_column: str,
    batch_column: str | None,
) -> list[Issue]:
    outcome_values = [record.get(outcome_column, "") for record in samples.records]
    unique_outcomes = {value for value in outcome_values if value}
    if len(unique_outcomes) < 2:
        return []

    suspicious_columns: list[str] = []
    excluded = {samples.id_column, outcome_column}
    if batch_column:
        excluded.add(batch_column)

    for column in samples.headers:
        if column in excluded:
            continue
        values = [record.get(column, "") for record in samples.records]
        unique_values = {value for value in values if value}
        if len(unique_values) < 2 or len(unique_values) > max(4, len(unique_outcomes) * 2):
            continue
        if _perfectly_predicts(values, outcome_values):
            suspicious_columns.append(column)

    if not suspicious_columns:
        return []

    return [
        Issue(
            code="possible_label_leakage",
            severity="warning",
            message="Some metadata columns perfectly predict the outcome.",
            recommendation=(
                "Confirm these columns are legitimate design variables and not derived labels "
                "that could leak target information into models."
            ),
            context={"columns": suspicious_columns[:20], "count": len(suspicious_columns)},
        )
    ]


def _sample_totals(matrix: MeasurementMatrix) -> dict[str, float]:
    totals = {sample_id: 0.0 for sample_id in matrix.sample_ids}
    for row in matrix.values:
        for sample_id, value in zip(matrix.sample_ids, row):
            if value is not None:
                totals[sample_id] += value
    return totals


def _feature_totals(matrix: MeasurementMatrix) -> dict[str, float]:
    totals: dict[str, float] = {}
    for feature_id, row in zip(matrix.feature_ids, matrix.values):
        totals[feature_id] = sum(value for value in row if value is not None)
    return totals


def _constant_features(matrix: MeasurementMatrix) -> list[str]:
    constant: list[str] = []
    for feature_id, row in zip(matrix.feature_ids, matrix.values):
        values = [value for value in row if value is not None]
        if values and len(set(values)) == 1:
            constant.append(feature_id)
    return constant


def _library_size_outliers(sample_totals: dict[str, float]) -> list[str]:
    if len(sample_totals) < 4:
        return []
    values = list(sample_totals.values())
    med = median(values)
    deviations = [abs(value - med) for value in values]
    mad = median(deviations)
    if mad == 0:
        return [sample_id for sample_id, value in sample_totals.items() if value != med]
    scale = 1.4826 * mad
    return [sample_id for sample_id, value in sample_totals.items() if abs(value - med) / scale > 6]


def _cramers_v(pairs: list[tuple[str, str]]) -> float:
    if not pairs:
        return 0.0
    rows = sorted({left for left, _ in pairs})
    cols = sorted({right for _, right in pairs})
    if len(rows) < 2 or len(cols) < 2:
        return 0.0

    table: dict[str, dict[str, int]] = {row: {col: 0 for col in cols} for row in rows}
    for left, right in pairs:
        table[left][right] += 1

    row_totals = {row: sum(table[row].values()) for row in rows}
    col_totals = {col: sum(table[row][col] for row in rows) for col in cols}
    n = len(pairs)
    chi_square = 0.0
    for row in rows:
        for col in cols:
            expected = row_totals[row] * col_totals[col] / n
            if expected:
                chi_square += (table[row][col] - expected) ** 2 / expected

    denominator = n * (min(len(rows) - 1, len(cols) - 1))
    return math.sqrt(chi_square / denominator) if denominator else 0.0


def _perfectly_predicts(values: list[str], outcome_values: list[str]) -> bool:
    mapping: dict[str, set[str]] = defaultdict(set)
    for value, outcome in zip(values, outcome_values):
        if value and outcome:
            mapping[value].add(outcome)
    if not mapping:
        return False
    predicted_outcomes = set().union(*mapping.values())
    return all(len(outcomes) == 1 for outcomes in mapping.values()) and len(predicted_outcomes) > 1


def _sort_issues(issues: list[Issue]) -> list[Issue]:
    severity_rank = {"error": 0, "warning": 1, "info": 2}
    return sorted(issues, key=lambda issue: (severity_rank[issue.severity], issue.code))
