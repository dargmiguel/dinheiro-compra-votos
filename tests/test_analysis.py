from __future__ import annotations

import csv
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

import math

import numpy as np
import pandas as pd

from tse_pilot.analysis import _build_race_curve, _fixed_expense_band, _fit_race_interaction, _race_curve_svg
from tse_pilot.analysis import run_financial_analysis
from tse_pilot.analysis import write_expense_temporal_analysis


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
                marital_status TEXT, occupation TEXT, candidate_total_status_code TEXT,
                candidate_total_status TEXT
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
                "INSERT INTO candidates VALUES (?, 2022, 1, ?, '6', '12', ?, ?, ?, ?, ?, 'SOLTEIRO', 'PROFESSOR', ?, ?)",
                (
                    candidate, uf, party, birth, gender, race, schooling,
                    ("2", "3", "4", "5")[(index * 7 + index // 3) % 4],
                    ("ELEITO POR QP", "ELEITO POR MÉDIA", "NÃO ELEITO", "SUPLENTE")[(index * 7 + index // 3) % 4],
                ),
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
                "INSERT INTO candidates VALUES (?, 2022, 1, 'SP', '6', '3', 'P1', '01/01/1970', ?, 'PARDA', 'MÉDIO', 'SOLTEIRO', 'PROFESSOR', '2', 'ELEITO POR QP')",
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
        secondary = result["secondary_election_analysis"]
        self.assertEqual(secondary["official_elected_codes"], {"2": "ELEITO POR QP", "3": "ELEITO POR MÉDIA"})
        self.assertEqual(secondary["official_not_elected_codes"], {"4": "NÃO ELEITO", "5": "SUPLENTE"})
        self.assertEqual({model["name"] for model in secondary["models"]}, {"eleicao_deduplicado", "eleicao_todas_as_linhas"})
        self.assertTrue(all("custo por voto" in model["excluded_predictors"] for model in secondary["models"]))
        self.assertEqual(sum(row["candidate_count"] for row in secondary["elected_share_by_uf_expense_band"]), secondary["eligible_complete_case_n"])
        self.assertTrue(all(0 <= row["elected_share"] <= 1 for row in secondary["elected_share_by_uf_expense_band"]))
        self.assertEqual(
            [_fixed_expense_band(value) for value in (0, 5_000_000, 5_000_001, 20_000_000, 20_000_001, 100_000_000, 100_000_001)],
            ["ate_50_mil", "ate_50_mil", "50_a_200_mil", "50_a_200_mil", "200_mil_a_1_milhao", "200_mil_a_1_milhao", "acima_1_milhao"],
        )
        fixed_band_summary = secondary["elected_share_by_fixed_expense_band_brazil_and_uf"]
        brazil_rows = [row for row in fixed_band_summary if row["geography_type"] == "BRASIL"]
        uf_rows = [row for row in fixed_band_summary if row["geography_type"] == "UF"]
        self.assertEqual(len(brazil_rows), 4)
        self.assertEqual(len(uf_rows), 8)
        self.assertEqual(sum(row["candidate_count"] for row in brazil_rows), secondary["eligible_complete_case_n"])
        self.assertEqual(sum(row["elected_count"] for row in brazil_rows), secondary["eligible_elected_n"])
        self.assertEqual(
            sum(row["candidate_count"] for row in fixed_band_summary if row["geography_type"] == "UF"),
            sum(row["candidate_count"] for row in brazil_rows),
        )
        with (self.output / "tse-2022-election-powerbi-candidates.csv").open(encoding="utf-8", newline="") as handle:
            candidate_export_rows = list(csv.DictReader(handle))
        self.assertEqual(len(candidate_export_rows), secondary["eligible_complete_case_n"])
        with (self.output / "tse-2022-election-powerbi-summary.csv").open(encoding="utf-8", newline="") as handle:
            powerbi_rows = list(csv.DictReader(handle))
        self.assertEqual(len(powerbi_rows), len(fixed_band_summary))
        self.assertEqual(
            sum(int(row["candidate_count"]) for row in powerbi_rows if row["geography_type"] == "BRASIL"),
            secondary["eligible_complete_case_n"],
        )
        expected_apto_elected = sum(
            ("2", "3", "4", "5")[(index * 7 + index // 3) % 4] in {"2", "3"}
            for index in range(48)
        )
        expected_complete_case_elected = expected_apto_elected - sum(
            ("2", "3", "4", "5")[(index * 7 + index // 3) % 4] in {"2", "3"}
            for index in (2, 4)
        )
        self.assertEqual(secondary["apto_elected_n"], expected_apto_elected)
        self.assertEqual(secondary["eligible_elected_n"], expected_complete_case_elected)
        self.assertFalse(result["payment_integration"]["integrated_in_analysis_database"])
        self.assertIn("despesas_pagas_candidatos_2022_SP.csv", result["payment_integration"]["frozen_archive_payment_members"])
        self.assertIn("não bloqueia", result["payment_integration"]["status"])
        predictions = result["prediction_tables"]
        scenario_points = predictions["scenario_comparison"]
        self.assertEqual(len(scenario_points), 3)
        for point in scenario_points:
            self.assertLessEqual(point["deduplicated_ci95_lower"], point["deduplicated_prediction"])
            self.assertLessEqual(point["deduplicated_prediction"], point["deduplicated_ci95_upper"])
            self.assertLessEqual(point["all_rows_ci95_lower"], point["all_rows_prediction"])
            self.assertLessEqual(point["all_rows_prediction"], point["all_rows_ci95_upper"])
            self.assertAlmostEqual(
                point["difference_percentage_points"],
                (point["all_rows_prediction"] - point["deduplicated_prediction"]) * 100,
            )
        sex_curve = predictions["sex_interaction_curve"]
        curve_points = sex_curve["points"]
        self.assertEqual(len(curve_points), 21)
        self.assertEqual(curve_points[0]["expense_brl"], sex_curve["common_support"]["lower_brl"])
        self.assertEqual(curve_points[-1]["expense_brl"], sex_curve["common_support"]["upper_brl"])
        self.assertTrue(all(point["male_ci95_lower"] <= point["male_prediction"] <= point["male_ci95_upper"] for point in curve_points))
        self.assertTrue(all(point["female_ci95_lower"] <= point["female_prediction"] <= point["female_ci95_upper"] for point in curve_points))
        diagnostics = result["model_diagnostics"]
        fit = diagnostics["deduplicado_completo"]["fit"]
        self.assertEqual(sum(row["n"] for row in fit["calibration_deciles"]), 46)
        influence = diagnostics["deduplicado_completo"]["influence"]
        self.assertEqual(influence["cook_distance_screen_threshold"], 4 / 46)
        self.assertEqual(len(influence["top_influential_candidates"]), 10)
        self.assertEqual(len(diagnostics["top_one_percent_expense_sensitivity"]), 2)
        self.assertIn("HC1", predictions["uncertainty_method"])

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

    def test_secondary_race_analysis_counts_apto_before_votes_and_reports_unsupported_curve(self) -> None:
        connection = sqlite3.connect(self.database)
        connection.execute("UPDATE candidates SET race = 'AMARELA' WHERE sq_candidate = 'A000'")
        connection.execute("UPDATE candidates SET race = 'INDÍGENA' WHERE sq_candidate = 'A001'")
        connection.execute("UPDATE candidates SET race = NULL WHERE sq_candidate = 'A006'")
        connection.execute("DELETE FROM votes WHERE sq_candidate = 'A003'")
        connection.commit()
        connection.close()

        result = run_financial_analysis(self.database, self.validation, self.output)
        secondary = result["secondary_race_analysis"]

        self.assertEqual(secondary["population"]["apto_candidates_n"], 48)
        self.assertEqual(secondary["population"]["apto_with_votes_n"], 47)
        self.assertEqual(
            secondary["population"]["race_category_counts"],
            {"AMARELA": 1, "BRANCA": 14, "INDÍGENA": 1, "PARDA": 15, "PRETA": 16, "(ausente)": 1},
        )
        self.assertEqual(secondary["population"]["race_category_counts_with_votes"]["BRANCA"], 13)
        self.assertEqual(
            secondary["population"]["comparison_group_counts"],
            {"brancas": 14, "pretas_pardas": 31},
        )
        self.assertEqual(
            secondary["population"]["comparison_group_counts_with_votes"],
            {"brancas": 13, "pretas_pardas": 31},
        )
        self.assertEqual(
            secondary["population"]["outside_comparison_counts"],
            {"AMARELA": 1, "INDÍGENA": 1, "(ausente)": 1},
        )
        self.assertEqual(secondary["comparison_binary_apto_n"], 45)
        self.assertEqual(secondary["comparison_binary_population_n"], 44)
        self.assertEqual(secondary["comparison_complete_case_n"], 42)
        self.assertEqual(secondary["comparison_exclusions"]["missing_vote_or_denominator_n"], 1)
        self.assertEqual(secondary["comparison_exclusions"]["missing_either_expense_n"], 1)
        self.assertEqual(secondary["comparison_exclusions"]["missing_controls_n"], 1)
        self.assertEqual(secondary["comparison_complete_case_group_counts"], {"brancas": 13, "pretas_pardas": 29})
        self.assertEqual({model["name"] for model in secondary["models"]}, {"raca_deduplicado", "raca_todas_as_linhas"})
        self.assertTrue(all(model["converged"] for model in secondary["models"]))
        self.assertTrue(all(model["n"] == 42 for model in secondary["models"]))
        self.assertTrue(all(model["hc1_correction_factor"] == 42 / (42 - model["parameter_count"]) for model in secondary["models"]))
        self.assertTrue(all("expense_x_black_brown" in {row["term"] for row in secondary["coefficients"] if row["model"] == model["name"]} for model in secondary["models"]))
        for model in secondary["models"]:
            self.assertEqual(
                model["controls"],
                ["UF", "partido", "idade na data da eleição", "sexo", "escolaridade"],
            )
            self.assertIn("custo por voto", model["excluded_predictors"])
        self.assertEqual(result["model_complete_case_n"], 44)
        self.assertEqual(sum(row["candidate_count"] for row in secondary["descriptive_by_group"]), 84)
        for row in secondary["descriptive_by_group"]:
            self.assertEqual(row["candidate_count"], row["election_classified_n"] + row["unclassified_result_n"])
            if row["election_classified_n"]:
                self.assertAlmostEqual(
                    row["elected_proportion"],
                    row["elected_count"] / row["election_classified_n"],
                )
            self.assertEqual(
                (row["elected_count"], row["election_classified_n"]),
                {"brancas": (6, 13), "pretas_pardas": (15, 29)}[row["race_group"]],
            )
        self.assertTrue(all(not curve["points"] for curve in secondary["curves"].values()))
        self.assertTrue(all(curve["no_curve_reason"] for curve in secondary["curves"].values()))
        report = (self.output / "tse-2022-financial-analysis.md").read_text(encoding="utf-8")
        self.assertIn("Análise secundária acrescentada após os primeiros resultados: raça/cor", report)
        self.assertIn("suporte insuficiente", report)
        for suffix in ("deduplicado", "todas-as-linhas"):
            svg = (self.output / f"tse-2022-race-interaction-curve-{suffix}.svg").read_text(encoding="utf-8")
            self.assertIn("Curva não exibida", svg)

        with (self.output / "tse-2022-race-group-descriptives.csv").open(encoding="utf-8", newline="") as handle:
            descriptive_rows = list(csv.DictReader(handle))
        self.assertEqual(len(descriptive_rows), 4)
        with (self.output / "tse-2022-race-support-by-uf-party.csv").open(encoding="utf-8", newline="") as handle:
            support_rows = list(csv.DictReader(handle))
        self.assertTrue(any(row["dimension"] == "UF" for row in support_rows))
        self.assertTrue(any(row["dimension"] == "partido" for row in support_rows))
        with (self.output / "tse-2022-race-curve-support.csv").open(encoding="utf-8", newline="") as handle:
            curve_support_reader = csv.DictReader(handle)
            self.assertIn("supported_uf_party_strata", curve_support_reader.fieldnames)
        for scenario in ("deduplicado", "todas_as_linhas"):
            scenario_rows = [row for row in support_rows if row["scenario"] == scenario]
            self.assertEqual(sum(row["dimension"] == "UF" for row in scenario_rows), 2)
            self.assertEqual(sum(row["dimension"] == "partido" for row in scenario_rows), 4)
            self.assertEqual(sum(row["dimension"] == "UF×partido" for row in scenario_rows), 8)

    def test_supported_race_curve_uses_training_reference_levels_and_svg_breaks_gaps(self) -> None:
        rows = []
        for uf, count in (("SP", 100), ("RJ", 5)):
            for race_group in ("brancas", "pretas_pardas"):
                for index in range(count):
                    expense = 1_000_000 + index * 50_000
                    log_expense = math.log1p(expense / 100)
                    linear_predictor = (
                        (-1.0 if uf == "RJ" else 1.5)
                        + 0.08 * log_expense
                        + (0.15 if race_group == "pretas_pardas" else 0)
                        + 0.04 * (index % 2)
                    )
                    rows.append({
                        "uf": uf,
                        "party_code": "P0",
                        "age_at_election": 30 + index % 40,
                        "gender": ("FEMININO", "MASCULINO")[index % 2],
                        "schooling": ("MÉDIO", "SUPERIOR", "FUNDAMENTAL")[index % 3],
                        "race_group": race_group,
                        "expense_deduplicated_centavos": expense,
                        "vote_share": min(0.99, max(0.01, 1 / (1 + math.exp(-linear_predictor)) + 0.02 * math.sin(index * 1.7))),
                    })
        frame = pd.DataFrame(rows)
        model, _, fitted, model_frame, covariance = _fit_race_interaction(
            "race_support_test",
            frame,
            "expense_deduplicated_centavos",
        )
        curve, support, _ = _build_race_curve(
            "deduplicado",
            fitted,
            model_frame,
            "expense_deduplicated_centavos",
            covariance,
        )

        self.assertTrue(curve["points"])
        self.assertEqual(curve["eligible_uf_party_cells_n"], 1)
        self.assertAlmostEqual(curve["eligible_group_coverage"]["brancas"], 100 / 105)
        self.assertTrue(all(point["brancas_prediction"] > 0.5 for point in curve["points"]))
        self.assertTrue(any(row["stratum"] == "RJ × P0" and not row["eligible_uf_party_cell"] for row in support))
        self.assertIn("uf_SP", fitted.model.exog_names)
        self.assertGreater(model["hc1_correction_factor"], 1)

        points = [
            {
                "expense_brl": expense,
                **{
                    f"{group}_{stat}": value
                    for group in ("brancas", "pretas_pardas")
                    for stat, value in (
                        ("prediction", 0.4),
                        ("ci95_lower", 0.3),
                        ("ci95_upper", 0.5),
                    )
                },
            }
            for expense in (100.0, 200.0, 800.0)
        ]
        svg = _race_curve_svg({
            "points": points,
            "candidate_support_points": [
                {"expense_brl": 100.0, "published": True},
                {"expense_brl": 200.0, "published": True},
                {"expense_brl": 500.0, "published": False},
                {"expense_brl": 800.0, "published": True},
            ],
        })
        self.assertEqual(svg.count("<polyline"), 2)
        self.assertEqual(svg.count("<circle"), 2)
        self.assertNotIn("var(--c", svg)


    def test_race_election_comparison_uses_common_population_and_withholds_unsupported_adjustments(self) -> None:
        connection = sqlite3.connect(self.database)
        connection.execute(
            "UPDATE candidates SET candidate_total_status_code = '9', candidate_total_status = 'OUTRO' "
            "WHERE sq_candidate = 'A000'"
        )
        connection.commit()
        connection.close()

        result = run_financial_analysis(self.database, self.validation, self.output)
        comparison = result["secondary_race_analysis"]["election_adjusted_comparison"]
        self.assertEqual(comparison["status"], "adjustment_withheld_insufficient_common_support")
        self.assertEqual(
            comparison["controls"],
            ["UF", "partido", "idade na data da eleição", "sexo", "escolaridade"],
        )
        self.assertEqual(comparison["common_population_n"], 45)
        self.assertEqual(comparison["group_counts"], {"brancas": 15, "pretas_pardas": 30})
        self.assertEqual(comparison["elected_counts"], {"brancas": 7, "pretas_pardas": 15})
        self.assertAlmostEqual(comparison["observed_proportions"]["brancas"], 7 / 15)
        self.assertEqual(comparison["observed_proportions"]["pretas_pardas"], 0.5)
        self.assertAlmostEqual(
            comparison["observed_difference_pretas_pardas_minus_brancas_pp"],
            (0.5 - 7 / 15) * 100,
        )
        self.assertEqual(comparison["support"]["eligible_uf_party_cells_n"], 0)
        self.assertFalse(comparison["support"]["common_support_sufficient"])
        self.assertFalse(comparison["support"]["sufficient"])
        self.assertEqual(comparison["adjusted_estimates"], [])
        self.assertEqual(
            [model["common_population_n"] for model in comparison["specifications"]],
            [45, 45, 45],
        )
        self.assertEqual(
            [model["model_population_n"] for model in comparison["specifications"]],
            [None, None, None],
        )
        report = (self.output / "tse-2022-financial-analysis.md").read_text(encoding="utf-8")
        self.assertIn("### Comparação ajustada de eleição por raça/cor", report)
        self.assertIn("Não estimamos probabilidades ajustadas nem ICs", report)
    def test_race_election_comparison_estimates_all_specs_on_supported_common_population(self) -> None:
        connection = sqlite3.connect(self.database)
        cells = (("SP", "P0"), ("SP", "P1"), ("RJ", "P0"), ("RJ", "P1"))
        for index in range(48):
            group = "brancas" if index % 3 == 0 else "pretas_pardas"
            uf, party = cells[index % len(cells)]
            race = "BRANCA" if group == "brancas" else "PARDA"
            connection.execute(
                "UPDATE candidates SET uf = ?, party_code = ?, race = ? WHERE sq_candidate = ?",
                (uf, party, race, f"A{index:03d}"),
            )
        occurrence_rows = []
        deduplicated_rows = []
        candidate_index = 0
        for cell_index, (uf, party) in enumerate(cells):
            for group_index, race in enumerate(("BRANCA", "PARDA")):
                for within_group in range(20):
                    candidate = f"S{candidate_index:03d}"
                    candidate_index += 1
                    elected = within_group % 2 == 0
                    result_code = "2" if elected else "4"
                    result_text = "ELEITO POR QP" if elected else "NÃO ELEITO"
                    gender = ("FEMININO", "MASCULINO")[(within_group // 2 + group_index + cell_index) % 2]
                    schooling = ("MÉDIO", "SUPERIOR", "FUNDAMENTAL")[within_group % 3]
                    birth_year = 1960 + (within_group * 7) % 35
                    connection.execute(
                        "INSERT INTO candidates VALUES (?, 2022, 1, ?, '6', '12', ?, ?, ?, ?, ?, 'SOLTEIRO', 'PROFESSOR', ?, ?)",
                        (
                            candidate, uf, party, f"01/01/{birth_year}", gender, race, schooling,
                            result_code, result_text,
                        ),
                    )
                    votes = 100 + within_group * 13 + group_index * 5 + cell_index
                    connection.execute("INSERT INTO votes VALUES (?, ?)", (candidate, votes))
                    amount = 10000 + within_group * 175 + group_index * 350 + cell_index * 90
                    expense = (candidate, f"DOC-{candidate}", "Final", f"{amount / 100:.2f}".replace(".", ","), "src.zip", "expenses.csv", 1000 + candidate_index)
                    occurrence_rows.append(expense)
                    deduplicated_rows.append(
                        (candidate, expense[1], amount, "signature", "snapshot-test", "src.zip", "expenses.csv", 1000 + candidate_index)
                    )
        connection.executemany("INSERT INTO expense_occurrences VALUES (?, ?, ?, ?, ?, ?, ?)", occurrence_rows)
        connection.executemany("INSERT INTO expenses VALUES (?, ?, ?, ?, ?, ?, ?, ?)", deduplicated_rows)
        connection.commit()
        connection.close()

        result = run_financial_analysis(self.database, self.validation, self.output)
        comparison = result["secondary_race_analysis"]["election_adjusted_comparison"]
        self.assertEqual(comparison["status"], "adjusted_models_estimated", comparison["withheld_reason"])
        self.assertTrue(comparison["support"]["sufficient"])
        self.assertGreaterEqual(comparison["support"]["coverage_by_group"]["brancas"], 0.8)
        self.assertGreaterEqual(comparison["support"]["coverage_by_group"]["pretas_pardas"], 0.8)
        estimates = comparison["adjusted_estimates"]
        self.assertEqual(
            [estimate["model"] for estimate in estimates],
            [
                "controls_only",
                "controls_plus_deduplicated_expense",
                "controls_plus_all_lines_expense",
            ],
        )
        self.assertEqual(
            [model["model_population_n"] for model in comparison["specifications"]],
            [comparison["support"]["supported_population_n"]] * 3,
        )
        for estimate in estimates:
            self.assertEqual(estimate["population_n"], comparison["support"]["supported_population_n"])
            for group in ("brancas", "pretas_pardas"):
                summary = estimate[group]
                self.assertGreaterEqual(summary["prediction"], 0)
                self.assertLessEqual(summary["prediction"], 1)
                self.assertLessEqual(summary["ci95_lower"], summary["prediction"])
                self.assertGreaterEqual(summary["ci95_upper"], summary["prediction"])
            self.assertTrue(math.isfinite(estimate["difference_pretas_pardas_minus_brancas_pp"]))
            self.assertTrue(math.isfinite(estimate["difference_ci95_lower_pp"]))
            self.assertTrue(math.isfinite(estimate["difference_ci95_upper_pp"]))
        report = (self.output / "tse-2022-financial-analysis.md").read_text(encoding="utf-8")
        self.assertIn("| Controles, sem despesa |", report)
        self.assertIn("| Controles + despesa deduplicada |", report)
        self.assertNotIn("Não estimamos probabilidades ajustadas nem ICs", report)


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


class ExpenseTemporalAnalysisTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.database = root / "temporal.sqlite"
        self.output = root / "reports"
        connection = sqlite3.connect(self.database)
        connection.executescript(
            """
            CREATE TABLE candidates (
                sq_candidate TEXT, candidate_status_code TEXT,
                election_year INTEGER, turn INTEGER, cargo_code TEXT
            );
            CREATE TABLE expense_occurrences (
                SQ_CANDIDATO TEXT, TP_PRESTACAO_CONTAS TEXT,
                DT_DESPESA TEXT, DT_PRESTACAO_CONTAS TEXT, DT_GERACAO TEXT,
                VR_DESPESA_CONTRATADA TEXT, _source_archive TEXT,
                _source_member TEXT, _source_row INTEGER
            );
            CREATE TABLE expenses (
                sq_candidate TEXT, sq_expense TEXT, amount_centavos INTEGER,
                source_archive TEXT, source_member TEXT, source_row INTEGER
            );
            """
        )
        connection.executemany(
            "INSERT INTO candidates VALUES (?, ?, 2022, 1, '6')",
            [(candidate, "12") for candidate in ("A", "B", "C", "D", "E", "F")]
            + [("G", "11")],
        )
        rows = []

        def add_row(candidate: str, expense_date: str, amount: str, submission: str = "Final", keep: bool = True) -> None:
            source_row = len(rows) + 1
            rows.append((
                candidate, submission, expense_date, "15/11/2022", "10/11/2022",
                amount, "source.zip", "expenses.csv", source_row,
            ))
            if keep:
                connection.execute(
                    "INSERT INTO expenses VALUES (?, ?, ?, 'source.zip', 'expenses.csv', ?)",
                    (candidate, f"DOC-{source_row}", int(amount.replace(",", "")), source_row),
                )

        add_row("A", "01/10/2022", "10,00")
        add_row("A", "01/10/2022", "10,00", keep=False)
        add_row("B", "02/10/2022", "30,00")
        add_row("C", "03/10/2022", "40,00")
        add_row("D", "", "50,00")
        add_row("E", "31/02/2022", "60,00")
        add_row("E", "31/02/2022", "60,00", keep=False)
        add_row("F", "31/12/2021", "70,00")
        add_row("A", "01/10/2022", "90,00", submission="Parcial", keep=False)
        add_row("G", "01/10/2022", "99,00", keep=False)
        connection.executemany(
            "INSERT INTO expense_occurrences VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        connection.commit()
        connection.close()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_reports_months_voting_day_and_date_quality_for_both_expense_scenarios(self) -> None:
        result = write_expense_temporal_analysis(self.database, self.output)
        self.assertEqual(result["scenarios"]["deduplicado"]["expense_count"], 6)
        self.assertEqual(result["scenarios"]["todas_as_linhas"]["expense_count"], 8)
        self.assertEqual(result["scenarios"]["deduplicado"]["first_valid_date"], "2021-12-31")
        self.assertEqual(result["scenarios"]["deduplicado"]["first_in_election_year"], "2022-10-01")
        self.assertEqual(result["scenarios"]["deduplicado"]["last_in_election_year"], "2022-10-03")

        with (self.output / "tse-2022-expense-temporal-monthly.csv").open(encoding="utf-8", newline="") as handle:
            monthly = list(csv.DictReader(handle))
        deduplicated_october = next(row for row in monthly if row["scenario"] == "deduplicado" and row["month"] == "2022-10")
        all_rows_october = next(row for row in monthly if row["scenario"] == "todas_as_linhas" and row["month"] == "2022-10")
        self.assertEqual((deduplicated_october["expense_count"], deduplicated_october["candidate_count"], deduplicated_october["declared_expense_centavos"]), ("3", "3", "8000"))
        self.assertEqual((all_rows_october["expense_count"], all_rows_october["candidate_count"], all_rows_october["declared_expense_centavos"]), ("4", "3", "9000"))
        self.assertEqual((deduplicated_october["first_expense_date"], deduplicated_october["last_expense_date"]), ("2022-10-01", "2022-10-03"))
        self.assertEqual(len(monthly), 24)
        self.assertEqual(sum(int(row["expense_count"]) for row in monthly if row["scenario"] == "deduplicado"), 3)

        with (self.output / "tse-2022-expense-temporal-relative-to-election.csv").open(encoding="utf-8", newline="") as handle:
            timing = list(csv.DictReader(handle))
        all_timing = {row["relative_period"]: row for row in timing if row["scenario"] == "todas_as_linhas"}
        self.assertEqual(
            {period: (row["expense_count"], row["candidate_count"], row["declared_expense_centavos"]) for period, row in all_timing.items()},
            {"before": ("2", "1", "2000"), "on": ("1", "1", "3000"), "after": ("1", "1", "4000")},
        )

        with (self.output / "tse-2022-expense-temporal-date-quality.csv").open(encoding="utf-8", newline="") as handle:
            quality = list(csv.DictReader(handle))
        all_quality = {row["date_status"]: row for row in quality if row["scenario"] == "todas_as_linhas"}
        self.assertEqual(all_quality["missing"]["expense_count"], "1")
        self.assertEqual(all_quality["invalid"]["expense_count"], "2")
        self.assertEqual(all_quality["outside_2022"]["expense_count"], "1")
        self.assertEqual(all_quality["valid_2022"]["expense_count"], "4")
        deduplicated_quality = {row["date_status"]: row for row in quality if row["scenario"] == "deduplicado"}
        self.assertEqual(
            {status: row["expense_count"] for status, row in deduplicated_quality.items()},
            {"valid_2022": "3", "outside_2022": "1", "missing": "1", "invalid": "1"},
        )
        self.assertEqual(all_quality["missing"]["declared_expense_centavos"], "5000")
        self.assertEqual(all_quality["invalid"]["declared_expense_centavos"], "12000")
        self.assertIn("31/02/2022", all_quality["invalid"]["example_raw_values"])
        self.assertEqual(deduplicated_quality["invalid"]["declared_expense_centavos"], "6000")
        recut = json.loads((self.output / "tse-2022-expense-temporal-recut.json").read_text(encoding="utf-8"))
        self.assertEqual(recut["date_field"], "DT_DESPESA")
        self.assertEqual(recut["scenarios"]["todas_as_linhas"]["date_quality"]["invalid"], 2)


if __name__ == "__main__":
    unittest.main()
