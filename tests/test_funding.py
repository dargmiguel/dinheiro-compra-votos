from __future__ import annotations

import csv
import json
import sqlite3
import tempfile
import unittest
import zipfile
from pathlib import Path

from tse_pilot.funding import write_funding_source_analysis


class FundingSourceAnalysisTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.database = root / "funding.sqlite"
        self.archive = root / "accounts.zip"
        self.output = root / "reports"
        connection = sqlite3.connect(self.database)
        connection.executescript(
            """
            CREATE TABLE candidates (
                sq_candidate TEXT, election_year INTEGER, turn INTEGER,
                cargo_code TEXT, candidate_status_code TEXT, uf TEXT,
                candidate_number TEXT, candidate_name TEXT, party_abbrev TEXT
            );
            CREATE TABLE expense_occurrences (
                SQ_CANDIDATO TEXT, SQ_PRESTADOR_CONTAS TEXT,
                TP_PRESTACAO_CONTAS TEXT, _source_archive TEXT,
                _source_member TEXT, _source_row INTEGER
            );
            CREATE TABLE expenses (
                sq_candidate TEXT, amount_centavos INTEGER, source_archive TEXT,
                source_member TEXT, source_row INTEGER
            );
            """
        )
        connection.executemany(
            "INSERT INTO candidates VALUES (?, 2022, 1, '6', ?, ?, ?, ?, ?)",
            [
                ("A", "12", "SP", "10", "Candidata A", "P1"),
                ("B", "3", "SP", "11", "Candidato B", "P1"),
                ("C", "12", "RJ", "12", "Candidato C", "P2"),
                ("D", "12", "RJ", "13", "Candidato D", "P2"),
            ],
        )
        occurrences = [
            ("A", "501", "Final", "accounts.zip", "expenses_SP.csv", 2),
            ("B", "502", "Final", "accounts.zip", "expenses_SP.csv", 3),
            ("C", "503", "Final", "accounts.zip", "expenses_RJ.csv", 2),
            ("D", "504", "Parcial", "accounts.zip", "expenses_RJ.csv", 3),
        ]
        connection.executemany(
            "INSERT INTO expense_occurrences VALUES (?, ?, ?, ?, ?, ?)", occurrences
        )
        connection.executemany(
            "INSERT INTO expenses VALUES (?, ?, ?, ?, ?)",
            [
                ("A", 10000, "accounts.zip", "expenses_SP.csv", 2),
                ("B", 20000, "accounts.zip", "expenses_SP.csv", 3),
                ("C", 20000, "accounts.zip", "expenses_RJ.csv", 2),
                ("D", 30000, "accounts.zip", "expenses_RJ.csv", 3),
            ],
        )
        connection.commit()
        connection.close()

        receipt_fields = [
            "AA_ELEICAO", "ST_TURNO", "TP_PRESTACAO_CONTAS", "CD_CARGO",
            "SQ_CANDIDATO", "SQ_PRESTADOR_CONTAS", "CD_FONTE_RECEITA",
            "DS_FONTE_RECEITA", "CD_NATUREZA_RECEITA", "DS_NATUREZA_RECEITA",
            "VR_RECEITA",
        ]
        paid_fields = [
            "AA_ELEICAO", "ST_TURNO", "TP_PRESTACAO_CONTAS", "SQ_PRESTADOR_CONTAS",
            "CD_FONTE_DESPESA", "DS_FONTE_DESPESA", "CD_NATUREZA_DESPESA",
            "DS_NATUREZA_DESPESA", "VR_PAGTO_DESPESA",
        ]
        receipt_rows = [
            ["2022", "1", "FINAL", "6", "A", "501", "0", "FUNDO PARTIDARIO", "1", "FINANCEIRO", "100,00"],
            ["2022", "1", "FINAL", "6", "A", "501", "2", "FUNDO ESPECIAL", "0", "ESTIMAVEL", "10,00"],
            ["2022", "1", "FINAL", "6", "A", "501", "1", "OUTROS RECURSOS", "1", "FINANCEIRO", "20,00"],
            ["2022", "1", "FINAL", "6", "A", "501", "9", "NAO INFORMADO", "1", "FINANCEIRO", "5,00"],
            ["2022", "1", "FINAL", "6", "A", "501", "#NULO", "#NULO", "-1", "#NULO", "#NULO"],
            ["2022", "1", "PARCIAL", "6", "A", "501", "2", "FUNDO ESPECIAL", "1", "FINANCEIRO", "999,00"],
            ["2022", "1", "FINAL", "6", "A", "501", "1", "OUTROS RECURSOS", "1", "FINANCEIRO", "888,00"],
        ]
        receipt_rows[-1][4] = "B"
        paid_rows = [
            ["2022", "1", "Final", "501", "2", "Fundo Especial", "1", "Financeiro", "30,00"],
            ["2022", "1", "Final", "501", "1", "Outros Recursos", "1", "Financeiro", "10,00"],
            ["2022", "1", "Final", "501", "9", "Não informado", "1", "Financeiro", "3,00"],
            ["2022", "1", "Parcial", "501", "2", "Fundo Especial", "1", "Financeiro", "999,00"],
            ["2022", "1", "Final", "502", "2", "Fundo Especial", "1", "Financeiro", "888,00"],
        ]
        with zipfile.ZipFile(self.archive, "w", zipfile.ZIP_DEFLATED) as archive:
            for uf in (
                "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
                "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
                "RS", "RO", "RR", "SC", "SP", "SE", "TO",
            ):
                receipts = receipt_rows if uf == "SP" else []
                paid = paid_rows if uf == "SP" else []
                archive.writestr(
                    f"receitas_candidatos_2022_{uf}.csv",
                    self._csv_text(receipt_fields, receipts),
                )
                archive.writestr(
                    f"despesas_pagas_candidatos_2022_{uf}.csv",
                    self._csv_text(paid_fields, paid),
                )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def _csv_text(fields: list[str], rows: list[list[str]]) -> str:
        import io

        output = io.StringIO(newline="")
        writer = csv.writer(output, delimiter=";", quoting=csv.QUOTE_ALL)
        writer.writerow(fields)
        writer.writerows(rows)
        return output.getvalue()

    def test_classifies_public_private_unknown_and_payment_coverage(self) -> None:
        result = write_funding_source_analysis(self.database, self.archive, self.output)
        self.assertEqual(result["population"]["reference_candidates_with_final_expenses"], 2)
        self.assertEqual(result["coverage"]["receipts_candidates_with_rows"], 1)
        self.assertEqual(result["coverage"]["payments_candidates_with_rows"], 1)

        with (self.output / "tse-2022-funding-source-candidates.csv").open(
            encoding="utf-8", newline=""
        ) as handle:
            candidates = {row["sq_candidate"]: row for row in csv.DictReader(handle)}
        self.assertEqual(candidates["A"]["receipt_public_centavos"], "11000")
        self.assertEqual(candidates["A"]["receipt_private_centavos"], "2000")
        self.assertEqual(candidates["A"]["receipt_unclassified_centavos"], "500")
        self.assertEqual(candidates["A"]["receipt_amount_missing_rows"], "1")
        self.assertEqual(candidates["A"]["receipt_public_estimable_centavos"], "1000")
        self.assertEqual(candidates["A"]["payment_public_centavos"], "3000")
        self.assertEqual(candidates["A"]["payment_private_centavos"], "1000")
        self.assertEqual(candidates["A"]["payment_unclassified_centavos"], "300")
        self.assertEqual(candidates["C"]["receipt_has_rows"], "False")
        self.assertEqual(candidates["C"]["receipt_total_centavos"], "")
        with (self.output / "tse-2022-funding-source-dictionary.csv").open(
            encoding="utf-8", newline=""
        ) as handle:
            dictionary = list(csv.DictReader(handle))
        has_rows_type = next(
            row["type"] for row in dictionary
            if row["table"] == "tse-2022-funding-source-candidates.csv"
            and row["field"] == "receipt_has_rows"
        )
        self.assertEqual(has_rows_type, "boolean")

        with (self.output / "tse-2022-funding-source-summary.csv").open(
            encoding="utf-8", newline=""
        ) as handle:
            summary = list(csv.DictReader(handle))
        public_receipts = next(
            row for row in summary if row["flow"] == "receipts" and row["source_class"] == "public"
        )
        self.assertEqual(public_receipts["share_of_classified_flow_amount_pct"], "84.6154")
        self.assertEqual(public_receipts["classified_flow_amount_denominator_centavos"], "13000")
        self.assertEqual(public_receipts["all_flow_amount_denominator_centavos"], "13500")
        public_payments = next(
            row for row in summary if row["flow"] == "payments" and row["source_class"] == "public"
        )
        self.assertEqual(public_payments["share_of_classified_flow_amount_pct"], "75.0000")
        unknown_receipts = next(
            row for row in summary
            if row["flow"] == "receipts" and row["source_class"] == "unclassified"
        )
        self.assertEqual(unknown_receipts["source_code_values"], "#NULO;9")
        self.assertEqual(unknown_receipts["amount_missing_rows"], "1")
        self.assertEqual(unknown_receipts["amount_centavos"], "500")

        recut = json.loads(
            (self.output / "tse-2022-funding-source-recut.json").read_text(encoding="utf-8")
        )
        self.assertEqual(recut["classification"]["public_source_codes"], ["0", "2"])
        self.assertEqual(recut["classification"]["private_source_codes"], ["1"])
        self.assertIn("9", recut["classification"]["unclassified_source_codes"])


if __name__ == "__main__":
    unittest.main()
