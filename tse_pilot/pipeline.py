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

def _iter_member_rows(archive_path: Path, member_name: str) -> Iterable[tuple[dict[str, str], int]]:
    with zipfile.ZipFile(archive_path) as archive:
        try:
            info = archive.getinfo(member_name)
        except KeyError as error:
            raise PipelineError(f"membro oficial ausente no ZIP: {member_name}") from error
        with archive.open(info) as raw:
            text = io.TextIOWrapper(raw, encoding="latin-1", newline="")
            reader = csv.DictReader(text, delimiter=";")
            for row_number, row in enumerate(reader, start=2):
                yield row, row_number
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


def _quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _create_expense_occurrences(connection: sqlite3.Connection, source_columns: list[str]) -> None:
    columns = ", ".join(f"{_quote_identifier(column)} TEXT" for column in source_columns)
    connection.execute(
        f"""
        CREATE TABLE expense_occurrences (
            {columns},
            _source_archive TEXT NOT NULL,
            _source_member TEXT NOT NULL,
            _source_row INTEGER NOT NULL,
            _row_signature TEXT NOT NULL,
            PRIMARY KEY (_source_member, _source_row)
        )
        """
    )
    connection.execute(
        "CREATE INDEX idx_expense_occurrences_candidate_expense "
        "ON expense_occurrences (SQ_CANDIDATO, SQ_DESPESA)"
    )
    connection.execute(
        "CREATE INDEX idx_expense_occurrences_signature "
        "ON expense_occurrences (_row_signature)"
    )


def _insert_expense_occurrence(
    connection: sqlite3.Connection,
    source_columns: list[str],
    row: dict[str, str],
    archive: Path,
    member: str,
    row_number: int,
) -> None:
    columns = [*source_columns, "_source_archive", "_source_member", "_source_row", "_row_signature"]
    values = [row.get(column) for column in source_columns]
    values.extend([archive.name, member, row_number, _row_signature(row)])
    placeholders = ", ".join("?" for _ in columns)
    quoted_columns = ", ".join(_quote_identifier(column) for column in columns)
    connection.execute(
        f"INSERT INTO expense_occurrences ({quoted_columns}) VALUES ({placeholders})",
        values,
    )

def materialize_deduplicated_expenses(
    connection: sqlite3.Connection,
    snapshot_id: str,
) -> dict[str, object]:
    audit_columns = {"_source_archive", "_source_member", "_source_row", "_row_signature"}
    table_exists = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'expense_occurrences'"
    ).fetchone()
    source_columns = []
    if table_exists:
        source_columns = [
            row[1]
            for row in connection.execute("PRAGMA table_info(expense_occurrences)")
            if row[1] not in audit_columns
        ]

    had_expense_view = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'view' AND name = 'expense_aggregate'"
    ).fetchone() is not None
    connection.execute("DROP VIEW IF EXISTS expense_aggregate")
    connection.execute("DROP TABLE IF EXISTS expenses")
    connection.executescript(
        """
        CREATE TABLE expenses (
            sq_candidate TEXT NOT NULL,
            sq_expense TEXT NOT NULL,
            amount_centavos INTEGER NOT NULL,
            row_signature TEXT NOT NULL,
            snapshot_id TEXT NOT NULL,
            source_archive TEXT NOT NULL,
            source_member TEXT NOT NULL,
            source_row INTEGER NOT NULL,
            PRIMARY KEY (source_member, source_row),
            FOREIGN KEY (sq_candidate) REFERENCES candidates (sq_candidate)
        );
        CREATE INDEX idx_expenses_snapshot_member_signature
            ON expenses (snapshot_id, source_member, row_signature);
        CREATE TABLE IF NOT EXISTS expense_dedup_exclusions (
            snapshot_id TEXT NOT NULL,
            source_archive TEXT NOT NULL,
            source_member TEXT NOT NULL,
            source_row INTEGER NOT NULL,
            row_signature TEXT NOT NULL,
            kept_source_archive TEXT NOT NULL,
            kept_source_member TEXT NOT NULL,
            kept_source_row INTEGER NOT NULL,
            sq_candidate TEXT NOT NULL,
            sq_expense TEXT NOT NULL,
            amount_centavos INTEGER NOT NULL,
            PRIMARY KEY (snapshot_id, source_member, source_row)
        );
        """
    )
    connection.execute("DELETE FROM expense_duplicates")
    connection.execute("DELETE FROM expense_dedup_exclusions")

    candidate_ids = {
        row[0] for row in connection.execute("SELECT sq_candidate FROM candidates")
    }
    if table_exists:
        quoted_fields = ", ".join(_quote_identifier(field) for field in source_columns)
        selected_fields = f"{quoted_fields}, " if quoted_fields else ""
        cursor = connection.execute(
            f"""
            SELECT {selected_fields}_source_archive, _source_member, _source_row, _row_signature
            FROM expense_occurrences
            ORDER BY _source_member, _source_row
            """
        )
        names = [column[0] for column in cursor.description]
        insert_rows = []

        for values in cursor:
            row = dict(zip(names, values))
            candidate_id = _text(row, "SQ_CANDIDATO")
            expense_id = _text(row, "SQ_DESPESA")
            if _missing(candidate_id) or _missing(expense_id) or candidate_id not in candidate_ids:
                continue
            try:
                amount_centavos = _centavos(row.get("VR_DESPESA_CONTRATADA"))
            except (InvalidOperation, ValueError):
                continue

            insert_rows.append(
                (
                    candidate_id,
                    expense_id,
                    amount_centavos,
                    row["_row_signature"],
                    snapshot_id,
                    row["_source_archive"],
                    row["_source_member"],
                    row["_source_row"],
                )
            )
            if len(insert_rows) == 5000:
                connection.executemany("INSERT INTO expenses VALUES (?, ?, ?, ?, ?, ?, ?, ?)", insert_rows)
                insert_rows.clear()
        if insert_rows:
            connection.executemany("INSERT INTO expenses VALUES (?, ?, ?, ?, ?, ?, ?, ?)", insert_rows)

    duplicate_groups = connection.execute(
        """
        SELECT source_member, row_signature
        FROM expenses
        WHERE snapshot_id = ?
        GROUP BY source_member, row_signature
        HAVING COUNT(*) > 1
        ORDER BY source_member, row_signature
        """,
        (snapshot_id,),
    )
    quoted_fields = ", ".join(f"o.{_quote_identifier(field)}" for field in source_columns)
    selected_fields = f", {quoted_fields}" if quoted_fields else ""
    excluded_rows = []
    duplicate_rows = []
    deleted_rows = []
    affected_candidates: set[str] = set()

    for source_member, signature in duplicate_groups:
        rows = connection.execute(
            f"""
            SELECT e.source_archive, e.source_member, e.source_row, e.sq_candidate,
                   e.sq_expense, e.amount_centavos, e.row_signature{selected_fields}
            FROM expenses AS e
            JOIN expense_occurrences AS o
              ON o._source_member = e.source_member AND o._source_row = e.source_row
            WHERE e.snapshot_id = ? AND e.source_member = ? AND e.row_signature = ?
            ORDER BY e.source_row
            """,
            (snapshot_id, source_member, signature),
        )
        kept_by_values = {}
        for row in rows:
            raw_values = tuple(row[7:])
            kept = kept_by_values.get(raw_values)
            if kept is None:
                kept_by_values[raw_values] = row[:3]
                continue

            archive, member, source_row, candidate_id, expense_id, amount_centavos, row_signature = row[:7]
            kept_archive, kept_member, kept_row = kept
            affected_candidates.add(candidate_id)
            excluded_rows.append(
                (
                    snapshot_id,
                    archive,
                    member,
                    source_row,
                    row_signature,
                    kept_archive,
                    kept_member,
                    kept_row,
                    candidate_id,
                    expense_id,
                    amount_centavos,
                )
            )
            duplicate_rows.append(
                (
                    candidate_id,
                    expense_id,
                    json.dumps(
                        {
                            "sq_candidate": candidate_id,
                            "sq_expense": expense_id,
                            "snapshot_id": snapshot_id,
                            "row_signature": row_signature,
                            "amount_centavos": amount_centavos,
                            "source_archive": archive,
                            "source_member": member,
                            "source_row": source_row,
                            "duplicate_of": {
                                "source_archive": kept_archive,
                                "source_member": kept_member,
                                "source_row": kept_row,
                            },
                        },
                        ensure_ascii=False,
                    ),
                )
            )
            deleted_rows.append((member, source_row))

    if excluded_rows:
        connection.executemany(
            "INSERT INTO expense_dedup_exclusions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            excluded_rows,
        )
        connection.executemany(
            "INSERT INTO expense_duplicates VALUES (?, ?, ?)",
            duplicate_rows,
        )
        connection.executemany(
            "DELETE FROM expenses WHERE source_member = ? AND source_row = ?",
            deleted_rows,
        )

    excluded_count = len(excluded_rows)
    kept_rows = connection.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
    kept_total = connection.execute(
        "SELECT COALESCE(SUM(amount_centavos), 0) FROM expenses"
    ).fetchone()[0]
    excluded_total = connection.execute(
        "SELECT COALESCE(SUM(amount_centavos), 0) FROM expense_dedup_exclusions"
    ).fetchone()[0]
    summary = {
        "method": f"Equality across all {len(source_columns)} original source fields, grouped by snapshot and source member; audit fields excluded.",
        "source_field_count": len(source_columns),
        "excluded_rows": excluded_count,
        "affected_candidates": len(affected_candidates),
        "rows_before_deduplication": kept_rows + excluded_count,
        "rows_after_deduplication": kept_rows,
        "preserve_all_total_centavos": kept_total + excluded_total,
        "deduplicated_total_centavos": kept_total,
        "financial_difference_centavos": excluded_total,
    }
    if had_expense_view:
        connection.execute(
            """
            CREATE VIEW expense_aggregate AS
            SELECT sq_candidate, COUNT(*) AS expense_row_count, SUM(amount_centavos) AS declared_expense_centavos,
                   COUNT(DISTINCT source_member) AS expense_source_member_count
            FROM expenses GROUP BY sq_candidate
            """
        )
    return summary


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
            candidate_status_code TEXT NOT NULL,
            party_code TEXT NOT NULL,
            party_abbrev TEXT NOT NULL,
            federation_code TEXT NOT NULL,
            birth_date TEXT NOT NULL,
            gender TEXT NOT NULL,
            race TEXT NOT NULL,
            schooling TEXT NOT NULL,
            marital_status TEXT NOT NULL,
            occupation TEXT NOT NULL,
            source_archive TEXT NOT NULL,
            source_member TEXT NOT NULL,
            source_row INTEGER NOT NULL
        );
        CREATE TABLE candidate_duplicates (
            sq_candidate TEXT NOT NULL,
            evidence_json TEXT NOT NULL
        );
        CREATE TABLE expense_duplicates (
            sq_candidate TEXT NOT NULL,
            sq_expense TEXT NOT NULL,
            evidence_json TEXT NOT NULL
        );
        CREATE TABLE vote_denominators (
            uf TEXT PRIMARY KEY,
            election_year INTEGER NOT NULL,
            turn INTEGER NOT NULL,
            cargo_code TEXT NOT NULL,
            cargo TEXT NOT NULL,
            valid_nominal_votes INTEGER NOT NULL,
            valid_legend_votes INTEGER NOT NULL,
            valid_votes_total INTEGER NOT NULL,
            source_row_count INTEGER NOT NULL,
            source_archive TEXT NOT NULL,
            source_member TEXT NOT NULL
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
        "vote_denominator_by_uf.csv",
        "analytical_base.csv",
    )
    for artifact_name in approved_artifacts:
        artifact_path = output_dir / artifact_name
        if artifact_path.exists():
            artifact_path.unlink()
    database_path = output_dir / "pilot.sqlite"
    for suffix in ("", "-journal", "-wal", "-shm"):
        database_file = Path(f"{database_path}{suffix}")
        if database_file.exists():
            database_file.unlink()
    fatal_counts = {
        "invalid_candidate_fields": 0,
        "duplicate_candidate_rows": 0,
        "invalid_expense_fields": 0,
        "missing_expense_amount": 0,
        "invalid_vote_fields": 0,
        "missing_vote_amount": 0,
        "duplicate_vote_rows": 0,
        "unknown_expense_candidates": 0,
        "unknown_vote_candidates": 0,
        "invalid_vote_total_fields": 0,
        "missing_vote_total_fields": 0,
        "vote_total_nominal_mismatch": 0,
        "vote_total_coverage_mismatch": 0,
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
        required = ["SG_UF", "SQ_CANDIDATO", "NR_CANDIDATO", "NM_CANDIDATO", "CD_CARGO", "DS_CARGO", "CD_SITUACAO_CANDIDATURA"]
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
            "candidate_status_code": _text(row, "CD_SITUACAO_CANDIDATURA"),
            "party_code": _text(row, "NR_PARTIDO"),
            "party_abbrev": _text(row, "SG_PARTIDO"),
            "federation_code": _text(row, "NR_FEDERACAO"),
            "birth_date": _text(row, "DT_NASCIMENTO"),
            "gender": _text(row, "DS_GENERO"),
            "race": _text(row, "DS_COR_RACA"),
            "schooling": _text(row, "DS_GRAU_INSTRUCAO"),
            "marital_status": _text(row, "DS_ESTADO_CIVIL"),
            "occupation": _text(row, "DS_OCUPACAO"),
            **_ref(candidate_archive, member, row_number),
        }
        try:
            connection.execute(
                "INSERT INTO candidates VALUES (:sq_candidate, :election_year, :turn, :uf, :cargo_code, :cargo, :candidate_number, :candidate_name, :candidate_status_code, :party_code, :party_abbrev, :federation_code, :birth_date, :gender, :race, :schooling, :marital_status, :occupation, :source_archive, :source_member, :source_row)",
                candidate,
            )
        except sqlite3.IntegrityError:
            fatal("duplicate_candidate_rows", {**_ref(candidate_archive, member, row_number), "sq_candidate": candidate["sq_candidate"]})
            connection.execute(
                "INSERT INTO candidate_duplicates VALUES (?, ?)",
                (candidate["sq_candidate"], json.dumps({**_ref(candidate_archive, member, row_number), "row": candidate}, ensure_ascii=False)),
            )
    connection.commit()
    candidate_ids = {
        row[0] for row in connection.execute("SELECT sq_candidate FROM candidates")
    }


    account_archive = _resource_path(manifest, "accounts_2022")
    expense_rows = 0
    expense_selected = 0
    expense_source_columns: list[str] | None = None
    for row, member, row_number in _iter_selected_rows(account_archive, "accounts_2022"):
        expense_rows += 1
        if _text(row, "AA_ELEICAO") != "2022" or _text(row, "ST_TURNO") != "1" or _text(row, "DS_CARGO").casefold() != FEDERAL_CARGO:
            continue
        expense_selected += 1
        if expense_source_columns is None:
            expense_source_columns = [column for column in row if isinstance(column, str)]
            _create_expense_occurrences(connection, expense_source_columns)
        _insert_expense_occurrence(connection, expense_source_columns, row, account_archive, member, row_number)
        reference = _ref(account_archive, member, row_number)
        sq_candidate = _text(row, "SQ_CANDIDATO")
        sq_expense = _text(row, "SQ_DESPESA")
        if _missing(sq_candidate) or _missing(sq_expense):
            fatal("invalid_expense_fields", {**reference, "reason": "candidate or expense identifier missing"})
            continue
        if sq_candidate not in candidate_ids:
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
    expense_deduplication = materialize_deduplicated_expenses(
        connection,
        str(manifest.get("manifest_id") or ""),
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
        if sq_candidate not in candidate_ids:
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

    party_vote_archive = _resource_path(manifest, "vote_totals_2022")
    party_member = "votacao_partido_munzona_2022_BRASIL.csv"
    with zipfile.ZipFile(party_vote_archive) as archive:
        party_members = [
            info.filename for info in archive.infolist()
            if info.filename.startswith("votacao_partido_munzona_2022_") and info.filename.casefold().endswith(".csv")
        ]
    if party_member not in party_members:
        raise PipelineError(f"membro nacional ausente no ZIP oficial de votação partidária: {party_member}")
    source_details["vote_totals_2022"] = {
        "archive": str(party_vote_archive),
        "selected_members": [party_member],
        "excluded_aggregate_or_document_members": sorted(name for name in party_members if name != party_member),
        "selected_member_count": 1,
        "aggregation_universe": "membro nacional BRASIL; membros BR e estaduais não são somados",
    }
    party_vote_rows_read = 0
    party_vote_rows_selected = 0
    party_totals: dict[str, dict[str, int]] = {}
    for row, row_number in _iter_member_rows(party_vote_archive, party_member):
        party_vote_rows_read += 1
        if (
            _text(row, "ANO_ELEICAO") != "2022"
            or _text(row, "NR_TURNO") != "1"
            or _text(row, "CD_CARGO") != "6"
            or _text(row, "DS_CARGO").casefold() != FEDERAL_CARGO
        ):
            continue
        party_vote_rows_selected += 1
        reference = {
            "source_archive": party_vote_archive.name,
            "source_member": party_member,
            "source_row": row_number,
        }
        uf = _text(row, "SG_UF")
        if uf not in UF_CODES:
            fatal("invalid_vote_total_fields", {**reference, "reason": "UF fora do escopo", "uf": uf})
            continue
        fields = (
            "QT_VOTOS_NOMINAIS_VALIDOS",
            "QT_VOTOS_LEGENDA_VALIDOS",
            "QT_VOTOS_NOM_CONVR_LEG_VALIDOS",
            "QT_TOTAL_VOTOS_LEG_VALIDOS",
        )
        if any(_missing(row.get(field)) for field in fields):
            fatal("missing_vote_total_fields", {**reference, "uf": uf, "reason": "componente oficial ausente"})
            continue
        try:
            valid_nominal = _integer(row["QT_VOTOS_NOMINAIS_VALIDOS"], "QT_VOTOS_NOMINAIS_VALIDOS")
            legend_valid = _integer(row["QT_VOTOS_LEGENDA_VALIDOS"], "QT_VOTOS_LEGENDA_VALIDOS")
            nominal_converted_to_legend = _integer(row["QT_VOTOS_NOM_CONVR_LEG_VALIDOS"], "QT_VOTOS_NOM_CONVR_LEG_VALIDOS")
            valid_legend_total = _integer(row["QT_TOTAL_VOTOS_LEG_VALIDOS"], "QT_TOTAL_VOTOS_LEG_VALIDOS")
            if min(valid_nominal, legend_valid, nominal_converted_to_legend, valid_legend_total) < 0:
                raise ValueError("contagem oficial de votos negativa")
            if valid_legend_total != legend_valid + nominal_converted_to_legend:
                raise ValueError("total oficial de legenda não reconcilia com seus componentes")
        except ValueError as error:
            fatal("invalid_vote_total_fields", {**reference, "uf": uf, "reason": str(error)})
            continue
        total = party_totals.setdefault(
            uf,
            {"valid_nominal_votes": 0, "valid_legend_votes": 0, "valid_votes_total": 0, "source_row_count": 0},
        )
        total["valid_nominal_votes"] += valid_nominal
        total["valid_legend_votes"] += valid_legend_total
        total["valid_votes_total"] += valid_nominal + valid_legend_total
        total["source_row_count"] += 1

    candidate_nominal_by_uf = {
        row["uf"]: row["valid_nominal_votes"]
        for row in connection.execute(
            """
            SELECT c.uf, SUM(v.valid_votes) AS valid_nominal_votes
            FROM votes v JOIN candidates c USING (sq_candidate)
            GROUP BY c.uf
            """
        )
    }
    candidate_ufs = {row[0] for row in connection.execute("SELECT DISTINCT uf FROM candidates")}
    party_ufs = set(party_totals)
    missing_party_ufs = sorted(candidate_ufs - party_ufs)
    unexpected_party_ufs = sorted(party_ufs - candidate_ufs)
    if missing_party_ufs or unexpected_party_ufs:
        fatal(
            "vote_total_coverage_mismatch",
            {"missing_party_ufs": missing_party_ufs, "unexpected_party_ufs": unexpected_party_ufs},
        )
    nominal_votes_by_uf = {}
    for uf in sorted(candidate_ufs | party_ufs):
        party_nominal = party_totals.get(uf, {}).get("valid_nominal_votes", 0)
        candidate_nominal = candidate_nominal_by_uf.get(uf, 0)
        nominal_votes_by_uf[uf] = {
            "party_source": party_nominal,
            "candidate_source": candidate_nominal,
        }
        if party_nominal != candidate_nominal:
            fatal(
                "vote_total_nominal_mismatch",
                {"uf": uf, "party_source": party_nominal, "candidate_source": candidate_nominal},
            )
    for uf, total in sorted(party_totals.items()):
        connection.execute(
            """
            INSERT INTO vote_denominators
            VALUES (?, 2022, 1, '6', 'Deputado Federal', ?, ?, ?, ?, ?, ?)
            """,
            (
                uf,
                total["valid_nominal_votes"],
                total["valid_legend_votes"],
                total["valid_votes_total"],
                total["source_row_count"],
                party_vote_archive.name,
                party_member,
            ),
        )
    connection.commit()

    source_counts = {
        "candidate_rows_read": candidate_rows,
        "candidate_rows_selected": candidate_selected,
        "candidate_rows_canonical": connection.execute("SELECT COUNT(*) FROM candidates").fetchone()[0],
        "expense_rows_read": expense_rows,
        "expense_rows_selected": expense_selected,
        "expense_rows_canonical": connection.execute("SELECT COUNT(*) FROM expenses").fetchone()[0],
        "expense_occurrence_rows_stored": (
            0 if expense_source_columns is None else connection.execute("SELECT COUNT(*) FROM expense_occurrences").fetchone()[0]
        ),
        "vote_rows_read": vote_rows,
        "vote_rows_selected": vote_selected,
        "vote_rows_canonical": connection.execute("SELECT COUNT(*) FROM votes").fetchone()[0],
        "party_vote_rows_read": party_vote_rows_read,
        "party_vote_rows_selected": party_vote_rows_selected,
        "vote_denominator_uf_count": connection.execute("SELECT COUNT(*) FROM vote_denominators").fetchone()[0],
    }

    repeated_expense_documents = connection.execute(
        "SELECT COUNT(*) FROM (SELECT sq_candidate, sq_expense FROM expenses GROUP BY sq_candidate, sq_expense HAVING COUNT(*) > 1)"
    ).fetchone()[0]
    validation = {
        "schema_version": 3,
        "manifest_id": manifest.get("manifest_id"),
        "scope": "Brasil / todas as UFs",
        "target": {"election_year": 2022, "turn": 1, "cargo": "Deputado Federal"},
        "expense_measure": "VR_DESPESA_CONTRATADA, em centavos de real; soma de todas as linhas selecionadas de despesas_contratadas por UF",
        "expense_grain": {
            "row_identity": "(snapshot_id, source_member, source_row)",
            "document_reference": "SQ_DESPESA",
            "documents_with_multiple_lines": repeated_expense_documents,
        },
        "vote_measure": "QT_VOTOS_NOMINAIS_VALIDOS por candidato dividido pelo total oficial de votos nominais válidos mais QT_TOTAL_VOTOS_LEG_VALIDOS, por UF/cargo/turno",
        "vote_denominator": {
            "source_resource": "vote_totals_2022",
            "member": party_member,
            "selected_rows": party_vote_rows_selected,
            "uf_count": len(party_totals),
            "legend_field": "QT_TOTAL_VOTOS_LEG_VALIDOS; conferido contra QT_VOTOS_LEGENDA_VALIDOS + QT_VOTOS_NOM_CONVR_LEG_VALIDOS",
            "filter_order": "calculated from the official full party-vote source before candidate APTO or expense Final filters",
        },
        "source_details": source_details,
        "expense_deduplication": {
            **expense_deduplication,
            "snapshot_id": manifest.get("manifest_id"),
            "identity_rule": "Equality across all 53 original TSE fields within the same snapshot and source member; audit fields are excluded.",
            "economic_identity_confirmed_by_tse": False,
            "interpretation": "A methodological treatment choice; the financial difference is not classified as waste or improper expenditure.",
        },
        "source_counts": source_counts,
        "fatal_counts": fatal_counts,
        "evidence": evidence,
        "reconciliation": {
            "nominal_votes_by_uf": nominal_votes_by_uf,
            "vote_denominator_coverage": {
                "candidate_ufs": sorted(candidate_ufs),
                "party_source_ufs": sorted(party_ufs),
                "missing_party_ufs": missing_party_ufs,
                "unexpected_party_ufs": unexpected_party_ufs,
            },
        },
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
            **validation["reconciliation"],
        }
        validation["reconciliation"] = reconciliation
        if expense_source_total != expense_aggregate_total:
            fatal("invalid_expense_fields", {"reason": "expense aggregate reconciliation failed"})
        if vote_source_total != vote_aggregate_total:
            fatal("invalid_vote_fields", {"reason": "vote aggregate reconciliation failed"})

    if any(fatal_counts.values()):
        validation["status"] = "blocked"
        validation["blocking_rule"] = "Bloqueio apenas por falhas de qualidade, unicidade e relação entre entidades das validações existentes; repetições documentadas de igualdade nos 53 campos originais, no mesmo snapshot/membro, são excluídas da base principal e auditadas, sem bloquear."
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
        ["sq_candidate", "election_year", "turn", "uf", "cargo_code", "cargo", "candidate_number", "candidate_name", "candidate_status_code", "party_code", "party_abbrev", "federation_code", "birth_date", "gender", "race", "schooling", "marital_status", "occupation", "source_archive", "source_member", "source_row"],
        (dict(row) for row in connection.execute("SELECT * FROM candidates ORDER BY uf, candidate_number, sq_candidate")),
    )
    _write_csv(
        output_dir / "vote_denominator_by_uf.csv",
        ["uf", "election_year", "turn", "cargo_code", "cargo", "valid_nominal_votes", "valid_legend_votes", "valid_votes_total", "source_row_count", "source_archive", "source_member"],
        (dict(row) for row in connection.execute("SELECT * FROM vote_denominators ORDER BY uf")),
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
               c.candidate_number, c.candidate_name, c.candidate_status_code, c.party_code,
               c.party_abbrev, c.federation_code, c.birth_date, c.gender, c.race, c.schooling,
               c.marital_status, c.occupation,
               c.source_archive AS candidate_source_archive,
               c.source_member AS candidate_source_member, c.source_row AS candidate_source_row,
               e.expense_row_count, e.declared_expense_centavos,
               CASE WHEN e.sq_candidate IS NULL THEN 'absent' WHEN e.declared_expense_centavos = 0 THEN 'observed_zero' ELSE 'observed' END AS expense_observation,
               e.expense_source_member_count, v.vote_row_count, v.valid_nominal_votes, v.nominal_votes,
               CASE WHEN v.sq_candidate IS NULL THEN 'absent' WHEN v.valid_nominal_votes = 0 THEN 'observed_zero' ELSE 'observed' END AS vote_observation,
               v.vote_source_member_count, vd.valid_votes_total AS official_valid_votes,
               CASE WHEN v.sq_candidate IS NULL OR vd.valid_votes_total = 0 THEN NULL
                    ELSE CAST(v.valid_nominal_votes AS REAL) / vd.valid_votes_total END AS vote_share
        FROM candidates c
        LEFT JOIN expense_aggregate e USING (sq_candidate)
        LEFT JOIN vote_aggregate v USING (sq_candidate)
        LEFT JOIN vote_denominators vd ON vd.uf = c.uf
        ORDER BY c.uf, c.candidate_number, c.sq_candidate
    """
    rows = []
    cursor = connection.execute(analytical_query)
    fieldnames = [column[0] for column in cursor.description]
    for row in cursor:
        item = dict(row)
        for key in ("expense_row_count", "declared_expense_centavos", "expense_source_member_count", "vote_row_count", "valid_nominal_votes", "nominal_votes", "vote_source_member_count", "official_valid_votes", "vote_share"):
            if item[key] is None:
                item[key] = ""
        rows.append(item)
    _write_csv(output_dir / "analytical_base.csv", fieldnames, rows)
    validation["analytical_rows"] = len(rows)
    (output_dir / "validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    connection.commit()
    connection.close()
    return validation
