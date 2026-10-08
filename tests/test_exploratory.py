import csv
import json
import sqlite3
import tempfile
import unittest
import zipfile
from pathlib import Path

from tse_pilot.exploratory import run_exploratory_scenarios


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
                    ],
                )
            ],
        )
        duplicate = {"AA_ELEICAO": "2022", "ST_TURNO": "1", "SG_UF": "SP", "CD_CARGO": "6", "DS_CARGO": "Deputado Federal", "SQ_CANDIDATO": "1", "TP_PRESTACAO_CONTAS": "Final", "DT_PRESTACAO_CONTAS": "20/11/2022", "SQ_PRESTADOR_CONTAS": "10", "SQ_DESPESA": "100", "VR_DESPESA_CONTRATADA": "50,00"}
        accounts = self._write_archive(
            directory,
            "accounts.zip",
            [
                (
                    "despesas_contratadas_candidatos_2022_SP.csv",
                    list(duplicate),
                    [duplicate, duplicate, {**duplicate, "TP_PRESTACAO_CONTAS": "Parcial", "SQ_DESPESA": "101", "VR_DESPESA_CONTRATADA": "900,00"}, {**duplicate, "SQ_CANDIDATO": "3", "SQ_DESPESA": "300", "VR_DESPESA_CONTRATADA": "0,00"}],
                )
            ],
        )
        votes = self._write_archive(directory, "votes.zip", [])
        candidates_sqlite = Path(directory) / "derived" / "pilot.sqlite"
        candidates_sqlite.parent.mkdir()
        connection = sqlite3.connect(candidates_sqlite)
        connection.execute("CREATE TABLE votes (sq_candidate TEXT, valid_votes INTEGER)")
        connection.executemany("INSERT INTO votes VALUES (?, ?)", [("1", 7), ("3", 0)])
        connection.commit()
        connection.close()
        validation = {
            "status": "blocked",
            "fatal_counts": {
                "invalid_candidate_fields": 0,
                "duplicate_candidate_rows": 0,
                "invalid_expense_fields": 0,
                "missing_expense_amount": 0,
                "duplicate_expense_rows": 1,
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

    def test_exploration_emits_two_marked_scenarios_without_approved_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest, validation, production_database = self._fixture(directory)
            production_dir = production_database.parent
            sentinel = production_dir / "analytical_base.csv"
            sentinel.write_text("approved sentinel", encoding="utf-8")
            output = Path(directory) / "exploratory" / "2022"

            metadata = run_exploratory_scenarios(manifest, validation, output)

            self.assertEqual(metadata["status"], "exploratory_only")
            self.assertTrue(metadata["not_approved"])
            self.assertEqual(metadata["population_included"], 2)
            self.assertEqual(metadata["population_excluded_by_reason"]["inapto"], 1)
            self.assertEqual(metadata["exact_repeat_rows_in_final_apto"], 1)
            self.assertTrue(sentinel.exists())
            self.assertFalse((output / "analytical_base.csv").exists())
            self.assertTrue((output / "exploratory_report.md").exists())

            with (output / "exploratory_scenario_a_preserve_all.csv").open(encoding="utf-8", newline="") as handle:
                scenario_a = {row["sq_candidate"]: row for row in csv.DictReader(handle)}
            with (output / "exploratory_scenario_b_remove_exact_repeats.csv").open(encoding="utf-8", newline="") as handle:
                scenario_b = {row["sq_candidate"]: row for row in csv.DictReader(handle)}

            self.assertEqual(scenario_a["1"]["declared_expense_centavos"], "10000")
            self.assertEqual(scenario_b["1"]["declared_expense_centavos"], "5000")
            self.assertEqual(scenario_a["3"]["expense_observation"], "observed_zero")
            self.assertEqual(scenario_a["3"]["valid_nominal_votes"], "0")
            self.assertEqual(scenario_a["3"]["vote_observation"], "observed_zero")

    def test_exploration_refuses_approved_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest, validation, _ = self._fixture(directory)
            approved_validation = Path(directory) / "approved-validation.json"
            data = json.loads(validation.read_text(encoding="utf-8"))
            data["status"] = "approved"
            approved_validation.write_text(json.dumps(data), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "validação bloqueada"):
                run_exploratory_scenarios(manifest, approved_validation, Path(directory) / "exploratory")

            self.assertFalse((Path(directory) / "exploratory").exists())

    def test_exploration_refuses_production_output_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest, validation, _ = self._fixture(directory)

            with self.assertRaisesRegex(ValueError, "diretório próprio"):
                run_exploratory_scenarios(manifest, validation, Path(directory) / "derived" / "2022")
