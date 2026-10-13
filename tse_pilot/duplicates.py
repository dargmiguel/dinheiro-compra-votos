from __future__ import annotations

import csv
import json
import sqlite3
from collections import defaultdict
from pathlib import Path


def _brl(centavos: int) -> str:
    value = f"{centavos / 100:,.2f}"
    return "R$ " + value.replace(",", "X").replace(".", ",").replace("X", ".")


def analyze_duplicate_expenses(database_path: Path) -> dict:
    connection = sqlite3.connect(database_path)
    candidates = dict(connection.execute("SELECT sq_candidate, uf FROM candidates"))
    canonical_by_uf = {
        uf: {"rows": rows, "centavos": centavos}
        for uf, rows, centavos in connection.execute(
            "SELECT c.uf, COUNT(*), COALESCE(SUM(e.amount_centavos), 0) FROM expenses e JOIN candidates c USING (sq_candidate) GROUP BY c.uf"
        )
    }
    multi_item_documents = {
        (sq_candidate, sq_expense)
        for sq_candidate, sq_expense in connection.execute(
            "SELECT sq_candidate, sq_expense FROM expenses GROUP BY sq_candidate, sq_expense HAVING COUNT(*) > 1"
        )
    }
    duplicate_by_uf = defaultdict(lambda: {"rows": 0, "centavos": 0, "candidates": set(), "documents": set()})
    duplicate_documents = set()
    duplicate_rows = []
    for sq_candidate, sq_expense, evidence_json in connection.execute(
        "SELECT sq_candidate, sq_expense, evidence_json FROM expense_duplicates"
    ):
        evidence = json.loads(evidence_json)
        evidence["sq_candidate"] = sq_candidate
        evidence["sq_expense"] = sq_expense
        uf = candidates[evidence["sq_candidate"]]
        item = duplicate_by_uf[uf]
        item["rows"] += 1
        item["centavos"] += evidence["amount_centavos"]
        item["candidates"].add(evidence["sq_candidate"])
        document = (evidence["sq_candidate"], evidence["sq_expense"])
        item["documents"].add(document)
        duplicate_documents.add(document)
        if len(duplicate_rows) < 20:
            duplicate_rows.append(evidence)

    all_ufs = sorted(set(canonical_by_uf) | set(duplicate_by_uf))
    by_uf = []
    for uf in all_ufs:
        canonical = canonical_by_uf.get(uf, {"rows": 0, "centavos": 0})
        duplicate = duplicate_by_uf[uf]
        by_uf.append({
            "uf": uf,
            "excluded_rows": duplicate["rows"],
            "affected_candidates": len(duplicate["candidates"]),
            "exact_repeat_documents": len(duplicate["documents"]),
            "documents_with_multiple_distinct_lines": sum(1 for candidate, expense in multi_item_documents if candidates[candidate] == uf),
            "primary_deduplicated_total_centavos": canonical["centavos"],
            "preserve_all_total_centavos": canonical["centavos"] + duplicate["centavos"],
            "financial_difference_centavos": duplicate["centavos"],
        })

    canonical_total = sum(item["centavos"] for item in canonical_by_uf.values())
    duplicate_total = sum(item["centavos"] for item in duplicate_by_uf.values())
    excluded_rows = sum(item["rows"] for item in duplicate_by_uf.values())
    affected_candidates = len({candidate for item in duplicate_by_uf.values() for candidate in item["candidates"]})
    source_field_count = sum(
        1
        for row in connection.execute("PRAGMA table_info(expense_occurrences)")
        if not row[1].startswith("_")
    )
    primary_rows = sum(item["rows"] for item in canonical_by_uf.values())
    occurrence_rows = connection.execute(
        "SELECT COUNT(*) FROM expense_occurrences"
    ).fetchone()[0]
    connection.close()
    return {
        "status": "primary_deduplicated_with_preserve_all_sensitivity",
        "database": str(database_path),
        "method": "Exact equality across original source fields, within the same snapshot and source member; audit fields excluded.",
        "methodological_uncertainty": "This is a methodological choice; the TSE has not officially confirmed economic identity of repeated records.",
        "interpretation": "Financial difference is not characterized as waste or improper expenditure.",
        "source_field_count": source_field_count,
        "rows_before_deduplication": occurrence_rows,
        "rows_after_deduplication": primary_rows,
        "rows_excluded": excluded_rows,
        "affected_candidates": affected_candidates,
        "exact_repeat_documents": len(duplicate_documents),
        "documents_with_multiple_distinct_lines": len(multi_item_documents),
        "primary_deduplicated_total_centavos": canonical_total,
        "preserve_all_total_centavos": canonical_total + duplicate_total,
        "financial_difference_centavos": duplicate_total,
        "primary_deduplicated_total_brl": _brl(canonical_total),
        "preserve_all_total_brl": _brl(canonical_total + duplicate_total),
        "financial_difference_brl": _brl(duplicate_total),
        "by_uf": by_uf,
        "excluded_occurrence_evidence_sample": duplicate_rows,
    }


def write_duplicate_diagnostics(database_path: Path, output_path: Path) -> Path:
    report = analyze_duplicate_expenses(Path(database_path))
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    exclusions_path = output_path.with_name("tse-2022-dedup-exclusions.csv")
    fields = [
        "snapshot_id", "source_archive", "source_member", "source_row",
        "kept_source_archive", "kept_source_member", "kept_source_row",
        "sq_candidate", "sq_expense", "amount_centavos", "row_signature",
    ]
    connection = sqlite3.connect(database_path)
    try:
        with exclusions_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(fields)
            writer.writerows(connection.execute(
                f"SELECT {', '.join(fields)} FROM expense_dedup_exclusions "
                "ORDER BY snapshot_id, source_member, source_row"
            ))
    finally:
        connection.close()
    return output_path
