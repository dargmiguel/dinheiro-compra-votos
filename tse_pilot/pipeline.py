from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import sqlite3
import zipfile
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Iterable


UF_CODES = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG",
    "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
}
FEDERAL_CARGO = "deputado federal"
SOURCE_PREFIXES = {
    "candidates_2022": "consulta_cand_2022_",
    "accounts_2022": "despesas_contratadas_candidatos_2022_",
    "votes_2022": "votacao_candidato_munzona_2022_",
}


class PipelineError(RuntimeError):
    pass


def _is_selected_member(name: str, prefix: str) -> bool:
    if not name.startswith(prefix) or not name.casefold().endswith(".csv"):
        return False
    match = re.search(r"_([A-Z]{2})\.csv$", name)
    return bool(match and match.group(1) in UF_CODES)


def _iter_selected_rows(archive_path: Path, resource_key: str) -> Iterable[tuple[dict[str, str], str, int]]:
    prefix = SOURCE_PREFIXES[resource_key]
    with zipfile.ZipFile(archive_path) as archive:
        for info in sorted(archive.infolist(), key=lambda item: item.filename):
            if not _is_selected_member(info.filename, prefix):
                continue
            with archive.open(info) as raw:
                text = io.TextIOWrapper(raw, encoding="latin-1", newline="")
                reader = csv.DictReader(text, delimiter=";")
                for row_number, row in enumerate(reader, start=2):
                    yield row, info.filename, row_number
                text.detach()


def _selected_members(archive_path: Path, resource_key: str) -> tuple[list[str], list[str]]:
    prefix = SOURCE_PREFIXES[resource_key]
    with zipfile.ZipFile(archive_path) as archive:
        selected = [info.filename for info in archive.infolist() if _is_selected_member(info.filename, prefix)]
        excluded = [
            info.filename for info in archive.infolist()
            if info.filename.startswith(prefix) and info.filename.casefold().endswith(".csv") and info.filename not in selected
        ]
    return sorted(selected), sorted(excluded)


def _resource_path(manifest: dict, resource_key: str) -> Path:
    for resource in manifest["resources"]:
        if resource["resource_key"] == resource_key:
            return Path(resource["local_path"])
    raise PipelineError(f"recurso ausente no manifesto: {resource_key}")


def _missing(value: str | None) -> bool:
    return value is None or value.strip() in {"", "#NULO", "#NE"}


def _text(row: dict[str, str], field: str) -> str:
    return (row.get(field) or "").strip()


def _integer(value: str, field: str) -> int:
    if _missing(value):
        raise ValueError(f"campo ausente: {field}")
    return int(value.strip())


def _centavos(value: str) -> int:
    if _missing(value):
        raise ValueError("valor ausente")
    normalized = value.strip().replace("R$", "").replace(" ", "")
    if "," in normalized:
        normalized = normalized.replace(".", "").replace(",", ".")
    amount = Decimal(normalized).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if amount < 0:
        raise ValueError("valor negativo")
    return int(amount * 100)


def _ref(archive: Path, member: str, row_number: int) -> dict[str, object]:
    return {"source_archive": archive.name, "source_member": member, "source_row": row_number}



def _row_signature(row: dict[str, str]) -> str:
    payload = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
def _setup_database(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        PRAGMA foreign_keys = ON;
        CREATE TABLE candidates (
            sq_candidate TEXT PRIMARY KEY,
            election_year INTEGER NOT NULL,
            turn INTEGER NOT NULL,
            uf TEXT NOT NULL,
            cargo_code TEXT NOT NULL,
            cargo TEXT NOT NULL,
            candidate_number TEXT NOT NULL,
            candidate_name TEXT NOT NULL,
            source_archive TEXT NOT NULL,
            source_member TEXT NOT NULL,
            source_row INTEGER NOT NULL
        );
        CREATE TABLE candidate_duplicates (
            sq_candidate TEXT NOT NULL,
            evidence_json TEXT NOT NULL
        );
        CREATE TABLE expenses (
            sq_candidate TEXT NOT NULL,
            sq_expense TEXT NOT NULL,
            amount_centavos INTEGER NOT NULL,
            row_signature TEXT NOT NULL UNIQUE,
            source_archive TEXT NOT NULL,
            source_member TEXT NOT NULL,
            source_row INTEGER NOT NULL,
            PRIMARY KEY (source_member, source_row),
            FOREIGN KEY (sq_candidate) REFERENCES candidates (sq_candidate)
        );
        CREATE TABLE expense_duplicates (
            sq_candidate TEXT NOT NULL,
            sq_expense TEXT NOT NULL,
            evidence_json TEXT NOT NULL
        );
        CREATE TABLE votes (
            sq_candidate TEXT NOT NULL,
            municipality_code TEXT NOT NULL,
            zone TEXT NOT NULL,
            transit TEXT NOT NULL,
            valid_votes INTEGER NOT NULL,
            nominal_votes INTEGER NOT NULL,
            source_archive TEXT NOT NULL,
            source_member TEXT NOT NULL,
            source_row INTEGER NOT NULL,
            PRIMARY KEY (sq_candidate, municipality_code, zone, transit),
            FOREIGN KEY (sq_candidate) REFERENCES candidates (sq_candidate)
        );
        CREATE TABLE vote_duplicates (
            sq_candidate TEXT NOT NULL,
            municipality_code TEXT NOT NULL,
            zone TEXT NOT NULL,
            transit TEXT NOT NULL,
            evidence_json TEXT NOT NULL
        );
        CREATE TABLE relation_violations (
            relation TEXT NOT NULL,
            sq_candidate TEXT NOT NULL,
            evidence_json TEXT NOT NULL
        );
        """
    )


def _write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _load_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def run_pipeline(manifest_path: Path, output_dir: Path) -> dict:
    manifest = _load_manifest(Path(manifest_path))
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    approved_artifacts = (
        "candidates_canonical.csv",
        "expense_aggregate.csv",
        "vote_aggregate.csv",
        "analytical_base.csv",
    )
    for artifact_name in approved_artifacts:
        artifact_path = output_dir / artifact_name
        if artifact_path.exists():
            artifact_path.unlink()
    database_path = output_dir / "pilot.sqlite"
    if database_path.exists():
        database_path.unlink()

    fatal_counts = {
        "invalid_candidate_fields": 0,
        "duplicate_candidate_rows": 0,
        "invalid_expense_fields": 0,
        "missing_expense_amount": 0,
        "duplicate_expense_rows": 0,
        "invalid_vote_fields": 0,
        "missing_vote_amount": 0,
        "duplicate_vote_rows": 0,
        "unknown_expense_candidates": 0,
        "unknown_vote_candidates": 0,
    }
    evidence: dict[str, list[dict[str, object]]] = {key: [] for key in fatal_counts}
    source_details = {}
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    _setup_database(connection)

    def fatal(name: str, item: dict[str, object]) -> None:
        fatal_counts[name] += 1
        if len(evidence[name]) < 20:
            evidence[name].append(item)

    for resource_key in SOURCE_PREFIXES:
        archive = _resource_path(manifest, resource_key)
        selected, excluded = _selected_members(archive, resource_key)
        source_details[resource_key] = {
            "archive": str(archive),
            "selected_members": selected,
            "excluded_aggregate_or_document_members": excluded,
            "selected_member_count": len(selected),
        }

    candidate_archive = _resource_path(manifest, "candidates_2022")
    candidate_rows = 0
    candidate_selected = 0
    for row, member, row_number in _iter_selected_rows(candidate_archive, "candidates_2022"):
        candidate_rows += 1
        if _text(row, "ANO_ELEICAO") != "2022" or _text(row, "NR_TURNO") != "1" or _text(row, "DS_CARGO").casefold() != FEDERAL_CARGO:
            continue
        candidate_selected += 1
        required = ["SG_UF", "SQ_CANDIDATO", "NR_CANDIDATO", "NM_CANDIDATO", "CD_CARGO", "DS_CARGO"]
        if any(_missing(row.get(field)) for field in required):
            fatal("invalid_candidate_fields", {**_ref(candidate_archive, member, row_number), "reason": "required field missing"})
            continue
        candidate = {
            "sq_candidate": _text(row, "SQ_CANDIDATO"),
            "election_year": 2022,
            "turn": 1,
            "uf": _text(row, "SG_UF"),
            "cargo_code": _text(row, "CD_CARGO"),
            "cargo": _text(row, "DS_CARGO"),
            "candidate_number": _text(row, "NR_CANDIDATO"),
            "candidate_name": _text(row, "NM_CANDIDATO"),
            **_ref(candidate_archive, member, row_number),
        }
        try:
            connection.execute(
                "INSERT INTO candidates VALUES (:sq_candidate, :election_year, :turn, :uf, :cargo_code, :cargo, :candidate_number, :candidate_name, :source_archive, :source_member, :source_row)",
                candidate,
            )
        except sqlite3.IntegrityError:
            fatal("duplicate_candidate_rows", {**_ref(candidate_archive, member, row_number), "sq_candidate": candidate["sq_candidate"]})
            connection.execute(
                "INSERT INTO candidate_duplicates VALUES (?, ?)",
                (candidate["sq_candidate"], json.dumps({**_ref(candidate_archive, member, row_number), "row": candidate}, ensure_ascii=False)),
            )
    connection.commit()

    account_archive = _resource_path(manifest, "accounts_2022")
    expense_rows = 0
    expense_selected = 0
    for row, member, row_number in _iter_selected_rows(account_archive, "accounts_2022"):
        expense_rows += 1
        if _text(row, "AA_ELEICAO") != "2022" or _text(row, "ST_TURNO") != "1" or _text(row, "DS_CARGO").casefold() != FEDERAL_CARGO:
            continue
        expense_selected += 1
        reference = _ref(account_archive, member, row_number)
        sq_candidate = _text(row, "SQ_CANDIDATO")
        sq_expense = _text(row, "SQ_DESPESA")
        if _missing(sq_candidate) or _missing(sq_expense):
            fatal("invalid_expense_fields", {**reference, "reason": "candidate or expense identifier missing"})
            continue
        if not connection.execute("SELECT 1 FROM candidates WHERE sq_candidate = ?", (sq_candidate,)).fetchone():
            fatal("unknown_expense_candidates", {**reference, "sq_candidate": sq_candidate})
            connection.execute("INSERT INTO relation_violations VALUES (?, ?, ?)", ("expense", sq_candidate, json.dumps(reference)))
            continue
        amount_text = row.get("VR_DESPESA_CONTRATADA")
        if _missing(amount_text):
            fatal("missing_expense_amount", {**reference, "sq_candidate": sq_candidate, "sq_expense": sq_expense})
            continue
        try:
            amount_centavos = _centavos(amount_text)
        except (InvalidOperation, ValueError) as error:
            fatal("invalid_expense_fields", {**reference, "reason": str(error), "value": amount_text})
            continue
        expense = {
            "sq_candidate": sq_candidate,
            "sq_expense": sq_expense,
            "amount_centavos": amount_centavos,
            "row_signature": _row_signature(row),
            **reference,
        }
        try:
            connection.execute(
                "INSERT INTO expenses VALUES (:sq_candidate, :sq_expense, :amount_centavos, :row_signature, :source_archive, :source_member, :source_row)",
                expense,
            )
        except sqlite3.IntegrityError:
            existing = connection.execute(
                "SELECT source_member, source_row FROM expenses WHERE row_signature = ?",
                (expense["row_signature"],),
            ).fetchone()
            duplicate_evidence = {
                **reference,
                "sq_candidate": sq_candidate,
                "sq_expense": sq_expense,
                "row_signature": expense["row_signature"],
                "duplicate_of": dict(existing) if existing else None,
            }
            fatal("duplicate_expense_rows", duplicate_evidence)
            connection.execute(
                "INSERT INTO expense_duplicates VALUES (?, ?, ?)",
                (sq_candidate, sq_expense, json.dumps({**expense, "duplicate_of": dict(existing) if existing else None}, ensure_ascii=False)),
            )
    connection.commit()

    vote_archive = _resource_path(manifest, "votes_2022")
    vote_rows = 0
    vote_selected = 0
    for row, member, row_number in _iter_selected_rows(vote_archive, "votes_2022"):
        vote_rows += 1
        if _text(row, "ANO_ELEICAO") != "2022" or _text(row, "NR_TURNO") != "1" or _text(row, "DS_CARGO").casefold() != FEDERAL_CARGO:
            continue
        vote_selected += 1
        reference = _ref(vote_archive, member, row_number)
        sq_candidate = _text(row, "SQ_CANDIDATO")
        municipality = _text(row, "CD_MUNICIPIO")
        zone = _text(row, "NR_ZONA")
        transit = _text(row, "ST_VOTO_EM_TRANSITO")
        if any(_missing(value) for value in (sq_candidate, municipality, zone, transit)):
            fatal("invalid_vote_fields", {**reference, "reason": "vote grain field missing"})
            continue
        if not connection.execute("SELECT 1 FROM candidates WHERE sq_candidate = ?", (sq_candidate,)).fetchone():
            fatal("unknown_vote_candidates", {**reference, "sq_candidate": sq_candidate})
            connection.execute("INSERT INTO relation_violations VALUES (?, ?, ?)", ("vote", sq_candidate, json.dumps(reference)))
            continue
        valid_text = row.get("QT_VOTOS_NOMINAIS_VALIDOS")
        nominal_text = row.get("QT_VOTOS_NOMINAIS")
        if _missing(valid_text) or _missing(nominal_text):
            fatal("missing_vote_amount", {**reference, "sq_candidate": sq_candidate})
            continue
        try:
            valid_votes = _integer(valid_text, "QT_VOTOS_NOMINAIS_VALIDOS")
            nominal_votes = _integer(nominal_text, "QT_VOTOS_NOMINAIS")
            if valid_votes < 0 or nominal_votes < 0 or valid_votes > nominal_votes:
                raise ValueError("vote count outside 0 <= valid <= nominal")
        except ValueError as error:
            fatal("invalid_vote_fields", {**reference, "reason": str(error), "sq_candidate": sq_candidate})
            continue
        vote = {
            "sq_candidate": sq_candidate,
            "municipality_code": municipality,
            "zone": zone,
            "transit": transit,
            "valid_votes": valid_votes,
            "nominal_votes": nominal_votes,
            **reference,
        }
        try:
            connection.execute(
                "INSERT INTO votes VALUES (:sq_candidate, :municipality_code, :zone, :transit, :valid_votes, :nominal_votes, :source_archive, :source_member, :source_row)",
                vote,
            )
        except sqlite3.IntegrityError:
            fatal("duplicate_vote_rows", {**reference, "sq_candidate": sq_candidate, "municipality_code": municipality, "zone": zone, "transit": transit})
            connection.execute(
                "INSERT INTO vote_duplicates VALUES (?, ?, ?, ?, ?)",
                (sq_candidate, municipality, zone, transit, json.dumps(vote, ensure_ascii=False)),
            )
    connection.commit()

    source_counts = {
        "candidate_rows_read": candidate_rows,
        "candidate_rows_selected": candidate_selected,
        "candidate_rows_canonical": connection.execute("SELECT COUNT(*) FROM candidates").fetchone()[0],
        "expense_rows_read": expense_rows,
        "expense_rows_selected": expense_selected,
        "expense_rows_canonical": connection.execute("SELECT COUNT(*) FROM expenses").fetchone()[0],
        "vote_rows_read": vote_rows,
        "vote_rows_selected": vote_selected,
        "vote_rows_canonical": connection.execute("SELECT COUNT(*) FROM votes").fetchone()[0],
    }

    repeated_expense_documents = connection.execute(
        "SELECT COUNT(*) FROM (SELECT sq_candidate, sq_expense FROM expenses GROUP BY sq_candidate, sq_expense HAVING COUNT(*) > 1)"
    ).fetchone()[0]
    validation = {
        "schema_version": 1,
        "manifest_id": manifest.get("manifest_id"),
        "scope": "Brasil / todas as UFs",
        "target": {"election_year": 2022, "turn": 1, "cargo": "Deputado Federal"},
        "expense_measure": "VR_DESPESA_CONTRATADA, em centavos de real; soma de todas as linhas selecionadas de despesas_contratadas por UF",
        "expense_grain": {
            "row_identity": "(source_member, source_row)",
            "document_reference": "SQ_DESPESA",
            "documents_with_multiple_lines": repeated_expense_documents,
        },
        "vote_measure": "QT_VOTOS_NOMINAIS_VALIDOS, agregado por SQ_CANDIDATO, município, zona e trânsito",
        "source_details": source_details,
        "source_counts": source_counts,
        "fatal_counts": fatal_counts,
        "evidence": evidence,
    }

    if not any(fatal_counts.values()):
        connection.executescript(
            """
            CREATE VIEW expense_aggregate AS
            SELECT sq_candidate, COUNT(*) AS expense_row_count, SUM(amount_centavos) AS declared_expense_centavos,
                   COUNT(DISTINCT source_member) AS expense_source_member_count
            FROM expenses GROUP BY sq_candidate;
            CREATE VIEW vote_aggregate AS
            SELECT sq_candidate, COUNT(*) AS vote_row_count, SUM(valid_votes) AS valid_nominal_votes,
                   SUM(nominal_votes) AS nominal_votes, COUNT(DISTINCT source_member) AS vote_source_member_count
            FROM votes GROUP BY sq_candidate;
            """
        )
        expense_source_total = tuple(connection.execute("SELECT COUNT(*) AS row_count, COALESCE(SUM(amount_centavos), 0) AS total_centavos FROM expenses").fetchone())
        expense_aggregate_total = tuple(connection.execute("SELECT COALESCE(SUM(expense_row_count), 0) AS row_count, COALESCE(SUM(declared_expense_centavos), 0) AS total_centavos FROM expense_aggregate").fetchone())
        vote_source_total = tuple(connection.execute("SELECT COUNT(*) AS row_count, COALESCE(SUM(valid_votes), 0) AS total_votes FROM votes").fetchone())
        vote_aggregate_total = tuple(connection.execute("SELECT COALESCE(SUM(vote_row_count), 0) AS row_count, COALESCE(SUM(valid_nominal_votes), 0) AS total_votes FROM vote_aggregate").fetchone())
        reconciliation = {
            "expense_rows_source_vs_aggregate": [expense_source_total[0], expense_aggregate_total[0]],
            "expense_centavos_source_vs_aggregate": [expense_source_total[1], expense_aggregate_total[1]],
            "vote_rows_source_vs_aggregate": [vote_source_total[0], vote_aggregate_total[0]],
            "vote_valid_votes_source_vs_aggregate": [vote_source_total[1], vote_aggregate_total[1]],
        }
        validation["reconciliation"] = reconciliation
        if expense_source_total != expense_aggregate_total:
            fatal("invalid_expense_fields", {"reason": "expense aggregate reconciliation failed"})
        if vote_source_total != vote_aggregate_total:
            fatal("invalid_vote_fields", {"reason": "vote aggregate reconciliation failed"})

    if any(fatal_counts.values()):
        validation["status"] = "blocked"
        validation["blocking_rule"] = "A base analítica não é emitida enquanto houver erro crítico, duplicidade ou relação sem candidato canônico."
        (output_dir / "validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        connection.commit()
        connection.close()
        return validation

    candidate_count = connection.execute("SELECT COUNT(*) FROM candidates").fetchone()[0]
    expense_missing = connection.execute("SELECT COUNT(*) FROM candidates c LEFT JOIN expense_aggregate e USING (sq_candidate) WHERE e.sq_candidate IS NULL").fetchone()[0]
    vote_missing = connection.execute("SELECT COUNT(*) FROM candidates c LEFT JOIN vote_aggregate v USING (sq_candidate) WHERE v.sq_candidate IS NULL").fetchone()[0]
    validation["warnings"] = {
        "candidates_without_expense_rows": expense_missing,
        "candidates_without_vote_rows": vote_missing,
        "absence_is_not_zero": True,
    }
    validation["reconciliation"] = validation.get("reconciliation", {})
    validation["status"] = "approved"
    validation["analytical_candidate_count"] = candidate_count

    _write_csv(
        output_dir / "candidates_canonical.csv",
        ["sq_candidate", "election_year", "turn", "uf", "cargo_code", "cargo", "candidate_number", "candidate_name", "source_archive", "source_member", "source_row"],
        (dict(row) for row in connection.execute("SELECT * FROM candidates ORDER BY uf, candidate_number, sq_candidate")),
    )
    _write_csv(
        output_dir / "expense_aggregate.csv",
        ["sq_candidate", "expense_row_count", "declared_expense_centavos", "expense_source_member_count"],
        (dict(row) for row in connection.execute("SELECT * FROM expense_aggregate ORDER BY sq_candidate")),
    )
    _write_csv(
        output_dir / "vote_aggregate.csv",
        ["sq_candidate", "vote_row_count", "valid_nominal_votes", "nominal_votes", "vote_source_member_count"],
        (dict(row) for row in connection.execute("SELECT * FROM vote_aggregate ORDER BY sq_candidate")),
    )
    analytical_query = """
        SELECT c.sq_candidate, c.election_year, c.turn, c.uf, c.cargo_code, c.cargo,
               c.candidate_number, c.candidate_name, c.source_archive AS candidate_source_archive,
               c.source_member AS candidate_source_member, c.source_row AS candidate_source_row,
               e.expense_row_count, e.declared_expense_centavos,
               CASE WHEN e.sq_candidate IS NULL THEN 'absent' WHEN e.declared_expense_centavos = 0 THEN 'observed_zero' ELSE 'observed' END AS expense_observation,
               e.expense_source_member_count, v.vote_row_count, v.valid_nominal_votes, v.nominal_votes,
               CASE WHEN v.sq_candidate IS NULL THEN 'absent' WHEN v.valid_nominal_votes = 0 THEN 'observed_zero' ELSE 'observed' END AS vote_observation,
               v.vote_source_member_count
        FROM candidates c
        LEFT JOIN expense_aggregate e USING (sq_candidate)
        LEFT JOIN vote_aggregate v USING (sq_candidate)
        ORDER BY c.uf, c.candidate_number, c.sq_candidate
    """
    rows = []
    cursor = connection.execute(analytical_query)
    fieldnames = [column[0] for column in cursor.description]
    for row in cursor:
        item = dict(row)
        for key in ("expense_row_count", "declared_expense_centavos", "expense_source_member_count", "vote_row_count", "valid_nominal_votes", "nominal_votes", "vote_source_member_count"):
            if item[key] is None:
                item[key] = ""
        rows.append(item)
    _write_csv(output_dir / "analytical_base.csv", fieldnames, rows)
    validation["analytical_rows"] = len(rows)
    (output_dir / "validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    connection.commit()
    connection.close()
    return validation
