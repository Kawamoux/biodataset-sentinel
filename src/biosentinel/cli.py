"""Command-line interface for BioDataset Sentinel."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from .audit import audit_dataset
from .io import DataFormatError
from .report import write_html_report, write_json_report


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "audit":
        return _audit_command(args)
    parser.print_help()
    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="biosentinel",
        description="Pre-analysis quality control for biological datasets.",
    )
    subparsers = parser.add_subparsers(dest="command")

    audit = subparsers.add_parser("audit", help="audit sample metadata and a measurement matrix")
    audit.add_argument("--samples", required=True, help="sample metadata CSV/TSV")
    audit.add_argument("--matrix", required=True, help="measurement matrix CSV/TSV")
    audit.add_argument("--features", help="optional feature annotation CSV/TSV")
    audit.add_argument("--dataset-name", default="dataset", help="dataset label stored in reports")
    audit.add_argument("--sample-id-column", default="sample_id", help="sample identifier column")
    audit.add_argument("--feature-id-column", default="feature_id", help="feature identifier column")
    audit.add_argument("--outcome-column", help="sample metadata column describing the biological outcome")
    audit.add_argument("--batch-column", help="sample metadata column describing technical or experimental batches")
    audit.add_argument("--min-replicates", type=int, default=3, help="minimum samples expected per outcome group")
    audit.add_argument("--allow-negative", action="store_true", help="allow signed matrix values")
    audit.add_argument("--json-report", help="write a machine-readable JSON report")
    audit.add_argument("--html-report", help="write a human-readable HTML report")
    audit.add_argument(
        "--fail-on",
        choices=["error", "warning", "never"],
        default="error",
        help="control the process exit code threshold",
    )
    return parser


def _audit_command(args: argparse.Namespace) -> int:
    try:
        report = audit_dataset(
            samples_path=args.samples,
            matrix_path=args.matrix,
            features_path=args.features,
            dataset_name=args.dataset_name,
            sample_id_column=args.sample_id_column,
            feature_id_column=args.feature_id_column,
            outcome_column=args.outcome_column,
            batch_column=args.batch_column,
            allow_negative=args.allow_negative,
            min_replicates=args.min_replicates,
        )
    except FileNotFoundError:
        print("Input file not found. Check the provided file arguments.", file=sys.stderr)
        return 2
    except PermissionError:
        print("Input file could not be read because permissions were denied.", file=sys.stderr)
        return 2
    except (OSError, DataFormatError) as exc:
        print(f"Input could not be parsed: {exc}", file=sys.stderr)
        return 2

    if args.json_report:
        write_json_report(report, Path(args.json_report))
    if args.html_report:
        write_html_report(report, Path(args.html_report))

    counts = report.summary.issue_counts
    print(
        "BioDataset Sentinel: "
        f"{report.summary.status} "
        f"({counts['error']} errors, {counts['warning']} warnings, {counts['info']} info)"
    )

    return _exit_code(report.summary.issue_counts, fail_on=args.fail_on)


def _exit_code(issue_counts: dict[str, int], *, fail_on: str) -> int:
    if fail_on == "never":
        return 0
    if fail_on == "warning":
        return 1 if issue_counts["error"] or issue_counts["warning"] else 0
    return 1 if issue_counts["error"] else 0
