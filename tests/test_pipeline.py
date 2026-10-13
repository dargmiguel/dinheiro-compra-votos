import csv
import json
import sqlite3
import tempfile
import unittest
import zipfile
from pathlib import Path

from tse_pilot.duplicates import analyze_duplicate_expenses
from tse_pilot.pipeline import materialize_deduplicated_expenses, run_pipeline


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

    def _manifest(self, directory, candidates, accounts, votes, party_votes):
        resources = []
        for key, path in (
            ("candidates_2022", candidates),
            ("accounts_2022", accounts),
            ("votes_2022", votes),
            ("vote_totals_2022", party_votes),
        ):
            resources.append({"resource_key": key, "local_path": str(path)})
        manifest = {"manifest_id": "fixture", "election": 2022, "resources": resources}
        path = Path(directory) / "manifest.json"
        path.write_text(json.dumps(manifest), encoding="utf-8")
        return path

    def _fixture(self, directory, duplicate_expense=False, unknown_expense=False, missing_expense=False, repeated_document=False, same_expense_in_other_member=False, unknown_vote=False, different_source_field=False):
        candidate_columns = ["ANO_ELEICAO", "NR_TURNO", "SG_UF", "CD_CARGO", "DS_CARGO", "SQ_CANDIDATO", "NR_CANDIDATO", "NM_CANDIDATO", "CD_SITUACAO_CANDIDATURA", "NR_PARTIDO", "DT_NASCIMENTO", "DS_GENERO", "DS_COR_RACA", "DS_GRAU_INSTRUCAO"]
        candidates = [
            {"ANO_ELEICAO": "2022", "NR_TURNO": "1", "SG_UF": "SP", "CD_CARGO": "6", "DS_CARGO": "Deputado Federal", "SQ_CANDIDATO": "1", "NR_CANDIDATO": "1001", "NM_CANDIDATO": "A", "CD_SITUACAO_CANDIDATURA": "12", "NR_PARTIDO": "10", "DT_NASCIMENTO": "1980-01-01", "DS_GENERO": "FEMININO", "DS_COR_RACA": "BRANCA", "DS_GRAU_INSTRUCAO": "SUPERIOR COMPLETO"},
            {"ANO_ELEICAO": "2022", "NR_TURNO": "1", "SG_UF": "SP", "CD_CARGO": "6", "DS_CARGO": "Deputado Federal", "SQ_CANDIDATO": "2", "NR_CANDIDATO": "1002", "NM_CANDIDATO": "B", "CD_SITUACAO_CANDIDATURA": "3", "NR_PARTIDO": "20", "DT_NASCIMENTO": "1975-01-01", "DS_GENERO": "MASCULINO", "DS_COR_RACA": "PARDA", "DS_GRAU_INSTRUCAO": "ENSINO MÉDIO COMPLETO"},
            {"ANO_ELEICAO": "2022", "NR_TURNO": "1", "SG_UF": "SP", "CD_CARGO": "7", "DS_CARGO": "Deputado Estadual", "SQ_CANDIDATO": "3", "NR_CANDIDATO": "1003", "NM_CANDIDATO": "C", "CD_SITUACAO_CANDIDATURA": "12", "NR_PARTIDO": "30", "DT_NASCIMENTO": "1990-01-01", "DS_GENERO": "MASCULINO", "DS_COR_RACA": "BRANCA", "DS_GRAU_INSTRUCAO": "SUPERIOR COMPLETO"},
        ]
        account_columns = [
            "DT_GERACAO", "HH_GERACAO", "AA_ELEICAO", "CD_TIPO_ELEICAO", "NM_TIPO_ELEICAO",
            "CD_ELEICAO", "DS_ELEICAO", "DT_ELEICAO", "ST_TURNO", "TP_PRESTACAO_CONTAS",
            "DT_PRESTACAO_CONTAS", "SQ_PRESTADOR_CONTAS", "SG_UF", "SG_UE", "NM_UE",
            "NR_CNPJ_PRESTADOR_CONTA", "CD_CARGO", "DS_CARGO", "SQ_CANDIDATO", "NR_CANDIDATO",
            "NM_CANDIDATO", "NR_CPF_CANDIDATO", "NR_CPF_VICE_CANDIDATO", "NR_PARTIDO", "SG_PARTIDO",
            "NM_PARTIDO", "CD_TIPO_FORNECEDOR", "DS_TIPO_FORNECEDOR", "CD_CNAE_FORNECEDOR",
            "DS_CNAE_FORNECEDOR", "NR_CPF_CNPJ_FORNECEDOR", "NM_FORNECEDOR", "NM_FORNECEDOR_RFB",
            "CD_ESFERA_PART_FORNECEDOR", "DS_ESFERA_PART_FORNECEDOR", "SG_UF_FORNECEDOR",
            "CD_MUNICIPIO_FORNECEDOR", "NM_MUNICIPIO_FORNECEDOR", "SQ_CANDIDATO_FORNECEDOR",
            "NR_CANDIDATO_FORNECEDOR", "CD_CARGO_FORNECEDOR", "DS_CARGO_FORNECEDOR",
            "NR_PARTIDO_FORNECEDOR", "SG_PARTIDO_FORNECEDOR", "NM_PARTIDO_FORNECEDOR",
            "DS_TIPO_DOCUMENTO", "NR_DOCUMENTO", "CD_ORIGEM_DESPESA", "DS_ORIGEM_DESPESA",
            "SQ_DESPESA", "DT_DESPESA", "DS_DESPESA", "VR_DESPESA_CONTRATADA",
        ]
        expenses = [
            {"AA_ELEICAO": "2022", "ST_TURNO": "1", "SG_UF": "SP", "CD_CARGO": "6", "DS_CARGO": "Deputado Federal", "SQ_CANDIDATO": "1", "SQ_DESPESA": "10", "VR_DESPESA_CONTRATADA": "100,00", "NR_DOCUMENTO": "493", "DS_DESPESA": "PANFLETOS"},
            {"AA_ELEICAO": "2022", "ST_TURNO": "1", "SG_UF": "SP", "CD_CARGO": "6", "DS_CARGO": "Deputado Federal", "SQ_CANDIDATO": "1", "SQ_DESPESA": "11", "VR_DESPESA_CONTRATADA": "0,00", "NR_DOCUMENTO": "494", "DS_DESPESA": "SANTINHO"},
        ]
        if duplicate_expense:
            expenses.append(expenses[0].copy())
        if different_source_field:
            expenses.append({**expenses[0], "DS_TIPO_DOCUMENTO": "Nota Fiscal"})
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
        if unknown_vote:
            votes.append({**votes[0], "SQ_CANDIDATO": "99", "CD_MUNICIPIO": "2"})
        candidates_path = self._write_archive(directory, "candidates.zip", [("consulta_cand_2022_SP.csv", candidate_columns, candidates)])
        account_members = [("despesas_contratadas_candidatos_2022_SP.csv", account_columns, expenses)]
        if same_expense_in_other_member:
            account_members.append(("despesas_contratadas_candidatos_2022_RJ.csv", account_columns, [expenses[0].copy()]))
        accounts_path = self._write_archive(directory, "accounts.zip", account_members)
        votes_path = self._write_archive(directory, "votes.zip", [("votacao_candidato_munzona_2022_SP.csv", vote_columns, votes)])
        party_columns = ["ANO_ELEICAO", "NR_TURNO", "SG_UF", "CD_CARGO", "DS_CARGO", "NR_PARTIDO", "CD_MUNICIPIO", "NR_ZONA", "QT_VOTOS_NOMINAIS_VALIDOS", "QT_VOTOS_LEGENDA_VALIDOS", "QT_VOTOS_NOM_CONVR_LEG_VALIDOS", "QT_TOTAL_VOTOS_LEG_VALIDOS"]
        party_votes = [
            {"ANO_ELEICAO": "2022", "NR_TURNO": "1", "SG_UF": "SP", "CD_CARGO": "6", "DS_CARGO": "Deputado Federal", "NR_PARTIDO": "10", "CD_MUNICIPIO": "1", "NR_ZONA": "10", "QT_VOTOS_NOMINAIS_VALIDOS": "3", "QT_VOTOS_LEGENDA_VALIDOS": "1", "QT_VOTOS_NOM_CONVR_LEG_VALIDOS": "0", "QT_TOTAL_VOTOS_LEG_VALIDOS": "1"},
            {"ANO_ELEICAO": "2022", "NR_TURNO": "1", "SG_UF": "SP", "CD_CARGO": "6", "DS_CARGO": "Deputado Federal", "NR_PARTIDO": "20", "CD_MUNICIPIO": "1", "NR_ZONA": "11", "QT_VOTOS_NOMINAIS_VALIDOS": "0", "QT_VOTOS_LEGENDA_VALIDOS": "2", "QT_VOTOS_NOM_CONVR_LEG_VALIDOS": "0", "QT_TOTAL_VOTOS_LEG_VALIDOS": "2"},
            {"ANO_ELEICAO": "2022", "NR_TURNO": "2", "SG_UF": "SP", "CD_CARGO": "6", "DS_CARGO": "Deputado Federal", "NR_PARTIDO": "10", "CD_MUNICIPIO": "1", "NR_ZONA": "10", "QT_VOTOS_NOMINAIS_VALIDOS": "1000", "QT_VOTOS_LEGENDA_VALIDOS": "1000", "QT_VOTOS_NOM_CONVR_LEG_VALIDOS": "0", "QT_TOTAL_VOTOS_LEG_VALIDOS": "1000"},
            {"ANO_ELEICAO": "2022", "NR_TURNO": "1", "SG_UF": "SP", "CD_CARGO": "7", "DS_CARGO": "Deputado Estadual", "NR_PARTIDO": "10", "CD_MUNICIPIO": "1", "NR_ZONA": "10", "QT_VOTOS_NOMINAIS_VALIDOS": "1000", "QT_VOTOS_LEGENDA_VALIDOS": "1000", "QT_VOTOS_NOM_CONVR_LEG_VALIDOS": "0", "QT_TOTAL_VOTOS_LEG_VALIDOS": "1000"},
        ]
        party_path = self._write_archive(directory, "party-votes.zip", [("votacao_partido_munzona_2022_BRASIL.csv", party_columns, party_votes)])
        return self._manifest(directory, candidates_path, accounts_path, votes_path, party_path)

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

    def test_raw_expense_occurrences_keep_full_rows_and_source_references(self):
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory) / "derived"
            result = run_pipeline(self._fixture(directory, duplicate_expense=True), output_dir)
            self.assertEqual(result["status"], "approved")
            self.assertEqual(result["source_counts"]["expense_occurrence_rows_stored"], 3)

            connection = sqlite3.connect(output_dir / "pilot.sqlite")
            rows = connection.execute(
                """
                SELECT SQ_CANDIDATO, SQ_DESPESA, NR_DOCUMENTO, DS_DESPESA,
                       VR_DESPESA_CONTRATADA, _source_member, _source_row, _row_signature
                FROM expense_occurrences
                WHERE SQ_CANDIDATO = '1' AND SQ_DESPESA = '10'
                ORDER BY _source_row
                """
            ).fetchall()
            connection.close()

            self.assertEqual(len(rows), 2)
            self.assertEqual([row[3] for row in rows], ["PANFLETOS", "PANFLETOS"])
            self.assertEqual([row[5] for row in rows], [
                "despesas_contratadas_candidatos_2022_SP.csv",
                "despesas_contratadas_candidatos_2022_SP.csv",
            ])
            self.assertEqual([row[6] for row in rows], [2, 4])
            self.assertEqual(rows[0][7], rows[1][7])
            self.assertEqual([row[4] for row in rows], ["100,00", "100,00"])

    def test_exact_duplicate_is_primary_and_excluded_occurrence_is_audited_idempotently(self):
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory) / "derived"
            result = run_pipeline(self._fixture(directory, duplicate_expense=True), output_dir)
            self.assertEqual(result["status"], "approved")
            self.assertEqual(result["expense_deduplication"]["source_field_count"], 53)
            self.assertEqual(result["expense_deduplication"]["excluded_rows"], 1)
            self.assertEqual(result["expense_deduplication"]["affected_candidates"], 1)
            self.assertEqual(result["expense_deduplication"]["financial_difference_centavos"], 10000)
            diagnostic = analyze_duplicate_expenses(output_dir / "pilot.sqlite")
            self.assertEqual(diagnostic["rows_excluded"], 1)
            self.assertTrue((output_dir / "analytical_base.csv").exists())

            connection = sqlite3.connect(output_dir / "pilot.sqlite")
            raw_count = connection.execute("SELECT COUNT(*) FROM expense_occurrences").fetchone()[0]
            primary_rows = connection.execute(
                "SELECT COUNT(*) FROM expenses WHERE sq_candidate = '1' AND sq_expense = '10'"
            ).fetchone()[0]
            excluded = connection.execute(
                """
                SELECT snapshot_id, source_member, source_row, kept_source_member, kept_source_row
                FROM expense_dedup_exclusions
                """
            ).fetchone()
            before = connection.execute(
                "SELECT sq_candidate, sq_expense, amount_centavos, source_member, source_row FROM expenses ORDER BY source_member, source_row"
            ).fetchall()
            excluded_before = connection.execute(
                "SELECT source_member, source_row, kept_source_member, kept_source_row FROM expense_dedup_exclusions ORDER BY source_member, source_row"
            ).fetchall()
            first_result = materialize_deduplicated_expenses(connection, "fixture")
            second_result = materialize_deduplicated_expenses(connection, "fixture")
            after = connection.execute(
                "SELECT sq_candidate, sq_expense, amount_centavos, source_member, source_row FROM expenses ORDER BY source_member, source_row"
            ).fetchall()
            excluded_after = connection.execute(
                "SELECT source_member, source_row, kept_source_member, kept_source_row FROM expense_dedup_exclusions ORDER BY source_member, source_row"
            ).fetchall()
            connection.close()

            self.assertEqual(raw_count, 3)
            self.assertEqual(primary_rows, 1)
            self.assertEqual(excluded, ("fixture", "despesas_contratadas_candidatos_2022_SP.csv", 4, "despesas_contratadas_candidatos_2022_SP.csv", 2))
            self.assertEqual(first_result, second_result)
            self.assertEqual(before, after)
            self.assertEqual(excluded_before, excluded_after)

    def test_different_original_field_prevents_exact_deduplication(self):
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory) / "derived"
            result = run_pipeline(
                self._fixture(directory, different_source_field=True),
                output_dir,
            )
            self.assertEqual(result["expense_deduplication"]["source_field_count"], 53)
            self.assertEqual(result["expense_deduplication"]["excluded_rows"], 0)
            connection = sqlite3.connect(output_dir / "pilot.sqlite")
            rows = connection.execute(
                "SELECT COUNT(*) FROM expenses WHERE sq_candidate = '1' AND sq_expense = '10'"
            ).fetchone()[0]
            connection.close()
            self.assertEqual(rows, 2)

    def test_exact_rows_in_different_source_members_are_not_deduplicated(self):
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory) / "derived"
            result = run_pipeline(
                self._fixture(directory, same_expense_in_other_member=True),
                output_dir,
            )
            self.assertEqual(result["status"], "approved")
            connection = sqlite3.connect(output_dir / "pilot.sqlite")
            rows = connection.execute(
                "SELECT source_member, source_row FROM expenses WHERE sq_candidate = '1' AND sq_expense = '10' ORDER BY source_member"
            ).fetchall()
            connection.close()
            self.assertEqual(rows, [
                ("despesas_contratadas_candidatos_2022_RJ.csv", 2),
                ("despesas_contratadas_candidatos_2022_SP.csv", 2),
            ])

    def test_duplicate_expense_is_not_a_blocker_but_other_validation_errors_remain_blocking(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run_pipeline(self._fixture(directory, duplicate_expense=True), Path(directory) / "derived")
            self.assertEqual(result["status"], "approved")
            self.assertNotIn("duplicate_expense_rows", result["fatal_counts"])

            blocked = run_pipeline(
                self._fixture(directory, duplicate_expense=True, unknown_expense=True),
                Path(directory) / "derived",
            )
            self.assertEqual(blocked["status"], "blocked")
            self.assertEqual(blocked["fatal_counts"]["unknown_expense_candidates"], 1)

    def test_official_denominator_includes_legend_and_is_reconciled_before_candidate_filters(self):
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory) / "derived"
            result = run_pipeline(self._fixture(directory), output_dir)

            self.assertEqual(result["status"], "approved")
            self.assertEqual(result["vote_denominator"]["uf_count"], 1)
            self.assertEqual(result["vote_denominator"]["selected_rows"], 2)
            self.assertEqual(result["reconciliation"]["nominal_votes_by_uf"], {"SP": {"party_source": 3, "candidate_source": 3}})
            with (output_dir / "vote_denominator_by_uf.csv").open(encoding="utf-8", newline="") as handle:
                totals = list(csv.DictReader(handle))
            self.assertEqual(totals, [{
                "uf": "SP",
                "election_year": "2022",
                "turn": "1",
                "cargo_code": "6",
                "cargo": "Deputado Federal",
                "valid_nominal_votes": "3",
                "valid_legend_votes": "3",
                "valid_votes_total": "6",
                "source_row_count": "2",
                "source_archive": "party-votes.zip",
                "source_member": "votacao_partido_munzona_2022_BRASIL.csv",
            }])
            with (output_dir / "analytical_base.csv").open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual({row["official_valid_votes"] for row in rows}, {"6"})
            self.assertEqual({row["vote_share"] for row in rows}, {"0.5", "0.0"})

    def test_blocked_run_removes_approved_artifacts_from_prior_run(self):
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory) / "derived"
            approved = run_pipeline(self._fixture(directory), output_dir)
            self.assertEqual(approved["status"], "approved")
            approved_files = (
                "candidates_canonical.csv",
                "expense_aggregate.csv",
                "vote_aggregate.csv",
                "analytical_base.csv",
            )
            self.assertTrue(all((output_dir / name).exists() for name in approved_files))

            blocked = run_pipeline(self._fixture(directory, unknown_expense=True), output_dir)
            self.assertEqual(blocked["status"], "blocked")
            self.assertTrue(all(not (output_dir / name).exists() for name in approved_files))

    def test_unknown_candidate_reference_blocks_relationship_integration(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run_pipeline(self._fixture(directory, unknown_expense=True), Path(directory) / "derived")
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["fatal_counts"]["unknown_expense_candidates"], 1)

    def test_unknown_vote_candidate_reference_blocks_relationship_integration(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run_pipeline(self._fixture(directory, unknown_vote=True), Path(directory) / "derived")
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["fatal_counts"]["unknown_vote_candidates"], 1)

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
