from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from biosentinel import audit_dataset
from biosentinel.report import render_html_report


ROOT = Path(__file__).resolve().parents[1]


class AuditTests(unittest.TestCase):
    def test_synthetic_example_has_no_errors(self) -> None:
        report = audit_dataset(
            samples_path=ROOT / "examples" / "samples.csv",
            matrix_path=ROOT / "examples" / "counts.csv",
            features_path=ROOT / "examples" / "features.csv",
            outcome_column="condition",
            batch_column="batch",
        )

        self.assertEqual(report.summary.issue_counts["error"], 0)
        self.assertEqual(report.summary.status, "pass")
        self.assertGreater(report.summary.issue_counts["info"], 0)
        self.assertIn("zero_fraction", report.metrics)

    def test_misaligned_samples_are_errors(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            samples = root / "samples.csv"
            matrix = root / "matrix.csv"
            samples.write_text("sample_id,condition\nS01,control\nS02,treated\n", encoding="utf-8")
            matrix.write_text("feature_id,S01,S03\ngene_001,1,2\n", encoding="utf-8")

            report = audit_dataset(samples_path=samples, matrix_path=matrix, outcome_column="condition")

        codes = {issue.code for issue in report.issues}
        self.assertIn("samples_missing_from_matrix", codes)
        self.assertIn("matrix_samples_missing_metadata", codes)
        self.assertEqual(report.summary.status, "fail")

    def test_batch_confounding_is_reported(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            samples = root / "samples.csv"
            matrix = root / "matrix.csv"
            samples.write_text(
                "\n".join(
                    [
                        "sample_id,condition,batch",
                        "S01,control,B1",
                        "S02,control,B1",
                        "S03,treated,B2",
                        "S04,treated,B2",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            matrix.write_text("feature_id,S01,S02,S03,S04\ngene_001,1,1,4,4\n", encoding="utf-8")

            report = audit_dataset(
                samples_path=samples,
                matrix_path=matrix,
                outcome_column="condition",
                batch_column="batch",
                min_replicates=2,
            )

        self.assertIn("batch_outcome_confounding", {issue.code for issue in report.issues})

    def test_privacy_patterns_are_reported_without_storing_input_paths(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            samples = root / "samples.csv"
            matrix = root / "matrix.csv"
            samples.write_text(
                "sample_id,condition,contact\nS01,control,person@example.org\nS02,treated,none\n",
                encoding="utf-8",
            )
            matrix.write_text("feature_id,S01,S02\ngene_001,1,2\n", encoding="utf-8")

            report = audit_dataset(samples_path=samples, matrix_path=matrix, outcome_column="condition")

        report_text = str(report.to_dict())
        self.assertIn("privacy_email", {issue.code for issue in report.issues})
        self.assertNotIn(str(root), report_text)

    def test_html_report_escapes_context(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            samples = root / "samples.csv"
            matrix = root / "matrix.csv"
            samples.write_text("sample_id,condition\nS01,<control>\nS02,treated\n", encoding="utf-8")
            matrix.write_text("feature_id,S01,S02\ngene_001,1,bad\n", encoding="utf-8")

            report = audit_dataset(samples_path=samples, matrix_path=matrix, outcome_column="condition")
            html = render_html_report(report)

        self.assertIn("&lt;control&gt;", html)
        self.assertNotIn("<control>", html)


if __name__ == "__main__":
    unittest.main()
