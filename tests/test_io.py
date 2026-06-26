from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from biosentinel.io import read_measurement_matrix, read_sample_table


class ReaderTests(unittest.TestCase):
    def test_reads_sample_table(self) -> None:
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "samples.csv"
            path.write_text("sample_id,condition\nS01,control\nS02,treated\n", encoding="utf-8")

            table = read_sample_table(path)

        self.assertEqual(table.headers, ["sample_id", "condition"])
        self.assertEqual(table.sample_ids, ["S01", "S02"])
        self.assertEqual(table.records[1]["condition"], "treated")

    def test_reads_numeric_matrix_and_records_cell_problems(self) -> None:
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "matrix.csv"
            path.write_text("feature_id,S01,S02\ngene_001,4,bad\ngene_002,,7\n", encoding="utf-8")

            matrix = read_measurement_matrix(path)

        self.assertEqual(matrix.feature_ids, ["gene_001", "gene_002"])
        self.assertEqual(matrix.sample_ids, ["S01", "S02"])
        self.assertEqual(matrix.values[0][0], 4.0)
        self.assertEqual([problem.problem for problem in matrix.cell_problems], ["non_numeric", "missing"])


if __name__ == "__main__":
    unittest.main()
