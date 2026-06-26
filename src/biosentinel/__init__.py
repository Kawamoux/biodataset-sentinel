"""Pre-analysis validation for biological datasets."""

__version__ = "0.2.0"

try:
    from .audit import audit_dataset
    from .microtrace import audit_microtrace_report
    from .models import AuditReport, AuditSummary, Issue
except ImportError:  # pragma: no cover - keeps package metadata importable during builds
    audit_dataset = None  # type: ignore[assignment]
    audit_microtrace_report = None  # type: ignore[assignment]
    AuditReport = None  # type: ignore[assignment]
    AuditSummary = None  # type: ignore[assignment]
    Issue = None  # type: ignore[assignment]

__all__ = [
    "__version__",
    "audit_dataset",
    "audit_microtrace_report",
    "AuditReport",
    "AuditSummary",
    "Issue",
]
