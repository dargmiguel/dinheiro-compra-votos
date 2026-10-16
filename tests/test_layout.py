import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from tse_pilot.layout import inspect_archive, inspect_text_sample


class LayoutInspectionTests(unittest.TestCase):
    def test_text_sample_detects_tse_semicolon_layout_and_encoding(self):
        sample = "NR_CANDIDATO;NM_CANDIDATO;DS_CARGO\n123;João;Deputado Federal\n".encode("latin-1")

        layout = inspect_text_sample(sample)

        self.assertEqual(layout["encoding"], "latin-1")
        self.assertEqual(layout["delimiter"], ";")
        self.assertEqual(layout["columns"], ["NR_CANDIDATO", "NM_CANDIDATO", "DS_CARGO"])
        self.assertEqual(layout["sample_rows"][0]["NM_CANDIDATO"], "João")

    def test_archive_report_lists_layout_without_loading_whole_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "source.zip"
            with zipfile.ZipFile(archive, "w") as handle:
                handle.writestr("leia-me.pdf", b"not a text table")
                handle.writestr("consulta_cand_2022_BRASIL.csv", "NR_CANDIDATO;NM_CANDIDATO\n1;A\n".encode("latin-1"))

            report = inspect_archive(archive)

        self.assertEqual(report["archive_name"], "source.zip")
        csv_member = next(item for item in report["members"] if item["name"].endswith(".csv"))
        self.assertEqual(csv_member["layout"]["delimiter"], ";")
        self.assertEqual(csv_member["layout"]["columns"], ["NR_CANDIDATO", "NM_CANDIDATO"])
        self.assertTrue(any(item["name"].endswith("leia-me.pdf") for item in report["members"]))


if __name__ == "__main__":
    unittest.main()
