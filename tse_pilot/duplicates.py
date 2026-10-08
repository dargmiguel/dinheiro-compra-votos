from __future__ import annotations

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
    for (evidence_json,) in connection.execute("SELECT evidence_json FROM expense_duplicates"):
        evidence = json.loads(evidence_json)
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
    connection.close()

    all_ufs = sorted(set(canonical_by_uf) | set(duplicate_by_uf))
    by_uf = []
    for uf in all_ufs:
        canonical = canonical_by_uf.get(uf, {"rows": 0, "centavos": 0})
        duplicate = duplicate_by_uf[uf]
        by_uf.append({
            "uf": uf,
            "exact_repeat_rows": duplicate["rows"],
            "affected_candidates": len(duplicate["candidates"]),
            "exact_repeat_documents": len(duplicate["documents"]),
            "documents_with_multiple_distinct_lines": sum(1 for candidate, expense in multi_item_documents if candidates[candidate] == uf),
            "remove_exact_repeats_centavos": canonical["centavos"],
            "preserve_all_lines_centavos": canonical["centavos"] + duplicate["centavos"],
            "difference_centavos": duplicate["centavos"],
        })

    canonical_total = sum(item["centavos"] for item in canonical_by_uf.values())
    duplicate_total = sum(item["centavos"] for item in duplicate_by_uf.values())
    return {
        "status": "diagnostic_only",
        "database": str(database_path),
        "exact_repeat_rows": sum(item["rows"] for item in duplicate_by_uf.values()),
        "exact_repeat_candidates": len({candidate for item in duplicate_by_uf.values() for candidate in item["candidates"]}),
        "exact_repeat_documents": len(duplicate_documents),
        "documents_with_multiple_distinct_lines": len(multi_item_documents),
        "remove_exact_repeats_centavos": canonical_total,
        "preserve_all_lines_centavos": canonical_total + duplicate_total,
        "difference_centavos": duplicate_total,
        "remove_exact_repeats_brl": _brl(canonical_total),
        "preserve_all_lines_brl": _brl(canonical_total + duplicate_total),
        "difference_brl": _brl(duplicate_total),
        "by_uf": by_uf,
        "duplicate_evidence_sample": duplicate_rows,
    }


def write_duplicate_diagnostics(database_path: Path, output_path: Path) -> Path:
    report = analyze_duplicate_expenses(Path(database_path))
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path
