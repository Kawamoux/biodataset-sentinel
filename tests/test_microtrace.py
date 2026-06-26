from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from biosentinel import audit_microtrace_report
from biosentinel.cli import main


class MicroTraceAuditTests(unittest.TestCase):
    def test_valid_microtrace_report_passes(self) -> None:
        with TemporaryDirectory() as tmpdir:
            report_dir = Path(tmpdir)
            _write_microtrace_report(report_dir)

            report = audit_microtrace_report(report_dir, min_images_per_condition=1)

        self.assertEqual(report.summary.status, "pass")
        self.assertEqual(report.summary.sample_count, 2)
        self.assertEqual(report.metrics["microtrace_object_count"], 4)

    def test_object_count_mismatch_is_error(self) -> None:
        with TemporaryDirectory() as tmpdir:
            report_dir = Path(tmpdir)
            _write_microtrace_report(report_dir, first_object_count=3)

            report = audit_microtrace_report(report_dir, min_images_per_condition=1)

        self.assertEqual(report.summary.status, "fail")
        self.assertIn("microtrace_object_count_mismatch", {issue.code for issue in report.issues})

    def test_metatrace_alias_writes_report(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            report_dir = root / "microtrace"
            output = root / "audit.json"
            report_dir.mkdir()
            _write_microtrace_report(report_dir)

            exit_code = main(
                [
                    "audit-metatrace",
                    str(report_dir),
                    "--min-images-per-condition",
                    "1",
                    "--json-report",
                    str(output),
                ]
            )

            payload = output.read_text(encoding="utf-8")

        self.assertEqual(exit_code, 0)
        self.assertIn('"microtrace_object_count": 4', payload)

    def test_report_paths_are_not_stored(self) -> None:
        with TemporaryDirectory() as tmpdir:
            report_dir = Path(tmpdir)
            _write_microtrace_report(report_dir)

            report = audit_microtrace_report(report_dir, min_images_per_condition=1)

        self.assertNotIn(str(report_dir), str(report.to_dict()))

    def test_numeric_measurements_do_not_trigger_privacy_phone(self) -> None:
        with TemporaryDirectory() as tmpdir:
            report_dir = Path(tmpdir)
            _write_microtrace_report(report_dir)

            report = audit_microtrace_report(report_dir, min_images_per_condition=1)

        self.assertNotIn("privacy_phone", {issue.code for issue in report.issues})


def _write_microtrace_report(report_dir: Path, *, first_object_count: int = 2) -> None:
    report_dir.joinpath("summary.csv").write_text(
        "\n".join(
            [
                "image,condition,threshold,object_count,total_area_px,median_area_px,mean_circularity,mean_elongation,mean_intensity",
                f"img_a.png,control,0.5,{first_object_count},30,15.0,0.55,1.15,0.4",
                "img_b.png,treated,0.5,2,70,35.0,0.65,1.25,0.5",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    report_dir.joinpath("objects.csv").write_text(
        "\n".join(
            [
                "image,condition,object_id,area_px,perimeter_px,circularity,elongation,centroid_x,centroid_y,bbox_x,bbox_y,bbox_width,bbox_height,mean_intensity,integrated_intensity",
                "img_a.png,control,1,10,18,0.5,1.1,4,4,1,1,6,6,0.3,3.0",
                "img_a.png,control,2,20,24,0.6,1.2,12,12,8,8,7,7,0.5,10.0",
                "img_b.png,treated,1,30,30,0.6,1.2,8,8,2,2,8,8,0.4,12.0",
                "img_b.png,treated,2,40,36,0.7,1.3,18,18,12,12,9,9,0.6,24.0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    report_dir.joinpath("statistics.csv").write_text(
        "\n".join(
            [
                "condition,object_count,mean_area_px,median_area_px,mean_perimeter_px,mean_circularity,mean_elongation,mean_intensity,mean_integrated_intensity",
                "all,4,25.0,25.0,27.0,0.6,1.2,0.45,12.25",
                "control,2,15.0,15.0,21.0,0.55,1.15,0.4,6.5",
                "treated,2,35.0,35.0,33.0,0.65,1.25,0.5,18.0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    unittest.main()
