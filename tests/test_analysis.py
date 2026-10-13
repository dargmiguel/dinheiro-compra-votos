from __future__ import annotations

import csv
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from tse_pilot.analysis import run_financial_analysis


class FinancialAnalysisTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.database = root / "pilot.sqlite"
        self.validation = root / "validation.json"
        self.output = root / "reports"
        self.validation.write_text(
            json.dumps({
                "status": "approved",
                "manifest_id": "snapshot-test",
                "vote_denominator": {"uf_count": 27},
                "fatal_counts": {"invalid_fields": 0},
                "source_details": {
                    "accounts_2022": {
                        "selected_members": ["despesas_contratadas.csv"],
                        "excluded_aggregate_or_document_members": ["despesas_pagas_candidatos_2022_SP.csv"],
                    },
                },
            }),
            encoding="utf-8",
        )
        self._create_database()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _create_database(self) -> None:
        connection = sqlite3.connect(self.database)
        connection.executescript(
            """
            CREATE TABLE candidates (
                sq_candidate TEXT PRIMARY KEY, election_year INTEGER, turn INTEGER,
                uf TEXT, cargo_code TEXT, candidate_status_code TEXT,
                party_code TEXT, birth_date TEXT, gender TEXT, race TEXT, schooling TEXT,
                marital_status TEXT, occupation TEXT
            );
            CREATE TABLE vote_denominators (
                uf TEXT PRIMARY KEY, election_year INTEGER, turn INTEGER, cargo_code TEXT, cargo TEXT,
                valid_nominal_votes INTEGER, valid_legend_votes INTEGER, valid_votes_total INTEGER,
                source_row_count INTEGER, source_archive TEXT, source_member TEXT
            );
            CREATE TABLE votes (sq_candidate TEXT, valid_votes INTEGER);
            CREATE TABLE expense_occurrences (
                SQ_CANDIDATO TEXT, SQ_DESPESA TEXT, TP_PRESTACAO_CONTAS TEXT,
                VR_DESPESA_CONTRATADA TEXT, _source_archive TEXT,
                _source_member TEXT, _source_row INTEGER
            );
            CREATE TABLE expenses (
                sq_candidate TEXT, sq_expense TEXT, amount_centavos INTEGER,
                row_signature TEXT, snapshot_id TEXT, source_archive TEXT,
                source_member TEXT, source_row INTEGER
            );
            CREATE TABLE expense_dedup_exclusions (
                snapshot_id TEXT, source_archive TEXT, source_member TEXT, source_row INTEGER,
                row_signature TEXT, kept_source_archive TEXT, kept_source_member TEXT, kept_source_row INTEGER,
                sq_candidate TEXT, sq_expense TEXT, amount_centavos INTEGER
            );
            """
        )
        ufs = ("AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO")
        connection.executemany(
            "INSERT INTO vote_denominators VALUES (?, 2022, 1, '6', 'Deputado Federal', 90000, 10000, 100000, 1, 'votes.zip', 'national.csv')",
            [(uf,) for uf in ufs],
        )
        occurrence_rows = []
        deduplicated_rows = []
        for index in range(48):
            candidate = f"A{index:03d}"
            uf = "SP" if (index // 4) % 2 == 0 else "RJ"
            gender = "FEMININO" if index % 5 < 2 else "MASCULINO"
            if index == 3:
                gender = "NÃO INFORMADO"
            party = f"P{index % 4}"
            birth = None if index == 4 else f"{1 + index % 12:02d}/01/{1970 + index % 20}"
            race = ("BRANCA", "PARDA", "PRETA")[index % 3]
            schooling = ("MÉDIO", "SUPERIOR", "FUNDAMENTAL")[(index // 3) % 3]
            connection.execute(
                "INSERT INTO candidates VALUES (?, 2022, 1, ?, '6', '12', ?, ?, ?, ?, ?, 'SOLTEIRO', 'PROFESSOR')",
                (candidate, uf, party, birth, gender, race, schooling),
            )
            votes = (index * 1877 + (index % 5) * 2911) % 1200
            connection.execute("INSERT INTO votes VALUES (?, ?)", (candidate, votes))
            if index == 2:
                occurrence_rows.append((candidate, "DOC-NONFINAL", "Parcial", "9000,00", "src.zip", "expenses.csv", 100 + index))
                deduplicated_rows.append((candidate, "DOC-NONFINAL", 900000, "signature", "snapshot-test", "src.zip", "expenses.csv", 100 + index))
                continue
            amount = 0 if index == 0 else 10000 + index * 250
            row = (candidate, f"DOC-{index}", "Final", f"{amount / 100:.2f}".replace(".", ","), "src.zip", "expenses.csv", 10 + index)
            occurrence_rows.append(row)
            deduplicated_rows.append((candidate, row[1], amount, "signature", "snapshot-test", "src.zip", "expenses.csv", 10 + index))
            if index == 1:
                occurrence_rows.append((*row[:6], 1000))
            if index == 0:
                occurrence_rows.append((candidate, "DOC-0-PARTIAL", "Parcial", "50000,00", "src.zip", "expenses.csv", 200))
                deduplicated_rows.append((candidate, "DOC-0-PARTIAL", 5000000, "signature", "snapshot-test", "src.zip", "expenses.csv", 200))
        for index, submission_type, amount in ((48, "Parcial", "15,00"), (49, "Final", "0,00")):
            candidate = f"I{index:03d}"
            connection.execute(
                "INSERT INTO candidates VALUES (?, 2022, 1, 'SP', '6', '3', 'P1', '01/01/1970', ?, 'PARDA', 'MÉDIO', 'SOLTEIRO', 'PROFESSOR')",
                (candidate, "FEMININO" if index == 48 else "MASCULINO"),
            )
            occurrence_rows.append((candidate, f"DOC-{candidate}", submission_type, amount, "src.zip", "expenses.csv", 300 + index))
            deduplicated_rows.append((candidate, f"DOC-{candidate}", 1500 if index == 48 else 0, "signature", "snapshot-test", "src.zip", "expenses.csv", 300 + index))
        connection.executemany(
            "INSERT INTO expense_occurrences VALUES (?, ?, ?, ?, ?, ?, ?)", occurrence_rows
        )
        connection.executemany("INSERT INTO expenses VALUES (?, ?, ?, ?, ?, ?, ?, ?)", deduplicated_rows)
        connection.execute(
            "INSERT INTO expense_dedup_exclusions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("snapshot-test", "src.zip", "expenses.csv", 1000, "signature", "src.zip", "expenses.csv", 11, "A001", "DOC-1", 10250),
        )
        connection.commit()
        connection.close()

    def test_runs_approved_population_sensitivities_controls_interaction_and_inapto_separately(self) -> None:
        result = run_financial_analysis(self.database, self.validation, self.output)

        self.assertEqual(result["manifest_id"], "snapshot-test")
        self.assertEqual(result["population"]["apto_candidates"], 48)
        self.assertEqual(result["population"]["inapto_candidates"], 2)
        expected_total = sum(0 if index in (0, 2) else 10000 + index * 250 for index in range(48))
        self.assertEqual(result["expense_scenarios"]["deduplicado"]["total_centavos"], expected_total)
        self.assertEqual(result["expense_scenarios"]["todas_as_linhas"]["total_centavos"], expected_total + 10250)
        self.assertEqual(result["expense_scenarios"]["deduplicado"]["observed_zero_candidates"], 1)
        self.assertEqual(result["expense_sensitivity_difference_centavos"], 10250)
        self.assertEqual(result["model_exclusion_reasons"]["apto_without_final_expense"], 1)
        self.assertEqual(result["model_exclusion_reasons"]["apto_with_missing_controls"], 1)
        self.assertEqual(sum(result["missing_controls_by_field"].values()), 1)
        self.assertEqual(result["missing_controls_by_field"]["age_at_election"], 1)
        self.assertEqual(result["inapto_expense_survey"]["candidate_count"], 2)
        self.assertEqual(result["expense_scenarios"]["deduplicado"]["absent_candidates"], 1)
        self.assertEqual(result["official_nominal_votes_national_total"], 2430000)
        self.assertEqual(result["official_legend_votes_national_total"], 270000)
        self.assertEqual(result["official_valid_votes_national_total"], 2700000)
        self.assertEqual(result["pipeline_validation"]["fatal_count_total"], 0)
        with (self.output / "tse-2022-vote-denominator-by-uf.csv").open(encoding="utf-8", newline="") as handle:
            denominator_rows = list(csv.DictReader(handle))
        self.assertEqual(len(denominator_rows), 27)
        self.assertTrue(all(int(row["valid_nominal_votes"]) + int(row["valid_legend_votes"]) == int(row["valid_votes_total"]) for row in denominator_rows))
        model_names = {model["name"] for model in result["models"]}
        self.assertEqual(
            model_names,
            {
                "deduplicado_completo",
                "todas_as_linhas_completo",
                "deduplicado_uf_partido",
                "deduplicado_interacao_sexo",
                "todas_as_linhas_interacao_sexo",
                "deduplicado_ols_participacao",
                "deduplicado_votos_brutos_log1p",
            },
        )
        reduced_model = next(model for model in result["models"] if model["name"] == "deduplicado_uf_partido")
        self.assertEqual(reduced_model["controls"], ["UF", "partido"])
        full_model = next(model for model in result["models"] if model["name"] == "deduplicado_completo")
        self.assertEqual(full_model["n"], 46)
        self.assertEqual(reduced_model["n"], 47)
        self.assertTrue(all(model["converged"] for model in result["models"]))
        self.assertIn("expense_x_female", {row["term"] for row in result["coefficients"]})
        self.assertFalse(result["payment_integration"]["integrated_in_analysis_database"])
        self.assertIn("despesas_pagas_candidatos_2022_SP.csv", result["payment_integration"]["frozen_archive_payment_members"])
        self.assertIn("não bloqueia", result["payment_integration"]["status"])

        with (self.output / "tse-2022-apto-expenses-by-type.csv").open(encoding="utf-8", newline="") as handle:
            apto_rows = list(csv.DictReader(handle))
        apto_by_type = {row["tp_prestacao_contas"]: row for row in apto_rows}
        self.assertIn("Final", apto_by_type)
        self.assertIn("Parcial", apto_by_type)
        self.assertEqual(int(apto_by_type["Final"]["all_lines_occurrence_rows"]), 48)
        self.assertEqual(int(apto_by_type["Final"]["deduplicated_occurrence_rows"]), 47)
        self.assertEqual(int(apto_by_type["Final"]["excluded_occurrence_rows"]), 1)
        self.assertEqual(int(apto_by_type["Final"]["excluded_affected_candidates"]), 1)

        with (self.output / "tse-2022-inapto-expenses-by-type.csv").open(encoding="utf-8", newline="") as handle:
            inapto_rows = list(csv.DictReader(handle))
        by_type = {row["tp_prestacao_contas"]: row for row in inapto_rows}
        self.assertEqual(set(by_type), {"Final", "Parcial"})
        self.assertEqual(int(by_type["Final"]["candidates_without_rows"]), 1)
        self.assertEqual(int(by_type["Final"]["all_lines_declared_expense_centavos"]), 0)
        self.assertEqual(int(by_type["Parcial"]["all_lines_declared_expense_centavos"]), 1500)
        report = (self.output / "tse-2022-financial-analysis.md").read_text(encoding="utf-8")
        self.assertIn("associação, não causalidade", report)
        self.assertIn("pagamentos", report)
        self.assertIn("48/48 com denominador e votos observados", report)
        self.assertIn("primeiro turno de 2022", report)
        self.assertIn("modelo de comparação com ajuste apenas por UF/partido, sem idade, usa N=47", report)
        self.assertIn("Com ajuste somente por UF/partido, sem idade (N=47)", report)

    def test_refuses_unapproved_pipeline_validation(self) -> None:
        self.validation.write_text(json.dumps({"status": "blocked"}), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "approved"):
            run_financial_analysis(self.database, self.validation, self.output)
    def test_refuses_approved_validation_with_nonzero_fatal_counts(self) -> None:
        self.validation.write_text(
            json.dumps({
                "status": "approved",
                "manifest_id": "snapshot-test",
                "vote_denominator": {"uf_count": 27},
                "fatal_counts": {"invalid_fields": 1},
            }),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "fatais"):
            run_financial_analysis(self.database, self.validation, self.output)


if __name__ == "__main__":
    unittest.main()
