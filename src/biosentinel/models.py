"""Shared data structures for dataset audits."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

Severity = Literal["error", "warning", "info"]


@dataclass(frozen=True)
class Issue:
    """A structured audit finding."""

    code: str
    severity: Severity
    message: str
    recommendation: str
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "recommendation": self.recommendation,
            "context": self.context,
        }


@dataclass(frozen=True)
class AuditSummary:
    """High-level status and dimensions of an audit."""

    status: Literal["pass", "review", "fail"]
    sample_count: int
    feature_count: int
    measurement_count: int
    issue_counts: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "sample_count": self.sample_count,
            "feature_count": self.feature_count,
            "measurement_count": self.measurement_count,
            "issue_counts": dict(self.issue_counts),
        }


@dataclass(frozen=True)
class AuditReport:
    """Complete audit result."""

    dataset_name: str
    created_at_utc: str
    summary: AuditSummary
    issues: list[Issue]
    metrics: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def build(
        cls,
        *,
        dataset_name: str,
        sample_count: int,
        feature_count: int,
        measurement_count: int,
        issues: list[Issue],
        metrics: dict[str, Any] | None = None,
    ) -> "AuditReport":
        issue_counts = count_issues(issues)
        if issue_counts["error"] > 0:
            status: Literal["pass", "review", "fail"] = "fail"
        elif issue_counts["warning"] > 0:
            status = "review"
        else:
            status = "pass"

        return cls(
            dataset_name=dataset_name,
            created_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            summary=AuditSummary(
                status=status,
                sample_count=sample_count,
                feature_count=feature_count,
                measurement_count=measurement_count,
                issue_counts=issue_counts,
            ),
            issues=issues,
            metrics=metrics or {},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_name": self.dataset_name,
            "created_at_utc": self.created_at_utc,
            "summary": self.summary.to_dict(),
            "issues": [issue.to_dict() for issue in self.issues],
            "metrics": self.metrics,
        }


@dataclass(frozen=True)
class SampleTable:
    headers: list[str]
    records: list[dict[str, str]]
    id_column: str

    @property
    def sample_ids(self) -> list[str]:
        return [record.get(self.id_column, "") for record in self.records]


@dataclass(frozen=True)
class FeatureTable:
    headers: list[str]
    records: list[dict[str, str]]
    id_column: str

    @property
    def feature_ids(self) -> list[str]:
        return [record.get(self.id_column, "") for record in self.records]


@dataclass(frozen=True)
class CellProblem:
    row_id: str
    column_id: str
    raw_value: str
    problem: Literal["missing", "non_numeric", "non_finite"]

    def to_dict(self) -> dict[str, str]:
        return {
            "row_id": self.row_id,
            "column_id": self.column_id,
            "raw_value": self.raw_value,
            "problem": self.problem,
        }


@dataclass(frozen=True)
class MeasurementMatrix:
    headers: list[str]
    feature_ids: list[str]
    sample_ids: list[str]
    values: list[list[float | None]]
    cell_problems: list[CellProblem]
    feature_id_column: str

    @property
    def measurement_count(self) -> int:
        return len(self.feature_ids) * len(self.sample_ids)


class DataFormatError(ValueError):
    """Raised when a file cannot be interpreted as a delimited table."""


def count_issues(issues: list[Issue]) -> dict[str, int]:
    counts = {"error": 0, "warning": 0, "info": 0}
    for issue in issues:
        counts[issue.severity] += 1
    return counts
