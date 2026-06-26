from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from biosentinel.cli import main


class CliTests(unittest.TestCase):
    def test_cli_writes_reports(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            samples = root / "samples.csv"
            matrix = root / "matrix.csv"
            json_report = root / "report.json"
            html_report = root / "report.html"
            samples.write_text(
                "sample_id,condition,batch\nS01,control,B1\nS02,treated,B1\n",
                encoding="utf-8",
            )
            matrix.write_text("feature_id,S01,S02\ngene_001,1,2\n", encoding="utf-8")

            exit_code = main(
                [
                    "audit",
                    "--samples",
                    str(samples),
                    "--matrix",
                    str(matrix),
                    "--outcome-column",
                    "condition",
                    "--batch-column",
                    "batch",
                    "--json-report",
                    str(json_report),
                    "--html-report",
                    str(html_report),
                    "--fail-on",
                    "never",
                ]
            )

            payload = json.loads(json_report.read_text(encoding="utf-8"))
            html = html_report.read_text(encoding="utf-8")

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["summary"]["sample_count"], 2)
        self.assertIn("BioDataset Sentinel Report", html)

    def test_cli_fails_on_parse_error(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            samples = root / "samples.csv"
            matrix = root / "matrix.csv"
            samples.write_text("sample_id,condition\nS01,control\n", encoding="utf-8")
            matrix.write_text("feature_id,S01\ngene_001,not_numeric\n", encoding="utf-8")

            exit_code = main(["audit", "--samples", str(samples), "--matrix", str(matrix)])

        self.assertEqual(exit_code, 1)


if __name__ == "__main__":
    unittest.main()
