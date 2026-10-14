from __future__ import annotations

import csv
import io
import json
import sqlite3
import zipfile
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

from .pipeline import UF_CODES, _centavos

SOURCE_CLASSES = {"0": "public", "1": "private", "2": "public"}
NATURE_CLASSES = {"0": "estimable", "1": "financial"}
UNKNOWN_MARKERS = {"", "-1", "-3", "#NULO", "#NE"}


def _percent(numerator: int, denominator: int) -> str | None:
    if denominator == 0:
        return None
    value = (Decimal(numerator) * 100 / Decimal(denominator)).quantize(
        Decimal("0.0001"), rounding=ROUND_HALF_UP
    )
    return f"{value:.4f}"


def _amount_centavos(value: str | None, member: str, row_number: int) -> int | None:
    if value is None or value.strip().upper() in UNKNOWN_MARKERS:
        return None
    try:
        return _centavos(value)
    except ValueError as error:
        raise ValueError(f"valor monetário inválido em {member}, linha {row_number}: {value!r}") from error


def _selected_members(names: list[str], prefix: str) -> tuple[dict[str, str], list[str]]:
    selected: dict[str, str] = {}
    excluded: list[str] = []
    for name in names:
        if not name.startswith(prefix) or not name.casefold().endswith(".csv"):
            continue
        uf = name[len(prefix) : -4]
        if uf not in UF_CODES:
            excluded.append(name)
            continue
        if uf in selected:
            raise ValueError(f"membro duplicado para {prefix}{uf}: {selected[uf]} e {name}")
        selected[uf] = name
    missing = sorted(UF_CODES - selected.keys())
    if missing:
        raise ValueError(f"ZIP incompleto para {prefix}: faltam UFs {', '.join(missing)}")
    return selected, sorted(excluded)


def _new_flow_row() -> dict[str, Any]:
    return {
        "rows": 0,
        "valid_amount_rows": 0,
        "missing_amount_rows": 0,
        "amount_centavos": 0,
        "class_amounts": {source_class: 0 for source_class in ("public", "private", "unclassified")},
        "class_nature_amounts": {
            (source_class, nature): 0
            for source_class in ("public", "private", "unclassified")
            for nature in ("financial", "estimable", "unclassified")
        },
    }


def _new_summary_group() -> dict[str, Any]:
    return {
        "amount_centavos": 0,
        "candidate_ids": set(),
        "record_count": 0,
        "valid_amount_rows": 0,
        "missing_amount_rows": 0,
        "nature_amounts": {nature: 0 for nature in ("financial", "estimable", "unclassified")},
        "codes": set(),
        "labels": set(),
    }


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

def _field_type(field: str) -> str:
    if field.endswith("_pct"):
        return "percentage"
    if field.endswith("_has_rows"):
        return "boolean"
    if field.endswith(("_centavos", "_rows", "_count")):
        return "integer"
    return "text"


def write_funding_source_analysis(
    database_path: Path,
    archive_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    """Export receipt and paid-expense sources for APTO candidates with Final contracted expenses."""
    database_path = Path(database_path)
    archive_path = Path(archive_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    try:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        required_tables = {"candidates", "expenses", "expense_occurrences"}
        missing_tables = required_tables - tables
        if missing_tables:
            raise ValueError(f"base derivada sem tabelas exigidas: {', '.join(sorted(missing_tables))}")
        occurrence_columns = {row[1] for row in connection.execute("PRAGMA table_info(expense_occurrences)")}
        if "SQ_PRESTADOR_CONTAS" not in occurrence_columns:
            raise ValueError("expense_occurrences não contém SQ_PRESTADOR_CONTAS; não é possível ligar pagamentos a candidatos")

        candidate_rows: dict[str, dict[str, Any]] = {}
        account_candidates: dict[str, str] = {}
        account_by_candidate: dict[str, str] = {}
        source_archive_names: set[str] = set()
        query = """
            SELECT c.sq_candidate, c.uf, c.candidate_number, c.candidate_name, c.party_abbrev,
                   e.amount_centavos, e.source_archive, o.SQ_PRESTADOR_CONTAS
            FROM expenses e
            JOIN expense_occurrences o
              ON e.source_archive = o._source_archive
             AND e.source_member = o._source_member
             AND e.source_row = o._source_row
            JOIN candidates c ON c.sq_candidate = e.sq_candidate
            WHERE c.candidate_status_code = '12'
              AND c.election_year = 2022 AND c.turn = 1 AND c.cargo_code = '6'
              AND o.TP_PRESTACAO_CONTAS = 'Final'
            ORDER BY c.sq_candidate, e.source_member, e.source_row
        """
        for row in connection.execute(query):
            source_archive_names.add(str(row["source_archive"]))
            candidate_id = str(row["sq_candidate"])
            candidate = candidate_rows.setdefault(
                candidate_id,
                {
                    "sq_candidate": candidate_id,
                    "uf": row["uf"],
                    "candidate_number": row["candidate_number"],
                    "candidate_name": row["candidate_name"],
                    "party_abbrev": row["party_abbrev"],
                    "contracted_expense_centavos": 0,
                    "account_keys": set(),
                    "receipts": _new_flow_row(),
                    "payments": _new_flow_row(),
                },
            )
            candidate["contracted_expense_centavos"] += int(row["amount_centavos"])
            account_key = "" if row["SQ_PRESTADOR_CONTAS"] is None else str(row["SQ_PRESTADOR_CONTAS"]).strip()
            candidate["account_keys"].add(account_key)
        if not candidate_rows:
            raise ValueError("base sem candidaturas APTO com despesa contratada Final observada")
        invalid_keys = {
            candidate_id: candidate["account_keys"]
            for candidate_id, candidate in candidate_rows.items()
            if len(candidate["account_keys"]) != 1 or "" in candidate["account_keys"]
        }
        if invalid_keys:
            raise ValueError(f"chave SQ_PRESTADOR_CONTAS ausente ou ambígua em {len(invalid_keys)} candidaturas APTO/Final")
        for candidate_id, candidate in candidate_rows.items():
            account_key = next(iter(candidate.pop("account_keys")))
            if account_key in account_candidates and account_candidates[account_key] != candidate_id:
                raise ValueError(f"SQ_PRESTADOR_CONTAS repetido entre candidaturas: {account_key}")
            account_candidates[account_key] = candidate_id
            account_by_candidate[candidate_id] = account_key
        if source_archive_names != {archive_path.name}:
            raise ValueError(
                "ZIP informado não corresponde ao arquivo que originou expenses: "
                f"base={sorted(source_archive_names)}, recebido={archive_path.name}"
            )
        apto_candidate_count = int(
            connection.execute(
                "SELECT COUNT(DISTINCT sq_candidate) FROM candidates WHERE candidate_status_code='12' AND election_year=2022 AND turn=1 AND cargo_code='6'"
            ).fetchone()[0]
        )
    finally:
        connection.close()

    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        receipt_members, excluded_receipt_members = _selected_members(names, "receitas_candidatos_2022_")
        paid_members, excluded_paid_members = _selected_members(names, "despesas_pagas_candidatos_2022_")
        donor_origin_members = sorted(
            name for name in names
            if name.startswith("receitas_candidatos_doador_originario_2022_") and name.casefold().endswith(".csv")
        )
        filtered_rows = {"receipts": 0, "payments": 0}
        receipt_account_key_mismatches: set[str] = set()
        summary_groups = {
            flow: {
                source_class: _new_summary_group()
                for source_class in ("public", "private", "unclassified")
            }
            for flow in ("receipts", "payments")
        }

        specifications = {
            "receipts": {
                "members": receipt_members,
                "required_fields": {
                    "AA_ELEICAO", "ST_TURNO", "TP_PRESTACAO_CONTAS", "CD_CARGO",
                    "SQ_CANDIDATO", "SQ_PRESTADOR_CONTAS", "CD_FONTE_RECEITA",
                    "DS_FONTE_RECEITA", "CD_NATUREZA_RECEITA", "DS_NATUREZA_RECEITA", "VR_RECEITA",
                },
                "source_code": "CD_FONTE_RECEITA",
                "source_label": "DS_FONTE_RECEITA",
                "nature_code": "CD_NATUREZA_RECEITA",
                "nature_label": "DS_NATUREZA_RECEITA",
                "amount": "VR_RECEITA",
            },
            "payments": {
                "members": paid_members,
                "required_fields": {
                    "AA_ELEICAO", "ST_TURNO", "TP_PRESTACAO_CONTAS", "SQ_PRESTADOR_CONTAS",
                    "CD_FONTE_DESPESA", "DS_FONTE_DESPESA", "CD_NATUREZA_DESPESA",
                    "DS_NATUREZA_DESPESA", "VR_PAGTO_DESPESA",
                },
                "source_code": "CD_FONTE_DESPESA",
                "source_label": "DS_FONTE_DESPESA",
                "nature_code": "CD_NATUREZA_DESPESA",
                "nature_label": "DS_NATUREZA_DESPESA",
                "amount": "VR_PAGTO_DESPESA",
            },
        }
        for flow, spec in specifications.items():
            for uf, member in sorted(spec["members"].items()):
                with archive.open(member) as raw:
                    text = io.TextIOWrapper(raw, encoding="latin-1", newline="")
                    reader = csv.DictReader(text, delimiter=";")
                    missing_fields = spec["required_fields"] - set(reader.fieldnames or [])
                    if missing_fields:
                        raise ValueError(f"{member}: faltam campos {', '.join(sorted(missing_fields))}")
                    for row_number, row in enumerate(reader, start=2):
                        if (
                            row.get("AA_ELEICAO") != "2022"
                            or row.get("ST_TURNO") != "1"
                            or (row.get("TP_PRESTACAO_CONTAS") or "").strip().casefold() != "final"
                        ):
                            continue
                        if flow == "receipts":
                            if row.get("CD_CARGO") != "6":
                                continue
                            candidate_id = row.get("SQ_CANDIDATO", "").strip()
                            candidate = candidate_rows.get(candidate_id)
                            if candidate is None:
                                continue
                            if row.get("SQ_PRESTADOR_CONTAS", "").strip() != account_by_candidate[candidate_id]:
                                receipt_account_key_mismatches.add(candidate_id)
                        else:
                            account_key = row.get("SQ_PRESTADOR_CONTAS", "").strip()
                            candidate_id = account_candidates.get(account_key)
                            if candidate_id is None:
                                continue
                            candidate = candidate_rows[candidate_id]
                        if candidate["uf"] != uf:
                            raise ValueError(f"candidatura {candidate_id} aparece em membro {member} incompatível com UF {candidate['uf']}")

                        raw_source_code = (row.get(spec["source_code"]) or "").strip()
                        source_code = raw_source_code.upper()
                        source_class = SOURCE_CLASSES.get(source_code, "unclassified")
                        source_label = (row.get(spec["source_label"]) or "").strip()
                        raw_nature_code = (row.get(spec["nature_code"]) or "").strip()
                        nature_code = raw_nature_code.upper()
                        nature_class = NATURE_CLASSES.get(nature_code, "unclassified")
                        nature_label = (row.get(spec["nature_label"]) or "").strip()
                        amount = _amount_centavos(row.get(spec["amount"]), member, row_number)
                        flow_row = candidate[flow]
                        flow_row["rows"] += 1
                        summary_group = summary_groups[flow][source_class]
                        summary_group["record_count"] += 1
                        summary_group["candidate_ids"].add(candidate_id)
                        summary_group["codes"].add(source_code or "(vazio)")
                        summary_group["labels"].add(source_label or "(vazio)")
                        if amount is None:
                            flow_row["missing_amount_rows"] += 1
                            summary_group["missing_amount_rows"] += 1
                        else:
                            flow_row["valid_amount_rows"] += 1
                            flow_row["amount_centavos"] += amount
                            flow_row["class_amounts"][source_class] += amount
                            flow_row["class_nature_amounts"][source_class, nature_class] += amount
                            summary_group["valid_amount_rows"] += 1
                            summary_group["amount_centavos"] += amount
                            summary_group["nature_amounts"][nature_class] += amount
                        filtered_rows[flow] += 1
                    text.detach()

    flow_candidate_sets = {
        flow: {
            candidate_id
            for candidate_id, candidate in candidate_rows.items()
            if candidate[flow]["rows"] > 0
        }
        for flow in ("receipts", "payments")
    }
    flow_totals = {
        flow: sum(candidate[flow]["amount_centavos"] for candidate in candidate_rows.values())
        for flow in ("receipts", "payments")
    }
    classified_totals = {
        flow: sum(
            candidate[flow]["class_amounts"][source_class]
            for candidate in candidate_rows.values()
            for source_class in ("public", "private")
        )
        for flow in ("receipts", "payments")
    }
    summary_rows: list[dict[str, Any]] = []
    for flow in ("receipts", "payments"):
        all_amount = flow_totals[flow]
        classified_amount = classified_totals[flow]
        for source_class in ("public", "private", "unclassified"):
            group = summary_groups[flow][source_class]
            summary_rows.append({
                "flow": flow,
                "source_class": source_class,
                "source_code_values": ";".join(sorted(group["codes"])),
                "source_label_values": ";".join(sorted(group["labels"])),
                "record_count": group["record_count"],
                "candidate_count": len(group["candidate_ids"]),
                "reference_candidate_count": len(candidate_rows),
                "candidate_coverage_pct": _percent(len(group["candidate_ids"]), len(candidate_rows)),
                "amount_valid_rows": group["valid_amount_rows"],
                "amount_missing_rows": group["missing_amount_rows"],
                "amount_centavos": group["amount_centavos"],
                "financial_amount_centavos": group["nature_amounts"]["financial"],
                "estimable_amount_centavos": group["nature_amounts"]["estimable"],
                "nature_unclassified_amount_centavos": group["nature_amounts"]["unclassified"],
                "all_flow_amount_denominator_centavos": all_amount,
                "classified_flow_amount_denominator_centavos": classified_amount,
                "share_of_all_flow_amount_pct": _percent(group["amount_centavos"], all_amount),
                "share_of_classified_flow_amount_pct": (
                    _percent(group["amount_centavos"], classified_amount)
                    if source_class != "unclassified" else None
                ),
            })

    candidate_fields = [
        "sq_candidate", "candidate_name", "candidate_number", "uf", "party_abbrev",
        "contracted_expense_centavos",
    ]
    for flow in ("receipt", "payment"):
        candidate_fields.extend([
            f"{flow}_has_rows", f"{flow}_rows", f"{flow}_amount_valid_rows",
            f"{flow}_amount_missing_rows", f"{flow}_total_centavos",
            f"{flow}_public_centavos", f"{flow}_private_centavos", f"{flow}_unclassified_centavos",
        ])
        for source_class in ("public", "private", "unclassified"):
            for nature in ("financial", "estimable", "nature_unclassified"):
                candidate_fields.append(f"{flow}_{source_class}_{nature}_centavos")
    candidate_export_rows: list[dict[str, Any]] = []
    for candidate_id in sorted(candidate_rows):
        candidate = candidate_rows[candidate_id]
        exported: dict[str, Any] = {
            key: candidate[key]
            for key in ("sq_candidate", "candidate_name", "candidate_number", "uf", "party_abbrev", "contracted_expense_centavos")
        }
        for flow in ("receipts", "payments"):
            stem = "receipt" if flow == "receipts" else "payment"
            data = candidate[flow]
            has_rows = data["rows"] > 0
            exported[f"{stem}_has_rows"] = has_rows
            exported[f"{stem}_rows"] = data["rows"]
            exported[f"{stem}_amount_valid_rows"] = data["valid_amount_rows"]
            exported[f"{stem}_amount_missing_rows"] = data["missing_amount_rows"]
            exported[f"{stem}_total_centavos"] = data["amount_centavos"] if data["valid_amount_rows"] else None
            for source_class in ("public", "private", "unclassified"):
                class_amount = data["class_amounts"][source_class]
                exported[f"{stem}_{source_class}_centavos"] = class_amount if has_rows else None
                for nature in ("financial", "estimable", "unclassified"):
                    field_nature = "nature_unclassified" if nature == "unclassified" else nature
                    exported[f"{stem}_{source_class}_{field_nature}_centavos"] = (
                        data["class_nature_amounts"][source_class, nature] if has_rows else None
                    )
        candidate_export_rows.append(exported)

    dictionary: list[dict[str, str]] = []
    candidate_definitions = {
        "sq_candidate": "Identificador sequencial da candidatura no TSE; chave candidata usada para ligar receitas.",
        "candidate_name": "Nome da candidatura conforme a base candidates já existente.",
        "candidate_number": "Número eleitoral da candidatura.",
        "uf": "UF da candidatura de deputado federal.",
        "party_abbrev": "Sigla partidária da candidatura.",
        "contracted_expense_centavos": "Despesa Final contratada da base principal deduplicada; referência para a população, não pagamento.",
    }
    for flow in ("receipt", "payment"):
        kind = "receita declarada" if flow == "receipt" else "pagamento declarado de despesa"
        candidate_definitions.update({
            f"{flow}_has_rows": f"Indica se há ao menos uma linha Final de {kind} ligada à candidatura.",
            f"{flow}_rows": f"Quantidade de linhas Final de {kind} ligadas à candidatura, sem nova deduplicação.",
            f"{flow}_amount_valid_rows": f"Linhas de {kind} com valor monetário interpretável.",
            f"{flow}_amount_missing_rows": f"Linhas de {kind} com valor ausente ou sentinela numérica #NULO/#NE.",
            f"{flow}_total_centavos": f"Soma em centavos das linhas válidas de {kind}; vazio quando não há valor válido.",
        })
        for source_class in ("public", "private", "unclassified"):
            candidate_definitions[f"{flow}_{source_class}_centavos"] = (
                f"Soma em centavos de {kind} da classe {source_class}; vazio se não houver linhas no fluxo."
            )
            for nature in ("financial", "estimable", "nature_unclassified"):
                nature_label = {"financial": "financeira", "estimable": "estimável", "nature_unclassified": "natureza não classificada"}[nature]
                candidate_definitions[f"{flow}_{source_class}_{nature}_centavos"] = (
                    f"Soma em centavos de {kind}, classe {source_class} e natureza {nature_label}."
                )
    for field in candidate_fields:
        dictionary.append({
            "table": "tse-2022-funding-source-candidates.csv",
            "field": field,
            "type": _field_type(field),
            "definition": candidate_definitions[field],
        })

    summary_fields = [
        "flow", "source_class", "source_code_values", "source_label_values", "record_count",
        "candidate_count", "reference_candidate_count", "candidate_coverage_pct", "amount_valid_rows",
        "amount_missing_rows", "amount_centavos", "financial_amount_centavos", "estimable_amount_centavos",
        "nature_unclassified_amount_centavos", "all_flow_amount_denominator_centavos",
        "classified_flow_amount_denominator_centavos", "share_of_all_flow_amount_pct",
        "share_of_classified_flow_amount_pct",
    ]
    summary_definitions = {
        "flow": "Fluxo: receipts são receitas declaradas; payments são despesas pagas declaradas.",
        "source_class": "public = CD_FONTE 0/2; private = CD_FONTE 1 (Outros Recursos); unclassified = qualquer outro código/ausência.",
        "source_code_values": "Códigos CD_FONTE observados nesta classe, separados por ponto e vírgula.",
        "source_label_values": "Descrições de fonte originais observadas, separadas por ponto e vírgula.",
        "record_count": "Linhas de origem no fluxo/classe; cada linha selecionada é contada uma vez.",
        "candidate_count": "Candidaturas de referência com ao menos uma linha nesta classe; classes podem se sobrepor.",
        "reference_candidate_count": "Denominador fixo: candidaturas APTO/Final com despesa contratada deduplicada observada.",
        "candidate_coverage_pct": "candidate_count dividido por reference_candidate_count; classes podem se sobrepor.",
        "amount_valid_rows": "Linhas com valor interpretável.",
        "amount_missing_rows": "Linhas com valor ausente ou sentinela; preservadas na contagem, fora das somas.",
        "amount_centavos": "Soma do VR_RECEITA ou VR_PAGTO_DESPESA válido em centavos.",
        "financial_amount_centavos": "Parcela da soma com CD_NATUREZA 1 (Financeiro).",
        "estimable_amount_centavos": "Parcela da soma com CD_NATUREZA 0 (Estimável).",
        "nature_unclassified_amount_centavos": "Parcela da soma com CD_NATUREZA fora de 0/1 ou ausente.",
        "all_flow_amount_denominator_centavos": "Denominador da participação sobre todos os valores monetários válidos do fluxo, incluindo fonte não classificada.",
        "classified_flow_amount_denominator_centavos": "Denominador da participação classificada: soma pública + private/Outros Recursos; exclui valores de fonte não classificada.",
        "share_of_all_flow_amount_pct": "amount_centavos dividido por all_flow_amount_denominator_centavos × 100.",
        "share_of_classified_flow_amount_pct": "Para classes pública/privada: amount_centavos dividido por classified_flow_amount_denominator_centavos × 100; vazio para não classificada.",
    }
    for field in summary_fields:
        dictionary.append({
            "table": "tse-2022-funding-source-summary.csv",
            "field": field,
            "type": _field_type(field),
            "definition": summary_definitions[field],
        })

    coverage = {
        "reference_candidates_with_final_expenses": len(candidate_rows),
        "all_apto_candidates": apto_candidate_count,
        "apto_candidates_without_observed_final_expense": apto_candidate_count - len(candidate_rows),
        "receipts_candidates_with_rows": len(flow_candidate_sets["receipts"]),
        "receipts_candidates_without_rows": len(candidate_rows) - len(flow_candidate_sets["receipts"]),
        "receipts_candidate_coverage_pct": _percent(len(flow_candidate_sets["receipts"]), len(candidate_rows)),
        "payments_candidates_with_rows": len(flow_candidate_sets["payments"]),
        "payments_candidates_without_rows": len(candidate_rows) - len(flow_candidate_sets["payments"]),
        "payments_candidate_coverage_pct": _percent(len(flow_candidate_sets["payments"]), len(candidate_rows)),
        "receipt_account_key_mismatch_candidates": len(receipt_account_key_mismatches),
    }
    recut = {
        "population": {
            "election_year": 2022,
            "turn": 1,
            "cargo_code": "6",
            "candidate_status_code": "12",
            "reference_definition": "candidatura APTO com ao menos uma linha Final retida em expenses; despesas contratadas observadas na base principal deduplicada",
            **coverage,
        },
        "coverage": coverage,
        "source_archive": str(archive_path),
        "source_members": {
            "receipts_selected": [receipt_members[uf] for uf in sorted(receipt_members)],
            "receipts_excluded_aggregate_or_document": excluded_receipt_members,
            "payments_selected": [paid_members[uf] for uf in sorted(paid_members)],
            "payments_excluded_aggregate_or_document": excluded_paid_members,
            "receipts_donor_origin_not_selected": donor_origin_members,
            "receipt_rows_linked_to_reference_candidates": filtered_rows["receipts"],
            "payment_rows_linked_to_reference_candidates": filtered_rows["payments"],
        },
        "filters": {
            "receipts": "AA_ELEICAO=2022; ST_TURNO=1; TP_PRESTACAO_CONTAS case-insensitive FINAL; CD_CARGO=6; SQ_CANDIDATO in reference population",
            "payments": "AA_ELEICAO=2022; ST_TURNO=1; TP_PRESTACAO_CONTAS case-insensitive FINAL; SQ_PRESTADOR_CONTAS linked to reference population through expense_occurrences",
            "receipt_candidate_key": "SQ_CANDIDATO liga receitas a candidates.sq_candidate; SQ_PRESTADOR_CONTAS é verificado contra a chave da prestação Final de despesas contratadas.",
            "payment_candidate_key": "SQ_PRESTADOR_CONTAS dos pagamentos liga à mesma chave extraída de expense_occurrences para cada candidatura APTO/Final; a chave é única no recorte.",
            "aggregation": "Todas as linhas dos arquivos estaduais selecionados; sem deduplicação adicional. Arquivos BR/BRASIL e receitas de doador originário não entram na soma.",
        },
        "classification": {
            "public_source_codes": ["0", "2"],
            "public_source_definitions": {"0": "Fundo Partidário", "2": "Fundo Especial de Financiamento de Campanha (FEFC)"},
            "private_source_codes": ["1"],
            "private_source_definition": "Outros Recursos (CD_FONTE=1); apresentado separadamente como recursos privados/outros não públicos conforme a categoria do leiaute.",
            "unclassified_source_codes": ["9", "-1", "-3", "#NULO", "#NE", "(vazio)", "qualquer código não mapeado"],
            "resource_nature_codes": {"0": "Estimável", "1": "Financeiro", "other": "Natureza não classificada"},
            "percentage_denominators": {
                "share_of_classified_flow_amount_pct": "valor público ou privado dividido pela soma pública + privada (CD_FONTE=0/2 + CD_FONTE=1); exclui fonte não classificada",
                "share_of_all_flow_amount_pct": "valor da classe dividido por todos os valores monetários válidos no fluxo, inclusive fonte não classificada",
            },
        },
        "interpretation": {
            "receipts": "VR_RECEITA é receita declarada; valores financeiros e estimáveis são separados. Ausência de linha não é receita zero.",
            "payments": "VR_PAGTO_DESPESA é despesa paga declarada; CD_FONTE_DESPESA descreve a fonte informada para a despesa, não rastreamento de fungibilidade nem pareamento a uma receita específica.",
            "contracted_expense": "A despesa contratada deduplicada define a população de referência e não equivale a pagamento.",
            "unclassified": "Códigos de fonte fora de 0/1/2, valores ausentes e sentinelas são mantidos em classe separada, nunca atribuídos a público ou privado.",
        },
        "outputs": [
            "tse-2022-funding-source-candidates.csv",
            "tse-2022-funding-source-summary.csv",
            "tse-2022-funding-source-dictionary.csv",
            "tse-2022-funding-source-recut.json",
        ],
    }
    _write_csv(output_dir / recut["outputs"][0], candidate_export_rows, candidate_fields)
    _write_csv(output_dir / recut["outputs"][1], summary_rows, summary_fields)
    _write_csv(output_dir / recut["outputs"][2], dictionary, ["table", "field", "type", "definition"])
    (output_dir / recut["outputs"][3]).write_text(
        json.dumps(recut, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return {
        "population": recut["population"],
        "coverage": coverage,
        "receipts_amount_centavos": flow_totals["receipts"],
        "payments_amount_centavos": flow_totals["payments"],
        "outputs": [str(output_dir / name) for name in recut["outputs"]],
    }
