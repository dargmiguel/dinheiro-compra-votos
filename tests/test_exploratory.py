import csv
import json
import sqlite3
import tempfile
import unittest
import zipfile
from pathlib import Path

from tse_pilot.exploratory import _comparison_rows, _spearman, run_exploratory_scenarios


class ExploratoryScenarioTests(unittest.TestCase):
    def _write_archive(self, directory, filename, members):
        path = Path(directory) / filename
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, columns, rows in members:
                lines = [";".join(columns)]
                lines.extend(";".join(row.get(column, "") for column in columns) for row in rows)
                archive.writestr(name, ("\n".join(lines) + "\n").encode("latin-1"))
        return path

    def _fixture(self, directory):
        candidates = self._write_archive(
            directory,
            "candidates.zip",
            [
                (
                    "consulta_cand_2022_SP.csv",
                    [
                        "ANO_ELEICAO", "NR_TURNO", "SG_UF", "CD_CARGO", "DS_CARGO",
                        "SQ_CANDIDATO", "NR_CANDIDATO", "NM_CANDIDATO",
                        "CD_SITUACAO_CANDIDATURA", "DS_SITUACAO_CANDIDATURA",
                        "CD_SIT_TOT_TURNO", "DS_SIT_TOT_TURNO",
                    ],
                    [
                        {"ANO_ELEICAO": "2022", "NR_TURNO": "1", "SG_UF": "SP", "CD_CARGO": "6", "DS_CARGO": "Deputado Federal", "SQ_CANDIDATO": "1", "NR_CANDIDATO": "1001", "NM_CANDIDATO": "A", "CD_SITUACAO_CANDIDATURA": "12", "DS_SITUACAO_CANDIDATURA": "APTO", "CD_SIT_TOT_TURNO": "4", "DS_SIT_TOT_TURNO": "NÃO ELEITO"},
                        {"ANO_ELEICAO": "2022", "NR_TURNO": "1", "SG_UF": "SP", "CD_CARGO": "6", "DS_CARGO": "Deputado Federal", "SQ_CANDIDATO": "2", "NR_CANDIDATO": "1002", "NM_CANDIDATO": "B", "CD_SITUACAO_CANDIDATURA": "3", "DS_SITUACAO_CANDIDATURA": "INAPTO", "CD_SIT_TOT_TURNO": "-1", "DS_SIT_TOT_TURNO": "#NULO"},
                        {"ANO_ELEICAO": "2022", "NR_TURNO": "1", "SG_UF": "SP", "CD_CARGO": "6", "DS_CARGO": "Deputado Federal", "SQ_CANDIDATO": "3", "NR_CANDIDATO": "1003", "NM_CANDIDATO": "C", "CD_SITUACAO_CANDIDATURA": "12", "DS_SITUACAO_CANDIDATURA": "APTO", "CD_SIT_TOT_TURNO": "5", "DS_SIT_TOT_TURNO": "SUPLENTE"},
                        {"ANO_ELEICAO": "2022", "NR_TURNO": "1", "SG_UF": "SP", "CD_CARGO": "6", "DS_CARGO": "Deputado Federal", "SQ_CANDIDATO": "4", "NR_CANDIDATO": "1004", "NM_CANDIDATO": "D", "CD_SITUACAO_CANDIDATURA": "12", "DS_SITUACAO_CANDIDATURA": "APTO", "CD_SIT_TOT_TURNO": "4", "DS_SIT_TOT_TURNO": "NÃO ELEITO"},
                        {"ANO_ELEICAO": "2022", "NR_TURNO": "1", "SG_UF": "SP", "CD_CARGO": "6", "DS_CARGO": "Deputado Federal", "SQ_CANDIDATO": "5", "NR_CANDIDATO": "1005", "NM_CANDIDATO": "E", "CD_SITUACAO_CANDIDATURA": "12", "DS_SITUACAO_CANDIDATURA": "APTO", "CD_SIT_TOT_TURNO": "5", "DS_SIT_TOT_TURNO": "SUPLENTE"},
                    ],
                )
            ],
        )
        duplicate = {"AA_ELEICAO": "2022", "ST_TURNO": "1", "SG_UF": "SP", "CD_CARGO": "6", "DS_CARGO": "Deputado Federal", "SQ_CANDIDATO": "1", "TP_PRESTACAO_CONTAS": "Final", "DT_PRESTACAO_CONTAS": "20/11/2022", "SQ_PRESTADOR_CONTAS": "10", "SQ_DESPESA": "100", "VR_DESPESA_CONTRATADA": "50,00"}
        expense_rows = [duplicate, duplicate, {**duplicate, "TP_PRESTACAO_CONTAS": "Parcial", "SQ_DESPESA": "101", "VR_DESPESA_CONTRATADA": "900,00"}, {**duplicate, "SQ_CANDIDATO": "3", "SQ_DESPESA": "300", "VR_DESPESA_CONTRATADA": "0,00"}, {**duplicate, "SQ_CANDIDATO": "4", "SQ_DESPESA": "400", "VR_DESPESA_CONTRATADA": "100,00"}]
        accounts = self._write_archive(
            directory,
            "accounts.zip",
            [
                (
                    "despesas_contratadas_candidatos_2022_SP.csv",
                    list(duplicate),
                    expense_rows,
                )
            ],
        )
        votes = self._write_archive(directory, "votes.zip", [])
        candidates_sqlite = Path(directory) / "derived" / "pilot.sqlite"
        candidates_sqlite.parent.mkdir()
        connection = sqlite3.connect(candidates_sqlite)
        connection.execute("CREATE TABLE votes (sq_candidate TEXT, valid_votes INTEGER)")
        connection.executemany("INSERT INTO votes VALUES (?, ?)", [("1", 7), ("3", 5), ("4", 0)])
        source_columns = list(duplicate)
        column_definitions = ", ".join(f'"{column}" TEXT' for column in source_columns)
        connection.execute(
            f"CREATE TABLE expense_occurrences ({column_definitions}, _source_archive TEXT, _source_member TEXT, _source_row INTEGER, _row_signature TEXT)"
        )
        placeholders = ", ".join("?" for _ in range(len(source_columns) + 4))
        connection.executemany(
            f"INSERT INTO expense_occurrences VALUES ({placeholders})",
            [
                (*[row[column] for column in source_columns], "accounts.zip", "despesas_contratadas_candidatos_2022_SP.csv", row_number, "fixture")
                for row_number, row in enumerate(expense_rows, start=2)
            ],
        )
        connection.commit()
        connection.close()
        validation = {
            "status": "approved",
            "fatal_counts": {
                "invalid_candidate_fields": 0,
                "duplicate_candidate_rows": 0,
                "invalid_expense_fields": 0,
                "missing_expense_amount": 0,
                "invalid_vote_fields": 0,
                "missing_vote_amount": 0,
                "duplicate_vote_rows": 0,
                "unknown_expense_candidates": 0,
                "unknown_vote_candidates": 0,
            },
        }
        validation_path = Path(directory) / "derived" / "validation.json"
        validation_path.write_text(json.dumps(validation), encoding="utf-8")
        manifest = {
            "manifest_id": "fixture",
            "resources": [
                {"resource_key": "candidates_2022", "local_path": str(candidates)},
                {"resource_key": "accounts_2022", "local_path": str(accounts)},
                {"resource_key": "votes_2022", "local_path": str(votes)},
            ],
        }
        manifest_path = Path(directory) / "manifest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        return manifest_path, validation_path, candidates_sqlite

    def test_exploration_emits_explicit_deduplicated_and_all_rows_scenarios(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest, validation, production_database = self._fixture(directory)
            production_dir = production_database.parent
            sentinel = production_dir / "analytical_base.csv"
            sentinel.write_text("approved sentinel", encoding="utf-8")
            output = Path(directory) / "exploratory" / "2022"

            metadata = run_exploratory_scenarios(manifest, validation, output)

            self.assertEqual(metadata["status"], "exploratory_only")
            self.assertTrue(metadata["not_approved"])
            self.assertEqual(metadata["scenario_deduplicated"], "deduplicado_principal")
            self.assertEqual(metadata["scenario_all_rows"], "todas_as_linhas_sensibilidade")
            self.assertEqual(metadata["population_included"], 4)
            self.assertEqual(metadata["population_excluded_by_reason"]["inapto"], 1)
            self.assertEqual(metadata["exact_repeat_rows_in_final_apto"], 1)
            self.assertEqual(metadata["candidates_affected_by_dedup_final_apto"], 1)
            self.assertEqual(metadata["preserve_all_total_centavos_final_apto"], 20000)
            self.assertEqual(metadata["deduplicated_total_centavos_final_apto"], 15000)
            self.assertEqual(metadata["financial_difference_centavos_final_apto"], 5000)
            self.assertTrue(sentinel.exists())
            self.assertFalse((output / "analytical_base.csv").exists())
            self.assertTrue((output / "exploratory_report.md").exists())

            with (output / "exploratory_deduplicated_primary.csv").open(encoding="utf-8", newline="") as handle:
                deduplicated_reader = csv.DictReader(handle)
                self.assertIn("sq_candidato", deduplicated_reader.fieldnames)
                self.assertIn("despesa_declarada_centavos", deduplicated_reader.fieldnames)
                deduplicated = {row["sq_candidato"]: row for row in deduplicated_reader}
            with (output / "exploratory_all_rows_sensitivity.csv").open(encoding="utf-8", newline="") as handle:
                all_rows = {row["sq_candidato"]: row for row in csv.DictReader(handle)}
            self.assertEqual(set(deduplicated), set(all_rows))
            self.assertEqual(set(deduplicated), {"1", "3", "4", "5"})

            self.assertEqual(deduplicated["1"]["despesa_declarada_centavos"], "5000")
            self.assertEqual(all_rows["1"]["despesa_declarada_centavos"], "10000")
            self.assertEqual(deduplicated["3"]["observacao_despesa"], "zero_observado")
            self.assertEqual(deduplicated["3"]["observacao_votacao"], "observado")
            self.assertEqual(deduplicated["3"]["custo_por_voto_reais"], "0.000000")
            self.assertEqual(deduplicated["4"]["despesa_declarada_centavos"], "10000")
            self.assertEqual(deduplicated["4"]["observacao_votacao"], "zero_observado")
            self.assertEqual(deduplicated["4"]["custo_por_voto_reais"], "")
            self.assertEqual(deduplicated["5"]["observacao_despesa"], "ausente")
            self.assertEqual(deduplicated["5"]["observacao_votacao"], "ausente")
            self.assertEqual(deduplicated["5"]["custo_por_voto_reais"], "")
            self.assertEqual(deduplicated["1"]["custo_por_voto_reais"], "7.142857")
            self.assertEqual(all_rows["1"]["custo_por_voto_reais"], "14.285714")
            with (output / "exploratory_deduplicated_vs_all_rows.csv").open(encoding="utf-8", newline="") as handle:
                comparison = {row["sq_candidato"]: row for row in csv.DictReader(handle)}
            self.assertEqual(set(comparison), set(deduplicated))
            self.assertEqual(comparison["1"]["custo_por_voto_reais_deduplicado"], "7.142857")
            self.assertEqual(comparison["1"]["custo_por_voto_reais_todas_as_linhas"], "14.285714")
            self.assertEqual(comparison["5"]["diferenca_todas_as_linhas_menos_deduplicado_centavos"], "")

            with (output / "exploratory_cost_per_vote.csv").open(encoding="utf-8", newline="") as handle:
                costs = list(csv.DictReader(handle))
            self.assertIn("custo_agregado_reais_por_voto", costs[0])
            self.assertNotIn("custo_agregado_centavos_por_voto", costs[0])
            self.assertEqual(costs[0]["custo_agregado_reais_por_voto"], "4.17")
            self.assertEqual(costs[1]["custo_agregado_reais_por_voto"], "8.33")
            report_text = (output / "exploratory_report.md").read_text(encoding="utf-8")
            self.assertIn("tratamento deduplicado", report_text)
            self.assertIn("todas as linhas", report_text)
            self.assertNotIn("Cenário A", report_text)
            self.assertNotIn("Cenário B", report_text)
            self.assertIn("R$ 8,33", report_text)
            self.assertIn("reais por voto", report_text)
            with (output / "exploratory_uf_associations.csv").open(encoding="utf-8", newline="") as handle:
                uf_rows = list(csv.DictReader(handle))
            sp_deduplicated = next(row for row in uf_rows if row["cenario"] == "deduplicado_principal" and row["uf"] == "SP")
            self.assertEqual(sp_deduplicated["despesas_iguais_a_zero"], "1")
            self.assertEqual(sp_deduplicated["votacoes_iguais_a_zero"], "1")
            self.assertEqual(sp_deduplicated["correlacao_spearman_despesa_votos"], "-0.500000")
            self.assertTrue((output / "plots" / "exploratory_uf_spearman_deduplicated_vs_all_rows.svg").exists())
            for plot_name in ("exploratory_uf_spearman_deduplicated_vs_all_rows.svg", "exploratory_uf_expense_totals.svg"):
                plot = (output / "plots" / plot_name).read_text(encoding="utf-8")
                self.assertIn("deduplicado", plot)
                self.assertIn("todas as linhas", plot)
                self.assertNotIn("A —", plot)
                self.assertNotIn("B —", plot)



    def test_exploration_refuses_blocked_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest, validation, _ = self._fixture(directory)
            blocked_validation = Path(directory) / "blocked-validation.json"
            data = json.loads(validation.read_text(encoding="utf-8"))
            data["status"] = "blocked"
            blocked_validation.write_text(json.dumps(data), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "base aprovada"):
                run_exploratory_scenarios(manifest, blocked_validation, Path(directory) / "exploratory")

            self.assertFalse((Path(directory) / "exploratory").exists())

    def test_exploration_refuses_production_output_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest, validation, _ = self._fixture(directory)

            with self.assertRaisesRegex(ValueError, "diretório próprio"):
                run_exploratory_scenarios(manifest, validation, Path(directory) / "derived" / "2022")


class ScenarioComparisonTests(unittest.TestCase):
    @staticmethod
    def _row(candidate_id, expense, uf="SP"):
        return {
            "sq_candidate": candidate_id,
            "uf": uf,
            "candidate_number": candidate_id,
            "candidate_name": f"candidate-{candidate_id}",
            "declared_expense_centavos": str(expense),
            "cost_per_vote_brl": "",
            "exact_repeat_rows": 0,
            "vote_observation": "observed",
            "valid_nominal_votes": "10",
        }

    def test_comparison_joins_reordered_rows_by_candidate_key(self):
        rows_deduplicated = [self._row("1", 500), self._row("2", 900)]
        rows_all_rows = [self._row("2", 800), self._row("1", 700)]

        comparison = _comparison_rows(rows_deduplicated, rows_all_rows)

        self.assertEqual([row["sq_candidate"] for row in comparison], ["1", "2"])
        self.assertEqual(comparison[0]["expense_all_rows_centavos"], 700)
        self.assertEqual(comparison[0]["difference_all_rows_minus_deduplicated_centavos"], 200)

    def test_comparison_rejects_different_lengths(self):
        with self.assertRaisesRegex(ValueError, "comprimentos"):
            _comparison_rows([self._row("1", 500), self._row("2", 900)], [self._row("1", 300)])

    def test_comparison_rejects_incompatible_candidate_keys(self):
        with self.assertRaisesRegex(ValueError, "chaves"):
            _comparison_rows([self._row("1", 500), self._row("2", 900)], [self._row("1", 300), self._row("3", 800)])

    def test_comparison_rejects_duplicate_candidate_keys(self):
        with self.assertRaisesRegex(ValueError, "duplicada"):
            _comparison_rows([self._row("1", 500), self._row("1", 600)], [self._row("1", 300), self._row("2", 800)])

    def test_comparison_rejects_divergent_candidate_identity(self):
        with self.assertRaisesRegex(ValueError, "identidade"):
            _comparison_rows([self._row("1", 500)], [self._row("1", 300, uf="RJ")])


class SpearmanTests(unittest.TestCase):
    def test_spearman_uses_average_ranks_for_ties(self):
        self.assertEqual(_spearman([(1, 1), (1, 2), (2, 3)]), "0.866025")
