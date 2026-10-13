import csv
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from tse_pilot.duplicates import analyze_duplicate_expenses, write_duplicate_diagnostics


class DuplicateDiagnosticsTests(unittest.TestCase):
    def test_reports_primary_totals_exclusions_and_distinct_document_lines(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "pilot.sqlite"
            connection = sqlite3.connect(database)
            connection.executescript(
                """
                CREATE TABLE candidates (sq_candidate TEXT, uf TEXT);
                CREATE TABLE expenses (
                    sq_candidate TEXT, sq_expense TEXT, amount_centavos INTEGER,
                    row_signature TEXT, snapshot_id TEXT, source_archive TEXT,
                    source_member TEXT, source_row INTEGER
                );
                CREATE TABLE expense_duplicates (
                    sq_candidate TEXT, sq_expense TEXT, evidence_json TEXT
                );
                CREATE TABLE expense_dedup_exclusions (
                    snapshot_id TEXT, source_archive TEXT, source_member TEXT, source_row INTEGER,
                    row_signature TEXT, kept_source_archive TEXT, kept_source_member TEXT, kept_source_row INTEGER,
                    sq_candidate TEXT, sq_expense TEXT, amount_centavos INTEGER
                );
                """
            )
            connection.execute("INSERT INTO candidates VALUES ('1', 'SP')")
            connection.executemany(
                "INSERT INTO expenses VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    ("1", "10", 10000, "first", "snapshot", "accounts.zip", "expenses_SP.csv", 2),
                    ("1", "10", 5000, "different-item", "snapshot", "accounts.zip", "expenses_SP.csv", 4),
                ],
            )
            duplicate = {
                "amount_centavos": 10000,
                "source_member": "expenses_SP.csv",
                "source_row": 3,
                "duplicate_of": {"source_member": "expenses_SP.csv", "source_row": 2},
            }
            connection.execute(
                "INSERT INTO expense_duplicates VALUES (?, ?, ?)",
                ("1", "10", json.dumps(duplicate)),
            )
            connection.execute(
                "INSERT INTO expense_dedup_exclusions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ("snapshot", "accounts.zip", "expenses_SP.csv", 3, "exact", "accounts.zip", "expenses_SP.csv", 2, "1", "10", 10000),
            )
            source_fields = [f"field_{index:02}" for index in range(53)]
            field_definitions = ", ".join(f'"{field}" TEXT' for field in source_fields)
            connection.execute(
                f"CREATE TABLE expense_occurrences ({field_definitions}, _source_archive TEXT, _source_member TEXT, _source_row INTEGER, _row_signature TEXT)"
            )
            connection.executemany(
                f"INSERT INTO expense_occurrences VALUES ({', '.join('?' for _ in range(57))})",
                [(None,) * 57, (None,) * 57, (None,) * 57],
            )
            connection.commit()
            connection.close()

            report = analyze_duplicate_expenses(database)

            self.assertEqual(report["source_field_count"], 53)
            self.assertEqual(report["rows_before_deduplication"], 3)
            self.assertEqual(report["rows_after_deduplication"], 2)
            self.assertEqual(report["rows_excluded"], 1)
            self.assertEqual(report["affected_candidates"], 1)
            self.assertEqual(report["primary_deduplicated_total_centavos"], 15000)
            self.assertEqual(report["preserve_all_total_centavos"], 25000)
            self.assertEqual(report["financial_difference_centavos"], 10000)
            self.assertEqual(report["documents_with_multiple_distinct_lines"], 1)
            self.assertIn("not characterized as waste", report["interpretation"])
            output = Path(directory) / "reports" / "diagnostics.json"
            write_duplicate_diagnostics(database, output)
            with output.with_name("tse-2022-dedup-exclusions.csv").open(encoding="utf-8", newline="") as handle:
                excluded = list(csv.DictReader(handle))
            self.assertEqual(len(excluded), 1)
            self.assertEqual(excluded[0]["source_member"], "expenses_SP.csv")
            self.assertEqual(excluded[0]["source_row"], "3")
            self.assertEqual(excluded[0]["kept_source_row"], "2")


if __name__ == "__main__":
    unittest.main()
