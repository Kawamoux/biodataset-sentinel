"""Pre-analysis validation for biological datasets."""

__version__ = "0.1.0"

try:
    from .audit import audit_dataset
    from .models import AuditReport, AuditSummary, Issue
except ImportError:  # pragma: no cover - keeps package metadata importable during builds
    audit_dataset = None  # type: ignore[assignment]
    AuditReport = None  # type: ignore[assignment]
    AuditSummary = None  # type: ignore[assignment]
    Issue = None  # type: ignore[assignment]

__all__ = [
    "__version__",
    "audit_dataset",
    "AuditReport",
    "AuditSummary",
    "Issue",
]
