"""Public audit API."""

from __future__ import annotations

from pathlib import Path

from .checks import run_checks
from .io import read_feature_table, read_measurement_matrix, read_sample_table
from .models import AuditReport


def audit_dataset(
    *,
    samples_path: str | Path,
    matrix_path: str | Path,
    features_path: str | Path | None = None,
    dataset_name: str = "dataset",
    sample_id_column: str = "sample_id",
    feature_id_column: str = "feature_id",
    outcome_column: str | None = None,
    batch_column: str | None = None,
    allow_negative: bool = False,
    min_replicates: int = 3,
) -> AuditReport:
    """Audit a biological sample table and measurement matrix."""

    samples = read_sample_table(samples_path, id_column=sample_id_column)
    matrix = read_measurement_matrix(matrix_path, feature_id_column=feature_id_column)
    features = (
        read_feature_table(features_path, id_column=feature_id_column)
        if features_path is not None
        else None
    )

    issues, metrics = run_checks(
        samples=samples,
        matrix=matrix,
        features=features,
        outcome_column=outcome_column,
        batch_column=batch_column,
        allow_negative=allow_negative,
        min_replicates=min_replicates,
    )

    return AuditReport.build(
        dataset_name=dataset_name,
        sample_count=len(samples.sample_ids),
        feature_count=len(matrix.feature_ids),
        measurement_count=matrix.measurement_count,
        issues=issues,
        metrics=metrics,
    )
