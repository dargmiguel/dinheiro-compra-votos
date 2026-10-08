import csv
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from tse_pilot.pipeline import run_pipeline


class PilotPipelineTests(unittest.TestCase):
    def _write_archive(self, directory, filename, members):
        path = Path(directory) / filename
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, columns, rows in members:
                output = []
                output.append(";".join(columns))
                output.extend(";".join(row.get(column, "") for column in columns) for row in rows)
                archive.writestr(name, ("\n".join(output) + "\n").encode("latin-1"))
        return path

    def _manifest(self, directory, candidates, accounts, votes):
        resources = []
        for key, path in (
            ("candidates_2022", candidates),
            ("accounts_2022", accounts),
            ("votes_2022", votes),
        ):
            resources.append({"resource_key": key, "local_path": str(path)})
        manifest = {"manifest_id": "fixture", "election": 2022, "resources": resources}
        path = Path(directory) / "manifest.json"
        path.write_text(json.dumps(manifest), encoding="utf-8")
        return path

    def _fixture(self, directory, duplicate_expense=False, unknown_expense=False, missing_expense=False, repeated_document=False):
        candidate_columns = ["ANO_ELEICAO", "NR_TURNO", "SG_UF", "CD_CARGO", "DS_CARGO", "SQ_CANDIDATO", "NR_CANDIDATO", "NM_CANDIDATO"]
        candidates = [
            {"ANO_ELEICAO": "2022", "NR_TURNO": "1", "SG_UF": "SP", "CD_CARGO": "6", "DS_CARGO": "Deputado Federal", "SQ_CANDIDATO": "1", "NR_CANDIDATO": "1001", "NM_CANDIDATO": "A"},
            {"ANO_ELEICAO": "2022", "NR_TURNO": "1", "SG_UF": "SP", "CD_CARGO": "6", "DS_CARGO": "Deputado Federal", "SQ_CANDIDATO": "2", "NR_CANDIDATO": "1002", "NM_CANDIDATO": "B"},
            {"ANO_ELEICAO": "2022", "NR_TURNO": "1", "SG_UF": "SP", "CD_CARGO": "7", "DS_CARGO": "Deputado Estadual", "SQ_CANDIDATO": "3", "NR_CANDIDATO": "1003", "NM_CANDIDATO": "C"},
        ]
        account_columns = ["AA_ELEICAO", "ST_TURNO", "SG_UF", "CD_CARGO", "DS_CARGO", "SQ_CANDIDATO", "SQ_DESPESA", "VR_DESPESA_CONTRATADA"]
        expenses = [
            {"AA_ELEICAO": "2022", "ST_TURNO": "1", "SG_UF": "SP", "CD_CARGO": "6", "DS_CARGO": "Deputado Federal", "SQ_CANDIDATO": "1", "SQ_DESPESA": "10", "VR_DESPESA_CONTRATADA": "100,00"},
            {"AA_ELEICAO": "2022", "ST_TURNO": "1", "SG_UF": "SP", "CD_CARGO": "6", "DS_CARGO": "Deputado Federal", "SQ_CANDIDATO": "1", "SQ_DESPESA": "11", "VR_DESPESA_CONTRATADA": "0,00"},
        ]
        if duplicate_expense:
            expenses.append(expenses[0].copy())
        if unknown_expense:
            expenses.append({**expenses[0], "SQ_CANDIDATO": "99", "SQ_DESPESA": "99"})
        if missing_expense:
            expenses[0]["VR_DESPESA_CONTRATADA"] = ""
        if repeated_document:
            expenses[1]["SQ_DESPESA"] = expenses[0]["SQ_DESPESA"]
        vote_columns = ["ANO_ELEICAO", "NR_TURNO", "SG_UF", "CD_CARGO", "DS_CARGO", "SQ_CANDIDATO", "CD_MUNICIPIO", "NR_ZONA", "ST_VOTO_EM_TRANSITO", "QT_VOTOS_NOMINAIS", "QT_VOTOS_NOMINAIS_VALIDOS"]
        votes = [
            {"ANO_ELEICAO": "2022", "NR_TURNO": "1", "SG_UF": "SP", "CD_CARGO": "6", "DS_CARGO": "Deputado Federal", "SQ_CANDIDATO": "1", "CD_MUNICIPIO": "1", "NR_ZONA": "10", "ST_VOTO_EM_TRANSITO": "N", "QT_VOTOS_NOMINAIS": "3", "QT_VOTOS_NOMINAIS_VALIDOS": "3"},
            {"ANO_ELEICAO": "2022", "NR_TURNO": "1", "SG_UF": "SP", "CD_CARGO": "6", "DS_CARGO": "Deputado Federal", "SQ_CANDIDATO": "1", "CD_MUNICIPIO": "1", "NR_ZONA": "11", "ST_VOTO_EM_TRANSITO": "N", "QT_VOTOS_NOMINAIS": "0", "QT_VOTOS_NOMINAIS_VALIDOS": "0"},
            {"ANO_ELEICAO": "2022", "NR_TURNO": "1", "SG_UF": "SP", "CD_CARGO": "6", "DS_CARGO": "Deputado Federal", "SQ_CANDIDATO": "2", "CD_MUNICIPIO": "1", "NR_ZONA": "10", "ST_VOTO_EM_TRANSITO": "N", "QT_VOTOS_NOMINAIS": "0", "QT_VOTOS_NOMINAIS_VALIDOS": "0"},
        ]
        candidates_path = self._write_archive(directory, "candidates.zip", [("consulta_cand_2022_SP.csv", candidate_columns, candidates)])
        accounts_path = self._write_archive(directory, "accounts.zip", [("despesas_contratadas_candidatos_2022_SP.csv", account_columns, expenses)])
        votes_path = self._write_archive(directory, "votes.zip", [("votacao_candidato_munzona_2022_SP.csv", vote_columns, votes)])
        return self._manifest(directory, candidates_path, accounts_path, votes_path)

    def test_validated_base_keeps_absence_distinct_from_observed_zero(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run_pipeline(self._fixture(directory), Path(directory) / "derived")
            self.assertEqual(result["status"], "approved")
            with (Path(directory) / "derived" / "analytical_base.csv").open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 2)
            by_candidate = {row["sq_candidate"]: row for row in rows}
            self.assertEqual(by_candidate["1"]["declared_expense_centavos"], "10000")
            self.assertEqual(by_candidate["1"]["vote_observation"], "observed")
            self.assertEqual(by_candidate["1"]["valid_nominal_votes"], "3")
            self.assertEqual(by_candidate["2"]["declared_expense_centavos"], "")
            self.assertEqual(by_candidate["2"]["expense_observation"], "absent")
            self.assertEqual(by_candidate["2"]["valid_nominal_votes"], "0")
            self.assertEqual(by_candidate["2"]["vote_observation"], "observed_zero")

    def test_duplicate_expense_blocks_approval_without_silent_deduplication(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run_pipeline(self._fixture(directory, duplicate_expense=True), Path(directory) / "derived")
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["fatal_counts"]["duplicate_expense_rows"], 1)
            self.assertFalse((Path(directory) / "derived" / "analytical_base.csv").exists())

    def test_unknown_candidate_reference_blocks_relationship_integration(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run_pipeline(self._fixture(directory, unknown_expense=True), Path(directory) / "derived")
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["fatal_counts"]["unknown_expense_candidates"], 1)

    def test_missing_declared_amount_blocks_instead_of_becoming_zero(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run_pipeline(self._fixture(directory, missing_expense=True), Path(directory) / "derived")
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["fatal_counts"]["missing_expense_amount"], 1)

    def test_repeated_document_reference_keeps_distinct_expense_lines(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run_pipeline(self._fixture(directory, repeated_document=True), Path(directory) / "derived")
            self.assertEqual(result["status"], "approved")
            self.assertEqual(result["expense_grain"]["documents_with_multiple_lines"], 1)
            with (Path(directory) / "derived" / "expense_aggregate.csv").open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[0]["expense_row_count"], "2")
            self.assertEqual(rows[0]["declared_expense_centavos"], "10000")
