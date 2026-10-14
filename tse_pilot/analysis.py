from __future__ import annotations

import csv
import json
import math
import sqlite3
import zipfile
from datetime import date, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import statsmodels.api as sm

from .pipeline import _centavos

ELECTION_DATE = date(2022, 10, 2)
MISSING_VALUES = {"", "#NULO", "#NE"}


def _missing(value: Any) -> bool:
    return value is None or str(value).strip().upper() in MISSING_VALUES


def _age_at_election(value: str | None) -> int | None:
    if _missing(value):
        return None
    try:
        born = datetime.strptime(str(value).strip(), "%d/%m/%Y").date()
    except ValueError:
        return None
    return ELECTION_DATE.year - born.year - ((ELECTION_DATE.month, ELECTION_DATE.day) < (born.month, born.day))


def _pt_int(value: int) -> str:
    return f"{int(value):,}".replace(",", ".")


def _pt_decimal(value: float, places: int = 2) -> str:
    formatted = f"{float(value):,.{places}f}"
    return formatted.replace(",", "\0").replace(".", ",").replace("\0", ".")


def _pt_brl_centavos(value: int) -> str:
    return _pt_decimal(value / 100)


def _pt_bool(value: bool | None) -> str:
    return "sim" if value is True else "não" if value is False else "não verificado"
def _fixed_expense_band(expense_centavos: int) -> str:
    if expense_centavos <= 5_000_000:
        return "ate_50_mil"
    if expense_centavos <= 20_000_000:
        return "50_a_200_mil"
    if expense_centavos <= 100_000_000:
        return "200_mil_a_1_milhao"
    return "acima_1_milhao"




def _write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_expense_temporal_analysis(database_path: Path, output_dir: Path) -> dict[str, Any]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    try:
        occurrence_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(expense_occurrences)")
        }
        if "DT_DESPESA" not in occurrence_columns:
            raise ValueError("expense_occurrences não contém DT_DESPESA")

        scope = """
            JOIN candidates c ON c.sq_candidate = {candidate}
            WHERE c.candidate_status_code = '12'
              AND c.election_year = 2022 AND c.turn = 1 AND c.cargo_code = '6'
              AND o.TP_PRESTACAO_CONTAS = 'Final'
        """
        queries = {
            "deduplicado": (
                """
                SELECT e.sq_candidate, e.amount_centavos, o.DT_DESPESA
                FROM expenses e
                JOIN expense_occurrences o
                  ON e.source_archive = o._source_archive
                 AND e.source_member = o._source_member
                 AND e.source_row = o._source_row
                """
                + scope.format(candidate="e.sq_candidate")
                + " ORDER BY e.source_archive, e.source_member, e.source_row"
            ),
            "todas_as_linhas": (
                """
                SELECT o.SQ_CANDIDATO, o.VR_DESPESA_CONTRATADA, o.DT_DESPESA
                FROM expense_occurrences o
                """
                + scope.format(candidate="o.SQ_CANDIDATO")
                + " ORDER BY o._source_archive, o._source_member, o._source_row"
            ),
        }
        election_date = date(2022, 10, 2)
        status_order = ("valid_2022", "outside_2022", "missing", "invalid")
        period_rules = {
            "before": ("data válida < 2022-10-02", 1),
            "on": ("data válida = 2022-10-02", 2),
            "after": ("data válida > 2022-10-02", 3),
        }
        monthly_rows: list[dict[str, Any]] = []
        event_rows: list[dict[str, Any]] = []
        quality_rows: list[dict[str, Any]] = []
        scenario_results: dict[str, dict[str, Any]] = {}
        expense_basis = "VR_DESPESA_CONTRATADA; valor contratado declarado, não pagamento"

        for scenario, query in queries.items():
            quality = {
                status: {
                    "expense_count": 0,
                    "amount_centavos": 0,
                    "candidates": set(),
                    "first_valid_date": None,
                    "last_valid_date": None,
                    "raw_examples": set(),
                }
                for status in status_order
            }
            months = {
                month: {
                    "expense_count": 0,
                    "amount_centavos": 0,
                    "candidates": set(),
                    "first_expense_date": None,
                    "last_expense_date": None,
                }
                for month in range(1, 13)
            }
            periods = {
                period: {"expense_count": 0, "amount_centavos": 0, "candidates": set()}
                for period in period_rules
            }
            all_candidates: set[str] = set()
            first_valid_date = last_valid_date = None
            first_in_year = last_in_year = None
            expense_count = total_amount_centavos = 0

            for candidate_id, raw_amount, raw_date in connection.execute(query):
                candidate_id = str(candidate_id)
                amount_centavos = int(raw_amount) if scenario == "deduplicado" else _centavos(raw_amount)
                expense_count += 1
                total_amount_centavos += amount_centavos
                all_candidates.add(candidate_id)

                if _missing(raw_date):
                    status = "missing"
                    expense_date = None
                else:
                    try:
                        expense_date = datetime.strptime(str(raw_date).strip(), "%d/%m/%Y").date()
                    except ValueError:
                        status = "invalid"
                        expense_date = None
                    else:
                        status = "valid_2022" if expense_date.year == 2022 else "outside_2022"

                bucket = quality[status]
                bucket["expense_count"] += 1
                bucket["amount_centavos"] += amount_centavos
                bucket["candidates"].add(candidate_id)
                if _missing(raw_date):
                    raw_example = "(ausente)" if raw_date is None or not str(raw_date).strip() else str(raw_date).strip()
                    bucket["raw_examples"].add(raw_example)
                elif status == "invalid":
                    bucket["raw_examples"].add(str(raw_date).strip())
                if expense_date is None:
                    continue

                iso_date = expense_date.isoformat()
                if bucket["first_valid_date"] is None or expense_date < bucket["first_valid_date"]:
                    bucket["first_valid_date"] = expense_date
                if bucket["last_valid_date"] is None or expense_date > bucket["last_valid_date"]:
                    bucket["last_valid_date"] = expense_date
                if first_valid_date is None or expense_date < first_valid_date:
                    first_valid_date = expense_date
                if last_valid_date is None or expense_date > last_valid_date:
                    last_valid_date = expense_date
                if status != "valid_2022":
                    continue

                if first_in_year is None or expense_date < first_in_year:
                    first_in_year = expense_date
                if last_in_year is None or expense_date > last_in_year:
                    last_in_year = expense_date
                month_bucket = months[expense_date.month]
                month_bucket["expense_count"] += 1
                month_bucket["amount_centavos"] += amount_centavos
                month_bucket["candidates"].add(candidate_id)
                if month_bucket["first_expense_date"] is None or expense_date < month_bucket["first_expense_date"]:
                    month_bucket["first_expense_date"] = expense_date
                if month_bucket["last_expense_date"] is None or expense_date > month_bucket["last_expense_date"]:
                    month_bucket["last_expense_date"] = expense_date
                period = "before" if expense_date < election_date else "on" if expense_date == election_date else "after"
                period_bucket = periods[period]
                period_bucket["expense_count"] += 1
                period_bucket["amount_centavos"] += amount_centavos
                period_bucket["candidates"].add(candidate_id)

            for month, bucket in months.items():
                first_month_date = bucket["first_expense_date"]
                last_month_date = bucket["last_expense_date"]
                monthly_rows.append({
                    "scenario": scenario,
                    "election_year": 2022,
                    "turn": 1,
                    "cargo": "Deputado Federal",
                    "month": f"2022-{month:02d}",
                    "month_number": month,
                    "first_expense_date": first_month_date.isoformat() if first_month_date else None,
                    "last_expense_date": last_month_date.isoformat() if last_month_date else None,
                    "expense_count": bucket["expense_count"],
                    "candidate_count": len(bucket["candidates"]),
                    "declared_expense_centavos": bucket["amount_centavos"],
                    "expense_basis": expense_basis,
                })
            for period, (rule, order) in period_rules.items():
                bucket = periods[period]
                event_rows.append({
                    "scenario": scenario,
                    "election_date": election_date.isoformat(),
                    "relative_period": period,
                    "period_order": order,
                    "date_rule": rule,
                    "expense_count": bucket["expense_count"],
                    "candidate_count": len(bucket["candidates"]),
                    "declared_expense_centavos": bucket["amount_centavos"],
                    "expense_basis": expense_basis,
                })
            date_quality_counts = {}
            for status in status_order:
                bucket = quality[status]
                date_quality_counts[status] = bucket["expense_count"]
                quality_rows.append({
                    "scenario": scenario,
                    "date_status": status,
                    "expense_count": bucket["expense_count"],
                    "candidate_count": len(bucket["candidates"]),
                    "declared_expense_centavos": bucket["amount_centavos"],
                    "first_valid_date": bucket["first_valid_date"].isoformat() if bucket["first_valid_date"] else None,
                    "last_valid_date": bucket["last_valid_date"].isoformat() if bucket["last_valid_date"] else None,
                    "example_raw_values": " | ".join(sorted(bucket["raw_examples"])[:5]),
                    "included_in_monthly_and_election_day_tables": status == "valid_2022",
                })
            scenario_results[scenario] = {
                "expense_count": expense_count,
                "candidate_count": len(all_candidates),
                "declared_expense_centavos": total_amount_centavos,
                "first_valid_date": first_valid_date.isoformat() if first_valid_date else None,
                "last_valid_date": last_valid_date.isoformat() if last_valid_date else None,
                "first_in_election_year": first_in_year.isoformat() if first_in_year else None,
                "last_in_election_year": last_in_year.isoformat() if last_in_year else None,
                "date_quality": date_quality_counts,
            }
    finally:
        connection.close()

    _write_csv(
        output_dir / "tse-2022-expense-temporal-monthly.csv",
        monthly_rows,
        [
            "scenario", "election_year", "turn", "cargo", "month", "month_number",
            "first_expense_date", "last_expense_date", "expense_count", "candidate_count",
            "declared_expense_centavos", "expense_basis",
        ],
    )
    _write_csv(
        output_dir / "tse-2022-expense-temporal-relative-to-election.csv",
        event_rows,
        [
            "scenario", "election_date", "relative_period", "period_order", "date_rule",
            "expense_count", "candidate_count", "declared_expense_centavos", "expense_basis",
        ],
    )
    _write_csv(
        output_dir / "tse-2022-expense-temporal-date-quality.csv",
        quality_rows,
        [
            "scenario", "date_status", "expense_count", "candidate_count",
            "declared_expense_centavos", "first_valid_date", "last_valid_date",
            "example_raw_values", "included_in_monthly_and_election_day_tables",
        ],
    )
    dictionary = [
        {"table": table, "field": field, "type": field_type, "definition": definition}
        for table, fields in {
            "tse-2022-expense-temporal-monthly.csv": [
                ("scenario", "text", "Cenário: principal deduplicado ou sensibilidade com todas as ocorrências."),
                ("election_year", "integer", "Ano eleitoral do recorte (2022)."),
                ("turn", "integer", "Turno eleitoral (1)."),
                ("cargo", "text", "Cargo do recorte (Deputado Federal)."),
                ("month", "text", "Mês de DT_DESPESA válida em 2022, formato AAAA-MM."),
                ("month_number", "integer", "Número do mês para ordenação cronológica no Power BI."),
                ("first_expense_date", "date nullable", "Primeira DT_DESPESA válida observada no mês."),
                ("last_expense_date", "date nullable", "Última DT_DESPESA válida observada no mês."),
                ("expense_count", "integer", "Quantidade de linhas de despesa do cenário no mês."),
                ("candidate_count", "integer", "Candidatos distintos com linha de despesa válida no mês; não somável entre meses."),
                ("declared_expense_centavos", "integer", "Soma de VR_DESPESA_CONTRATADA das linhas no mês, em centavos."),
                ("expense_basis", "text", "Despesa contratada declarada; não equivale a pagamento."),
            ],
            "tse-2022-expense-temporal-relative-to-election.csv": [
                ("scenario", "text", "Cenário: principal deduplicado ou sensibilidade com todas as ocorrências."),
                ("election_date", "date", "Data da votação: 2022-10-02."),
                ("relative_period", "text", "before (<), on (=) ou after (>) a data da votação."),
                ("period_order", "integer", "Ordem cronológica: antes=1, no dia=2, depois=3."),
                ("date_rule", "text", "Regra de inclusão de DT_DESPESA válida no período."),
                ("expense_count", "integer", "Quantidade de linhas de despesa no período."),
                ("candidate_count", "integer", "Candidatos distintos com linha de despesa no período."),
                ("declared_expense_centavos", "integer", "Soma de VR_DESPESA_CONTRATADA no período, em centavos."),
                ("expense_basis", "text", "Despesa contratada declarada; não equivale a pagamento."),
            ],
            "tse-2022-expense-temporal-date-quality.csv": [
                ("scenario", "text", "Cenário: principal deduplicado ou sensibilidade com todas as ocorrências."),
                ("date_status", "text", "valid_2022, outside_2022, missing ou invalid."),
                ("expense_count", "integer", "Quantidade de linhas classificadas neste estado de DT_DESPESA."),
                ("candidate_count", "integer", "Candidatos distintos com linha neste estado; pode haver interseção entre estados."),
                ("declared_expense_centavos", "integer", "Soma declarada das linhas neste estado, em centavos."),
                ("first_valid_date", "date nullable", "Primeira data válida para o estado; vazio quando ausente/inválida."),
                ("last_valid_date", "date nullable", "Última data válida para o estado; vazio quando ausente/inválida."),
                ("example_raw_values", "text", "Exemplos de valores originais ausentes/inválidos, quando houver."),
                ("included_in_monthly_and_election_day_tables", "boolean", "Verdadeiro somente para data válida dentro de 2022."),
            ],
        }.items()
        for field, field_type, definition in fields
    ]
    _write_csv(
        output_dir / "tse-2022-expense-temporal-dictionary.csv",
        dictionary,
        ["table", "field", "type", "definition"],
    )
    recut = {
        "election_year": 2022,
        "turn": 1,
        "cargo": "Deputado Federal",
        "candidate_status": "APTO (CD_SITUACAO_CANDIDATURA=12)",
        "submission_type": "Final",
        "date_field": "DT_DESPESA",
        "not_date_fields": ["DT_PRESTACAO_CONTAS", "DT_GERACAO"],
        "date_format": "DD/MM/YYYY",
        "monthly_and_election_day_window": ["2022-01-01", "2022-12-31"],
        "election_date": election_date.isoformat(),
        "expense_unit": "linha de despesa; no cenário deduplicado, linhas retidas por expenses; na sensibilidade, todas as ocorrências de expense_occurrences",
        "deduplication_rule": "reutiliza expenses e suas referências de origem; deduplicação integral já materializada pelo pipeline para o mesmo snapshot/membro",
        "date_quality_policy": {
            "missing": "nulo, vazio, #NULO ou #NE",
            "invalid": "valor não ausente que não pode ser interpretado como DD/MM/YYYY",
            "outside_2022": "data válida cujo ano não é 2022; reportada, mas fora das tabelas mensais/evento",
            "valid_2022": "data válida em 2022; entra nas tabelas mensais e relativa à votação",
        },
        "scenarios": scenario_results,
        "interpretation_limit": "DT_DESPESA é a data registrada da despesa, não data de pagamento, prestação ou geração do arquivo.",
        "outputs": [
            "tse-2022-expense-temporal-monthly.csv",
            "tse-2022-expense-temporal-relative-to-election.csv",
            "tse-2022-expense-temporal-date-quality.csv",
            "tse-2022-expense-temporal-dictionary.csv",
        ],
    }
    (output_dir / "tse-2022-expense-temporal-recut.json").write_text(
        json.dumps(recut, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return recut

def _read_validation(path: Path) -> dict[str, Any]:
    validation = json.loads(path.read_text(encoding="utf-8"))
    if validation.get("status") != "approved":
        raise ValueError("análise exige validação do pipeline com status approved")
    denominator = validation.get("vote_denominator")
    if not denominator or denominator.get("uf_count") != 27:
        raise ValueError("validação não comprova denominador oficial reconciliado para as 27 UFs")
    fatal_counts = validation.get("fatal_counts")
    if not isinstance(fatal_counts, dict) or not fatal_counts or any(int(value) != 0 for value in fatal_counts.values()):
        raise ValueError("análise exige todas as contagens fatais da validação iguais a zero")
    return validation


def _expense_totals(connection: sqlite3.Connection, deduplicated: bool) -> dict[str, int]:
    if deduplicated:
        query = """
            SELECT e.sq_candidate, SUM(e.amount_centavos) AS amount_centavos
            FROM expenses e
            JOIN expense_occurrences o
              ON o._source_member = e.source_member AND o._source_row = e.source_row
            JOIN candidates c ON c.sq_candidate = e.sq_candidate
            WHERE c.candidate_status_code = '12'
              AND c.election_year = 2022 AND c.turn = 1 AND c.cargo_code = '6'
              AND o.TP_PRESTACAO_CONTAS = 'Final'
            GROUP BY e.sq_candidate
        """
        return {row[0]: int(row[1]) for row in connection.execute(query)}

    totals: dict[str, int] = {}
    query = """
        SELECT o.SQ_CANDIDATO, o.VR_DESPESA_CONTRATADA
        FROM expense_occurrences o
        JOIN candidates c ON c.sq_candidate = o.SQ_CANDIDATO
        WHERE c.candidate_status_code = '12'
          AND c.election_year = 2022 AND c.turn = 1 AND c.cargo_code = '6'
          AND o.TP_PRESTACAO_CONTAS = 'Final'
        ORDER BY o._source_member, o._source_row
    """
    for candidate_id, amount in connection.execute(query):
        totals[candidate_id] = totals.get(candidate_id, 0) + _centavos(amount)
    return totals


def _expense_survey_by_type(
    connection: sqlite3.Connection,
    status_code: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    candidates = {
        row[0]
        for row in connection.execute(
            "SELECT sq_candidate FROM candidates WHERE candidate_status_code = ? AND election_year = 2022 AND turn = 1 AND cargo_code = '6'",
            (status_code,),
        )
    }
    raw_types: dict[str, dict[str, Any]] = {}
    per_candidate_type: dict[tuple[str, str], int] = {}
    raw_query = """
        SELECT o.SQ_CANDIDATO, o.TP_PRESTACAO_CONTAS, o.VR_DESPESA_CONTRATADA
        FROM expense_occurrences o
        JOIN candidates c ON c.sq_candidate = o.SQ_CANDIDATO
        WHERE c.candidate_status_code = ?
          AND c.election_year = 2022 AND c.turn = 1 AND c.cargo_code = '6'
        ORDER BY o._source_member, o._source_row
    """
    for candidate_id, raw_type, raw_amount in connection.execute(raw_query, (status_code,)):
        submission_type = "(não informado)" if _missing(raw_type) else str(raw_type).strip()
        amount = _centavos(raw_amount)
        summary = raw_types.setdefault(
            submission_type,
            {"candidates": set(), "rows": 0, "zero_rows": 0, "amount_centavos": 0},
        )
        summary["candidates"].add(candidate_id)
        summary["rows"] += 1
        summary["zero_rows"] += int(amount == 0)
        summary["amount_centavos"] += amount
        key = (candidate_id, submission_type)
        per_candidate_type[key] = per_candidate_type.get(key, 0) + amount

    deduplicated_types: dict[str, dict[str, Any]] = {}
    excluded_candidates_by_type: dict[str, set[str]] = {}
    excluded_rows_by_type: dict[str, int] = {}
    exclusion_query = """
        SELECT o.SQ_CANDIDATO, o.TP_PRESTACAO_CONTAS
        FROM expense_dedup_exclusions x
        JOIN expense_occurrences o
          ON o._source_archive = x.source_archive
         AND o._source_member = x.source_member
         AND o._source_row = x.source_row
        JOIN candidates c ON c.sq_candidate = o.SQ_CANDIDATO
        WHERE c.candidate_status_code = ?
          AND c.election_year = 2022 AND c.turn = 1 AND c.cargo_code = '6'
    """
    for candidate_id, raw_type in connection.execute(exclusion_query, (status_code,)):
        submission_type = "(não informado)" if _missing(raw_type) else str(raw_type).strip()
        excluded_candidates_by_type.setdefault(submission_type, set()).add(candidate_id)
        excluded_rows_by_type[submission_type] = excluded_rows_by_type.get(submission_type, 0) + 1
    deduplicated_query = """
        SELECT e.sq_candidate, o.TP_PRESTACAO_CONTAS, e.amount_centavos
        FROM expenses e
        JOIN expense_occurrences o
          ON o._source_member = e.source_member AND o._source_row = e.source_row
        JOIN candidates c ON c.sq_candidate = e.sq_candidate
        WHERE c.candidate_status_code = ?
          AND c.election_year = 2022 AND c.turn = 1 AND c.cargo_code = '6'
        ORDER BY e.source_member, e.source_row
    """
    for candidate_id, raw_type, amount in connection.execute(deduplicated_query, (status_code,)):
        submission_type = "(não informado)" if _missing(raw_type) else str(raw_type).strip()
        summary = deduplicated_types.setdefault(submission_type, {"candidates": set(), "rows": 0, "amount_centavos": 0})
        summary["candidates"].add(candidate_id)
        summary["rows"] += 1
        summary["amount_centavos"] += int(amount)

    rows: list[dict[str, Any]] = []
    for submission_type in sorted(set(raw_types) | set(deduplicated_types)):
        raw = raw_types.get(submission_type, {"candidates": set(), "rows": 0, "zero_rows": 0, "amount_centavos": 0})
        deduplicated = deduplicated_types.get(submission_type, {"candidates": set(), "rows": 0, "amount_centavos": 0})
        zero_candidates = sum(
            amount == 0
            for (candidate, kind), amount in per_candidate_type.items()
            if kind == submission_type
        )
        excluded_count = excluded_rows_by_type.get(submission_type, 0)
        if excluded_count != raw["rows"] - deduplicated["rows"]:
            raise ValueError(f"exclusões não reconciliam para status {status_code}, prestação {submission_type}")
        rows.append({
            "tp_prestacao_contas": submission_type,
            "candidate_status_code": status_code,
            "candidate_count": len(candidates),
            "candidates_with_rows": len(raw["candidates"]),
            "candidates_without_rows": len(candidates) - len(raw["candidates"]),
            "candidates_with_zero_total": zero_candidates,
            "all_lines_occurrence_rows": raw["rows"],
            "all_lines_zero_amount_rows": raw["zero_rows"],
            "all_lines_declared_expense_centavos": raw["amount_centavos"],
            "deduplicated_occurrence_rows": deduplicated["rows"],
            "deduplicated_candidates_with_rows": len(deduplicated["candidates"]),
            "deduplicated_declared_expense_centavos": deduplicated["amount_centavos"],
            "excluded_occurrence_rows": excluded_count,
            "excluded_affected_candidates": len(excluded_candidates_by_type.get(submission_type, set())),
            "excluded_amount_centavos": raw["amount_centavos"] - deduplicated["amount_centavos"],
        })
    any_rows = {candidate for candidate, _ in per_candidate_type}
    return rows, {
        "candidate_count": len(candidates),
        "candidates_with_any_expense_rows": len(any_rows),
        "candidates_without_any_expense_rows": len(candidates - any_rows),
        "expense_occurrence_rows": sum(row["all_lines_occurrence_rows"] for row in rows),
        "deduplicated_occurrence_rows": sum(row["deduplicated_occurrence_rows"] for row in rows),
        "all_lines_declared_expense_centavos": sum(row["all_lines_declared_expense_centavos"] for row in rows),
        "deduplicated_declared_expense_centavos": sum(row["deduplicated_declared_expense_centavos"] for row in rows),
    }


def _design_matrix(
    frame: pd.DataFrame,
    include_demographics: bool,
    interaction: bool,
    include_age: bool = True,
    race_interaction: bool = False,
    categorical_levels: dict[str, list[str]] | None = None,
) -> tuple[pd.DataFrame, list[str]]:
    if interaction and race_interaction:
        raise ValueError("interações por sexo e raça exigem amostras distintas")
    design = pd.DataFrame(index=frame.index)
    design["intercept"] = 1.0
    design["log1p_expense_brl"] = frame["log1p_expense_brl"].astype(float)
    if include_age:
        design["age_at_election"] = frame["age_at_election"].astype(float)
    categorical = ["uf", "party_code"]
    if include_demographics:
        categorical += ["gender", "race", "schooling"]
    if interaction:
        categorical.remove("gender")
    if race_interaction:
        categorical.remove("race")
    for column in categorical:
        values = frame[column].astype(str)
        levels = (categorical_levels or {}).get(column)
        category_values = pd.Categorical(values, categories=levels) if levels else values
        dummies = pd.get_dummies(
            category_values,
            prefix=column,
            drop_first=True,
            dtype=float,
        )
        design = pd.concat([design, dummies], axis=1)
    if interaction:
        design["female"] = (frame["gender"] == "FEMININO").astype(float)
        design["expense_x_female"] = design["log1p_expense_brl"] * design["female"]
    if race_interaction:
        design["black_brown"] = (frame["race_group"] == "pretas_pardas").astype(float)
        design["expense_x_black_brown"] = design["log1p_expense_brl"] * design["black_brown"]
    return design, categorical


def _fit_election_model(name: str, frame: pd.DataFrame, expense_column: str) -> tuple[dict[str, Any], dict[str, Any]]:
    model_frame = frame.copy()
    model_frame["log1p_expense_brl"] = model_frame[expense_column].astype(float).div(100).map(math.log1p)
    design, categorical = _design_matrix(model_frame, include_demographics=True, interaction=False)
    if np.linalg.matrix_rank(design.to_numpy()) != design.shape[1]:
        raise ValueError(f"matriz do modelo {name} tem colinearidade exata; estimativa não foi publicada")
    fitted = sm.GLM(model_frame["elected"].astype(float), design, family=sm.families.Binomial()).fit(maxiter=100, cov_type="HC1")
    if not fitted.converged:
        raise ValueError(f"modelo {name} não convergiu")
    conf = fitted.conf_int().loc["log1p_expense_brl"]
    coefficient = float(fitted.params["log1p_expense_brl"])
    return {
        "name": name,
        "n": int(fitted.nobs),
        "elected_n": int(model_frame["elected"].sum()),
        "not_elected_n": int(len(model_frame) - model_frame["elected"].sum()),
        "coefficient_log1p_expense_brl": coefficient,
        "odds_ratio_per_log_unit": float(math.exp(coefficient)),
        "odds_ratio_ci95_lower": float(math.exp(conf.iloc[0])),
        "odds_ratio_ci95_upper": float(math.exp(conf.iloc[1])),
        "p_value": float(fitted.pvalues["log1p_expense_brl"]),
        "robust_se_hc1": float(fitted.bse["log1p_expense_brl"]),
        "controls": ["UF", "partido", "idade na data da eleição", "sexo", "raça", "escolaridade"],
        "family": "logit binário com erros-padrão robustos HC1",
        "excluded_predictors": ["votos", "custo por voto"],
    }, {
        "model": name,
        "term": "log1p_expense_brl",
        "coefficient": coefficient,
        "robust_se_hc1": float(fitted.bse["log1p_expense_brl"]),
        "ci95_low": float(conf.iloc[0]),
        "ci95_high": float(conf.iloc[1]),
        "p_value": float(fitted.pvalues["log1p_expense_brl"]),
    }


def _election_race_design_matrix(
    frame: pd.DataFrame,
    *,
    include_expense: bool,
    categorical_levels: dict[str, list[str]] | None = None,
) -> tuple[pd.DataFrame, list[str]]:
    design = pd.DataFrame(index=frame.index)
    design["intercept"] = 1.0
    if include_expense:
        design["log1p_expense_brl"] = frame["log1p_expense_brl"].astype(float)
    design["age_at_election"] = frame["age_at_election"].astype(float)
    categorical = ["uf", "party_code", "gender", "schooling"]
    for column in categorical:
        values = frame[column].astype(str)
        levels = (categorical_levels or {}).get(column)
        category_values = pd.Categorical(values, categories=levels) if levels else values
        dummies = pd.get_dummies(
            category_values,
            prefix=column,
            drop_first=True,
            dtype=float,
        )
        dummies.index = frame.index
        design = pd.concat([design, dummies], axis=1)
    design["black_brown"] = frame["race_group"].eq("pretas_pardas").astype(float)
    return design, categorical


def _fit_election_race_model(
    name: str,
    frame: pd.DataFrame,
    expense_column: str | None,
) -> tuple[dict[str, Any], Any, pd.DataFrame, np.ndarray, dict[str, list[str]]]:
    model_frame = frame.copy()
    include_expense = expense_column is not None
    if include_expense:
        model_frame["log1p_expense_brl"] = (
            model_frame[expense_column].astype(float).div(100).map(math.log1p)
        )
    design, categorical = _election_race_design_matrix(
        model_frame,
        include_expense=include_expense,
    )
    if np.linalg.matrix_rank(design.to_numpy()) != design.shape[1]:
        raise ValueError(f"matriz do modelo {name} tem colinearidade exata")
    n, parameter_count = design.shape
    if n <= parameter_count:
        raise ValueError(f"modelo {name} não permite correção HC1 com N≤K")
    fitted = sm.GLM(
        model_frame["elected"].astype(float),
        design,
        family=sm.families.Binomial(),
    ).fit(maxiter=100, cov_type="HC0")
    if not fitted.converged:
        raise ValueError(f"modelo {name} não convergiu")
    correction_factor = n / (n - parameter_count)
    covariance_hc1 = np.asarray(fitted.cov_params(), dtype=float) * correction_factor
    standard_errors = np.sqrt(np.diag(covariance_hc1))
    if not np.isfinite(covariance_hc1).all() or not np.isfinite(standard_errors).all():
        raise ValueError(f"modelo {name} tem covariância HC1 ou erros-padrão não finitos")
    categorical_levels = {
        column: sorted(model_frame[column].astype(str).unique().tolist())
        for column in categorical
    }
    return {
        "name": name,
        "n": int(n),
        "elected_n": int(model_frame["elected"].sum()),
        "not_elected_n": int(len(model_frame) - model_frame["elected"].sum()),
        "parameter_count": int(parameter_count),
        "converged": bool(fitted.converged),
        "covariance": "HC1: covariância HC0 multiplicada por N/(N−K)",
        "hc1_correction_factor": correction_factor,
        "controls": ["UF", "partido", "idade na data da eleição", "sexo", "escolaridade"],
        "race_reference": "brancas",
        "black_brown_group": "autodeclarações PRETA + PARDA",
        "expense_column": expense_column,
    }, fitted, model_frame, covariance_hc1, categorical_levels


def _marginal_election_race_prediction(
    fitted: Any,
    standardization_frame: pd.DataFrame,
    race_group: str,
    *,
    include_expense: bool,
    categorical_levels: dict[str, list[str]],
    covariance_matrix: np.ndarray,
) -> dict[str, Any]:
    prediction_frame = standardization_frame.copy()
    prediction_frame["race_group"] = race_group
    design, _ = _election_race_design_matrix(
        prediction_frame,
        include_expense=include_expense,
        categorical_levels=categorical_levels,
    )
    design = design.reindex(columns=fitted.model.exog_names, fill_value=0.0)
    matrix = design.to_numpy(dtype=float)
    if not np.isfinite(matrix).all():
        invalid_columns = [
            column for column in design.columns
            if not np.isfinite(design[column].to_numpy(dtype=float)).all()
        ]
        raise ValueError(f"matriz padronizada contém valores não finitos: {invalid_columns}")
    linear_predictor = matrix @ fitted.params.to_numpy(dtype=float)
    if not np.isfinite(linear_predictor).all():
        raise ValueError("preditor linear marginal contém valores não finitos")
    probabilities = 1 / (1 + np.exp(-np.clip(linear_predictor, -40, 40)))
    prediction = float(probabilities.mean())
    gradient = (matrix * (probabilities * (1 - probabilities))[:, None]).mean(axis=0)
    covariance = np.asarray(covariance_matrix, dtype=float)
    variance = max(0.0, float(gradient @ covariance @ gradient))
    standard_error = math.sqrt(variance)
    margin = 1.959963984540054 * standard_error
    if not all(np.isfinite(value) for value in (prediction, standard_error, margin)):
        raise ValueError(
            f"previsão marginal de eleição ou seu IC não é finito: "
            f"predição={prediction}, erro-padrão={standard_error}, margem={margin}, "
            f"betas_finitos={np.isfinite(fitted.params.to_numpy(dtype=float)).all()}"
        )
    return {
        "prediction": prediction,
        "ci95_lower": max(0.0, prediction - margin),
        "ci95_upper": min(1.0, prediction + margin),
        "gradient": gradient,
    }


def _fit_model(
    name: str,
    frame: pd.DataFrame,
    include_demographics: bool,
    interaction: bool,
    include_age: bool = True,
) -> tuple[dict[str, Any], list[dict[str, Any]], Any, pd.DataFrame]:
    model_frame = frame
    if interaction:
        model_frame = frame[frame["gender"].isin(["FEMININO", "MASCULINO"])].copy()
    design, categorical = _design_matrix(model_frame, include_demographics, interaction, include_age)
    required_controls = ["uf", "party_code"]
    if include_age:
        required_controls.append("age_at_election")
    if include_demographics:
        required_controls.extend(["gender", "race", "schooling"])
    missing_columns = [column for column in required_controls if model_frame[column].isna().any()]
    if missing_columns:
        raise ValueError(f"amostra do modelo contém controles ausentes: {', '.join(missing_columns)}")
    if np.linalg.matrix_rank(design.to_numpy()) != design.shape[1]:
        raise ValueError(f"matriz do modelo {name} tem colinearidade exata; estimativa não foi publicada")
    fitted = sm.GLM(model_frame["vote_share"], design, family=sm.families.Binomial()).fit(maxiter=100, cov_type="HC1")
    if not fitted.converged:
        raise ValueError(f"modelo {name} não convergiu")
    conf = fitted.conf_int()
    coefficient_rows = []
    for term, estimate in fitted.params.items():
        coefficient_rows.append({
            "model": name,
            "term": term,
            "coefficient": float(estimate),
            "robust_se_hc1": float(fitted.bse[term]),
            "ci95_low": float(conf.loc[term, 0]),
            "ci95_high": float(conf.loc[term, 1]),
            "p_value": float(fitted.pvalues[term]),
        })
    controls = ["UF", "partido"]
    if include_age:
        controls.append("idade na data da eleição")
    if include_demographics:
        controls.extend(["sexo", "raça", "escolaridade"])
    return {
        "name": name,
        "n": int(fitted.nobs),
        "converged": bool(fitted.converged),
        "covariance": "HC1 robusta",
        "family": "logit fracionário (GLM Binomial)",
        "controls": controls,
        "interaction": interaction,
        "deviance": float(fitted.deviance),
        "aic": float(fitted.aic),
        "categorical_controls": categorical,
    }, coefficient_rows, fitted, model_frame


def _fit_race_interaction(
    name: str,
    frame: pd.DataFrame,
    expense_column: str,
) -> tuple[dict[str, Any], list[dict[str, Any]], Any, pd.DataFrame, np.ndarray]:
    model_frame = frame.copy()
    model_frame["log1p_expense_brl"] = (
        model_frame[expense_column].astype(float).div(100).map(math.log1p)
    )
    design, categorical = _design_matrix(
        model_frame,
        include_demographics=True,
        interaction=False,
        include_age=True,
        race_interaction=True,
    )
    required_controls = [
        "uf", "party_code", "age_at_election", "gender", "schooling", "race_group",
    ]
    missing_columns = [column for column in required_controls if model_frame[column].isna().any()]
    if missing_columns:
        raise ValueError(f"amostra do modelo {name} contém controles ausentes: {', '.join(missing_columns)}")
    if np.linalg.matrix_rank(design.to_numpy()) != design.shape[1]:
        raise ValueError(f"matriz do modelo {name} tem colinearidade exata; estimativa não foi publicada")
    fitted = sm.GLM(
        model_frame["vote_share"],
        design,
        family=sm.families.Binomial(),
    ).fit(maxiter=100, cov_type="HC0")
    if not fitted.converged:
        raise ValueError(f"modelo {name} não convergiu")
    n = int(fitted.nobs)
    parameter_count = design.shape[1]
    if n <= parameter_count:
        raise ValueError(f"modelo {name} não permite correção HC1 com N≤K")
    correction_factor = n / (n - parameter_count)
    covariance_hc1 = np.asarray(fitted.cov_params(), dtype=float) * correction_factor
    standard_errors = pd.Series(
        np.sqrt(np.diag(covariance_hc1)),
        index=fitted.params.index,
    )
    z_critical = 1.959963984540054
    coefficients = []
    for term, estimate in fitted.params.items():
        se = float(standard_errors[term])
        z_score = float(estimate) / se
        coefficients.append({
            "model": name,
            "term": term,
            "coefficient": float(estimate),
            "robust_se_hc1": se,
            "ci95_low": float(estimate) - z_critical * se,
            "ci95_high": float(estimate) + z_critical * se,
            "p_value": math.erfc(abs(z_score) / math.sqrt(2)),
        })
    return {
        "name": name,
        "n": n,
        "converged": bool(fitted.converged),
        "covariance": "HC1: covariância HC0 multiplicada por N/(N−K)",
        "hc1_correction_factor": correction_factor,
        "parameter_count": parameter_count,
        "family": "logit fracionário (GLM Binomial)",
        "outcome": "participação de votos nominais válidos na UF",
        "controls": ["UF", "partido", "idade na data da eleição", "sexo", "escolaridade"],
        "interaction": "log1p_expense_brl × black_brown",
        "race_reference": "brancas",
        "black_brown_group": "autodeclarações PRETA + PARDA",
        "excluded_predictors": ["custo por voto", "votos nominais"],
        "categorical_controls": categorical,
    }, coefficients, fitted, model_frame, covariance_hc1


def _fit_ols_sensitivity(name: str, frame: pd.DataFrame, response: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    design, categorical = _design_matrix(frame, include_demographics=True, interaction=False)
    if np.linalg.matrix_rank(design.to_numpy()) != design.shape[1]:
        raise ValueError(f"matriz do modelo {name} tem colinearidade exata; estimativa não foi publicada")
    fitted = sm.OLS(frame[response], design).fit(cov_type="HC1")
    conf = fitted.conf_int()
    coefficients = [
        {
            "model": name,
            "term": term,
            "coefficient": float(estimate),
            "robust_se_hc1": float(fitted.bse[term]),
            "ci95_low": float(conf.loc[term, 0]),
            "ci95_high": float(conf.loc[term, 1]),
            "p_value": float(fitted.pvalues[term]),
        }
        for term, estimate in fitted.params.items()
    ]
    return {
        "name": name,
        "n": int(fitted.nobs),
        "converged": True,
        "covariance": "HC1 robusta",
        "family": "OLS de sensibilidade",
        "outcome": response,
        "controls": ["UF", "partido", "idade na data da eleição", "sexo", "raça", "escolaridade"],
        "interaction": False,
        "r_squared": float(fitted.rsquared),
        "rmse": float(math.sqrt(fitted.mse_resid)),
        "categorical_controls": categorical,
    }, coefficients

def _marginal_prediction(
    fitted: Any,
    standardization_frame: pd.DataFrame,
    expense_centavos: float,
    *,
    interaction: bool = False,
    gender: str | None = None,
    race_interaction: bool = False,
    race_group: str | None = None,
    categorical_levels: dict[str, list[str]] | None = None,
    covariance_matrix: np.ndarray | None = None,
) -> dict[str, float]:
    prediction_frame = standardization_frame.copy()
    prediction_frame["log1p_expense_brl"] = math.log1p(float(expense_centavos) / 100)
    if gender is not None:
        prediction_frame["gender"] = gender
    if race_group is not None:
        prediction_frame["race_group"] = race_group
    design, _ = _design_matrix(
        prediction_frame,
        include_demographics=True,
        interaction=interaction,
        include_age=True,
        race_interaction=race_interaction,
        categorical_levels=categorical_levels,
    )
    design = design.reindex(columns=fitted.model.exog_names, fill_value=0.0)
    matrix = design.to_numpy(dtype=float)
    linear_predictor = matrix @ fitted.params.to_numpy(dtype=float)
    probability = 1 / (1 + np.exp(-np.clip(linear_predictor, -40, 40)))
    mean_prediction = float(probability.mean())
    gradient = (matrix * (probability * (1 - probability))[:, None]).mean(axis=0)
    covariance = np.asarray(
        fitted.cov_params() if covariance_matrix is None else covariance_matrix,
        dtype=float,
    )
    variance = max(0.0, float(gradient @ covariance @ gradient))
    standard_error = math.sqrt(variance)
    margin = 1.959963984540054 * standard_error
    return {
        "prediction": mean_prediction,
        "ci95_lower": max(0.0, mean_prediction - margin),
        "ci95_upper": min(1.0, mean_prediction + margin),
        "standard_error": standard_error,
    }


def _fit_diagnostics(fitted: Any, frame: pd.DataFrame) -> dict[str, Any]:
    observed = frame["vote_share"].to_numpy(dtype=float)
    predicted = np.asarray(fitted.fittedvalues, dtype=float)
    residual = observed - predicted
    calibration_frame = pd.DataFrame(
        {"observed": observed, "predicted": predicted},
        index=frame.index,
    )
    calibration_frame["decile"] = pd.qcut(
        calibration_frame["predicted"],
        q=10,
        labels=False,
        duplicates="drop",
    )
    calibration_deciles = []
    for decile, group in calibration_frame.groupby("decile", observed=True):
        mean_observed = float(group["observed"].mean())
        mean_predicted = float(group["predicted"].mean())
        calibration_deciles.append({
            "decile": int(decile) + 1,
            "n": int(len(group)),
            "mean_observed_vote_share": mean_observed,
            "mean_predicted_vote_share": mean_predicted,
            "calibration_gap": mean_observed - mean_predicted,
        })
    return {
        "n": int(len(frame)),
        "mean_observed_vote_share": float(observed.mean()),
        "mean_predicted_vote_share": float(predicted.mean()),
        "rmse": float(np.sqrt(np.mean(residual ** 2))),
        "mae": float(np.mean(np.abs(residual))),
        "max_absolute_decile_calibration_gap": max(abs(row["calibration_gap"]) for row in calibration_deciles),
        "calibration_deciles": calibration_deciles,
        "evaluation": "calibração na própria amostra; não é validação externa",
    }


def _influence_diagnostics(
    fitted: Any,
    frame: pd.DataFrame,
    expense_column: str,
) -> dict[str, Any]:
    influence = fitted.get_influence(observed=True)
    cooks_distance = np.asarray(influence.cooks_distance[0], dtype=float)
    leverage = np.asarray(influence.hat_matrix_diag, dtype=float)
    fitted_values = np.asarray(fitted.fittedvalues, dtype=float)
    expense_index = fitted.model.exog_names.index("log1p_expense_brl")
    expense_dfbetas = np.asarray(influence.dfbetas[:, expense_index], dtype=float)
    n = len(frame)
    threshold = 4 / n
    finite_cooks = np.isfinite(cooks_distance)
    finite_dfbeta = np.isfinite(expense_dfbetas)
    top_indices = np.argsort(np.where(finite_cooks, cooks_distance, -np.inf))[::-1][:10]
    max_cook = float(np.max(cooks_distance[finite_cooks])) if finite_cooks.any() else None
    max_abs_dfbeta = float(np.max(np.abs(expense_dfbetas[finite_dfbeta]))) if finite_dfbeta.any() else None
    top_candidates = []
    for rank, position in enumerate(top_indices, start=1):
        candidate = frame.iloc[int(position)]
        top_candidates.append({
            "rank": rank,
            "sq_candidate": candidate["sq_candidate"],
            "expense_brl": float(candidate[expense_column]) / 100,
            "observed_vote_share": float(candidate["vote_share"]),
            "fitted_vote_share": float(fitted_values[int(position)]),
            "cooks_distance": float(cooks_distance[position]) if finite_cooks[position] else None,
            "leverage": float(leverage[position]),
            "dfbeta_log1p_expense": float(expense_dfbetas[position]) if finite_dfbeta[position] else None,
        })
    return {
        "n": n,
        "screening_rule": "Distância de Cook > 4/N; triagem heurística, sem exclusão automática de candidaturas",
        "cook_distance_screen_threshold": threshold,
        "candidates_above_cook_screen": int(np.count_nonzero(cooks_distance > threshold)),
        "maximum_cook_distance": max_cook,
        "maximum_leverage": float(leverage.max()),
        "maximum_absolute_expense_dfbeta": max_abs_dfbeta,
        "top_influential_candidates": top_candidates,
    }


def _build_prediction_and_diagnostic_tables(
    fitted_models: dict[str, tuple[Any, pd.DataFrame, str]],
    complete_case_frame: pd.DataFrame,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    spending_quantiles = (("Q25", 0.25), ("Mediana", 0.5), ("Q75", 0.75))
    spending_values = [
        int(np.quantile(
            complete_case_frame["expense_deduplicated_centavos"].to_numpy(dtype=float),
            quantile,
            method="nearest",
        ))
        for _, quantile in spending_quantiles
    ]
    scenario_comparison = []
    for (label, quantile), expense_centavos in zip(spending_quantiles, spending_values):
        dedup_fit, dedup_frame, _ = fitted_models["deduplicado_completo"]
        all_rows_fit, all_rows_frame, _ = fitted_models["todas_as_linhas_completo"]
        dedup_prediction = _marginal_prediction(dedup_fit, dedup_frame, expense_centavos)
        all_rows_prediction = _marginal_prediction(all_rows_fit, all_rows_frame, expense_centavos)
        scenario_comparison.append({
            "expense_level": label,
            "expense_quantile": quantile,
            "expense_brl": expense_centavos / 100,
            "deduplicated_prediction": dedup_prediction["prediction"],
            "deduplicated_ci95_lower": dedup_prediction["ci95_lower"],
            "deduplicated_ci95_upper": dedup_prediction["ci95_upper"],
            "all_rows_prediction": all_rows_prediction["prediction"],
            "all_rows_ci95_lower": all_rows_prediction["ci95_lower"],
            "all_rows_ci95_upper": all_rows_prediction["ci95_upper"],
            "difference_percentage_points": (
                all_rows_prediction["prediction"] - dedup_prediction["prediction"]
            ) * 100,
            "standardization_n": len(dedup_frame),
        })

    interaction_fit, interaction_frame, _ = fitted_models["deduplicado_interacao_sexo"]
    female_expenses = interaction_frame.loc[
        interaction_frame["gender"] == "FEMININO", "expense_deduplicated_centavos"
    ].to_numpy(dtype=float)
    male_expenses = interaction_frame.loc[
        interaction_frame["gender"] == "MASCULINO", "expense_deduplicated_centavos"
    ].to_numpy(dtype=float)
    female_lower, female_upper = np.quantile(female_expenses, (0.05, 0.95), method="nearest")
    male_lower, male_upper = np.quantile(male_expenses, (0.05, 0.95), method="nearest")
    common_lower = max(float(female_lower), float(male_lower))
    common_upper = min(float(female_upper), float(male_upper))
    if common_lower >= common_upper:
        raise ValueError("faixa central de despesas de mulheres e homens não tem suporte comum")
    curve_expenses = np.unique(np.rint(np.linspace(common_lower, common_upper, 21)).astype(int))
    sex_curve_points = []
    for expense_centavos in curve_expenses:
        male_prediction = _marginal_prediction(
            interaction_fit,
            interaction_frame,
            int(expense_centavos),
            interaction=True,
            gender="MASCULINO",
        )
        female_prediction = _marginal_prediction(
            interaction_fit,
            interaction_frame,
            int(expense_centavos),
            interaction=True,
            gender="FEMININO",
        )
        sex_curve_points.append({
            "expense_brl": int(expense_centavos) / 100,
            "male_prediction": male_prediction["prediction"],
            "male_ci95_lower": male_prediction["ci95_lower"],
            "male_ci95_upper": male_prediction["ci95_upper"],
            "female_prediction": female_prediction["prediction"],
            "female_ci95_lower": female_prediction["ci95_lower"],
            "female_ci95_upper": female_prediction["ci95_upper"],
            "female_minus_male_percentage_points": (
                female_prediction["prediction"] - male_prediction["prediction"]
            ) * 100,
        })
    prediction_tables = {
        "scenario_comparison": scenario_comparison,
        "sex_interaction_curve": {
            "support_definition": "interseção dos intervalos P5–P95 das despesas Final deduplicadas de mulheres e homens",
            "common_support": {
                "female_p05_brl": float(female_lower) / 100,
                "female_p95_brl": float(female_upper) / 100,
                "male_p05_brl": float(male_lower) / 100,
                "male_p95_brl": float(male_upper) / 100,
                "lower_brl": common_lower / 100,
                "upper_brl": common_upper / 100,
            },
            "standardization_n": len(interaction_frame),
            "points": sex_curve_points,
        },
        "standardization": "média de previsões na escala de participação sobre a mesma distribuição de controles completos; fixa-se a despesa e, nas curvas de interação, o sexo",
        "uncertainty_method": "ICs pontuais de 95% pelo método delta para médias padronizadas, usando a covariância sanduíche HC1 do modelo; não são intervalos individuais. Diferenças entre cenários são estimativas pontuais sem IC próprio.",
    }

    model_diagnostics: dict[str, Any] = {}
    calibration_rows = []
    influence_rows = []
    for model_name in ("deduplicado_completo", "todas_as_linhas_completo"):
        fitted, fitted_frame, expense_column = fitted_models[model_name]
        fit = _fit_diagnostics(fitted, fitted_frame)
        influence = _influence_diagnostics(fitted, fitted_frame, expense_column)
        model_diagnostics[model_name] = {"fit": fit, "influence": influence}
        calibration_rows.extend(
            {"model": model_name, **row}
            for row in fit["calibration_deciles"]
        )
        influence_rows.extend(
            {"model": model_name, **row}
            for row in influence["top_influential_candidates"]
        )

    cutoff_centavos = float(np.quantile(
        complete_case_frame["expense_deduplicated_centavos"].to_numpy(dtype=float),
        0.99,
        method="nearest",
    ))
    tail_frame = complete_case_frame.loc[
        complete_case_frame["expense_deduplicated_centavos"] <= cutoff_centavos
    ].copy()
    excluded_tail_count = len(complete_case_frame) - len(tail_frame)
    tail_sensitivity = []
    for scenario, source_model, expense_column in (
        ("deduplicado", "deduplicado_completo", "expense_deduplicated_centavos"),
        ("todas_as_linhas", "todas_as_linhas_completo", "expense_all_lines_centavos"),
    ):
        full_fitted = fitted_models[source_model][0]
        trimmed_frame = tail_frame.copy()
        trimmed_frame["log1p_expense_brl"] = (
            trimmed_frame[expense_column].astype(float).div(100).map(math.log1p)
        )
        _, _, trimmed_fit, _ = _fit_model(
            f"{source_model}_sem_top_1pct",
            trimmed_frame,
            include_demographics=True,
            interaction=False,
            include_age=True,
        )
        full_interval = full_fitted.conf_int().loc["log1p_expense_brl"]
        trimmed_interval = trimmed_fit.conf_int().loc["log1p_expense_brl"]
        tail_sensitivity.append({
            "scenario": scenario,
            "cutoff_rule": "1% superior da distribuição de despesas deduplicadas (P99; candidaturas acima do limite removidas apenas neste diagnóstico)",
            "cutoff_brl": cutoff_centavos / 100,
            "excluded_candidates": excluded_tail_count,
            "n_after_exclusion": int(trimmed_fit.nobs),
            "full_coefficient": float(full_fitted.params["log1p_expense_brl"]),
            "trimmed_coefficient": float(trimmed_fit.params["log1p_expense_brl"]),
            "trimmed_ci95_lower": float(trimmed_interval.iloc[0]),
            "trimmed_ci95_upper": float(trimmed_interval.iloc[1]),
            "coefficient_change": float(
                trimmed_fit.params["log1p_expense_brl"] - full_fitted.params["log1p_expense_brl"]
            ),
            "full_ci95_lower": float(full_interval.iloc[0]),
            "full_ci95_upper": float(full_interval.iloc[1]),
        })
    model_diagnostics["top_one_percent_expense_sensitivity"] = tail_sensitivity
    return prediction_tables, model_diagnostics, calibration_rows, influence_rows


def _race_category(value: Any) -> str:
    return "(ausente)" if _missing(value) else str(value).strip().upper()


def _race_quantile_brl(values: pd.Series, probability: float) -> float | None:
    if values.empty:
        return None
    return float(np.quantile(values.to_numpy(dtype=float), probability, method="linear") / 100)


def _build_race_curve(
    scenario: str,
    fitted: Any,
    frame: pd.DataFrame,
    expense_column: str,
    covariance_matrix: np.ndarray,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    categorical_levels = {
        column: sorted(frame[column].astype(str).unique().tolist())
        for column in ("uf", "party_code", "gender", "schooling")
    }
    local_support_rows: list[dict[str, Any]] = []
    local_intervals: dict[tuple[str, str], tuple[float, float]] = {}
    eligible_cells: set[tuple[str, str]] = set()
    dimension_columns = (
        ("UF", ["uf"]),
        ("partido", ["party_code"]),
        ("UF×partido", ["uf", "party_code"]),
    )
    total_group_counts = {
        group: int((frame["race_group"] == group).sum())
        for group in ("brancas", "pretas_pardas")
    }
    for dimension, columns in dimension_columns:
        for key, stratum_frame in frame.groupby(columns, sort=True, dropna=False):
            key_values = key if isinstance(key, tuple) else (key,)
            stratum = " × ".join(str(value) for value in key_values)
            white = stratum_frame.loc[stratum_frame["race_group"] == "brancas"]
            black_brown = stratum_frame.loc[stratum_frame["race_group"] == "pretas_pardas"]
            white_p10 = _race_quantile_brl(white[expense_column].astype(float), 0.10)
            white_p90 = _race_quantile_brl(white[expense_column].astype(float), 0.90)
            black_p10 = _race_quantile_brl(black_brown[expense_column].astype(float), 0.10)
            black_p90 = _race_quantile_brl(black_brown[expense_column].astype(float), 0.90)
            lower = max(white_p10, black_p10) if white_p10 is not None and black_p10 is not None else None
            upper = min(white_p90, black_p90) if white_p90 is not None and black_p90 is not None else None
            eligible = len(white) >= 10 and len(black_brown) >= 10
            if dimension == "UF×partido" and eligible:
                cell_key = (str(key_values[0]), str(key_values[1]))
                eligible_cells.add(cell_key)
                if lower is not None and upper is not None and lower < upper:
                    local_intervals[cell_key] = (lower * 100, upper * 100)
            local_support_rows.append({
                "scenario": scenario,
                "dimension": dimension,
                "stratum": stratum,
                "brancas_n": int(len(white)),
                "pretas_pardas_n": int(len(black_brown)),
                "brancas_p10_brl": white_p10,
                "brancas_p90_brl": white_p90,
                "pretas_pardas_p10_brl": black_p10,
                "pretas_pardas_p90_brl": black_p90,
                "common_p10_p90_lower_brl": lower,
                "common_p10_p90_upper_brl": upper,
                "eligible_uf_party_cell": bool(eligible) if dimension == "UF×partido" else None,
                "brancas_share_of_group_in_stratum": len(white) / max(1, total_group_counts["brancas"]),
                "pretas_pardas_share_of_group_in_stratum": len(black_brown) / max(1, total_group_counts["pretas_pardas"]),
            })

    frame_cell_keys = list(zip(frame["uf"].astype(str), frame["party_code"].astype(str)))
    eligible_mask = pd.Series(
        [key in eligible_cells for key in frame_cell_keys],
        index=frame.index,
    )
    eligible_frame = frame.loc[eligible_mask].copy()
    eligible_group_counts = {
        group: int((eligible_frame["race_group"] == group).sum())
        for group in ("brancas", "pretas_pardas")
    }

    total_group_counts = {
        group: int((frame["race_group"] == group).sum())
        for group in ("brancas", "pretas_pardas")
    }
    initial_lower = initial_upper = None
    candidate_expenses: np.ndarray = np.array([], dtype=int)
    if not eligible_frame.empty:
        white_expenses = eligible_frame.loc[
            eligible_frame["race_group"] == "brancas", expense_column
        ].to_numpy(dtype=float)
        black_expenses = eligible_frame.loc[
            eligible_frame["race_group"] == "pretas_pardas", expense_column
        ].to_numpy(dtype=float)
        if len(white_expenses) and len(black_expenses):
            initial_lower = max(
                float(np.quantile(white_expenses, 0.10, method="linear")),
                float(np.quantile(black_expenses, 0.10, method="linear")),
            )
            initial_upper = min(
                float(np.quantile(white_expenses, 0.90, method="linear")),
                float(np.quantile(black_expenses, 0.90, method="linear")),
            )
            if initial_lower < initial_upper:
                candidate_expenses = np.unique(
                    np.rint(np.linspace(initial_lower, initial_upper, 21)).astype(int)
                )

    curve_points = []
    candidate_support = []
    for expense_centavos in candidate_expenses:
        supported_cells = {
            cell_key
            for cell_key, (lower_centavos, upper_centavos) in local_intervals.items()
            if lower_centavos <= expense_centavos <= upper_centavos
        }
        supported_mask = pd.Series(
            [key in supported_cells for key in frame_cell_keys],
            index=frame.index,
        )
        standardization_frame = frame.loc[supported_mask].copy()
        supported_counts = {
            group: int((standardization_frame["race_group"] == group).sum())
            for group in ("brancas", "pretas_pardas")
        }
        coverage = {
            group: supported_counts[group] / max(1, total_group_counts[group])
            for group in ("brancas", "pretas_pardas")
        }
        publish = coverage["brancas"] >= 0.80 and coverage["pretas_pardas"] >= 0.80
        candidate_row = {
            "scenario": scenario,
            "expense_brl": expense_centavos / 100,
            "brancas_supported_n": supported_counts["brancas"],
            "pretas_pardas_supported_n": supported_counts["pretas_pardas"],
            "brancas_coverage": coverage["brancas"],
            "pretas_pardas_coverage": coverage["pretas_pardas"],
            "supported_uf_party_cells_n": len(supported_cells),
            "standardization_n": len(standardization_frame),
            "published": publish,
            "supported_uf_party_strata": [
                f"{uf} × {party}" for uf, party in sorted(supported_cells)
            ],
        }
        candidate_support.append(candidate_row)
        if not publish:
            continue
        white_prediction = _marginal_prediction(
            fitted,
            standardization_frame,
            int(expense_centavos),
            race_interaction=True,
            race_group="brancas",
            categorical_levels=categorical_levels,
            covariance_matrix=covariance_matrix,
        )
        black_prediction = _marginal_prediction(
            fitted,
            standardization_frame,
            int(expense_centavos),
            race_interaction=True,
            race_group="pretas_pardas",
            categorical_levels=categorical_levels,
            covariance_matrix=covariance_matrix,
        )
        curve_points.append({
            **candidate_row,
            "brancas_prediction": white_prediction["prediction"],
            "brancas_ci95_lower": white_prediction["ci95_lower"],
            "brancas_ci95_upper": white_prediction["ci95_upper"],
            "pretas_pardas_prediction": black_prediction["prediction"],
            "pretas_pardas_ci95_lower": black_prediction["ci95_lower"],
            "pretas_pardas_ci95_upper": black_prediction["ci95_upper"],
            "difference_pretas_pardas_minus_brancas_pp": (
                black_prediction["prediction"] - white_prediction["prediction"]
            ) * 100,
        })
    if curve_points:
        no_curve_reason = None
    elif not eligible_cells:
        no_curve_reason = "nenhuma célula UF×partido alcançou 10 candidaturas em cada grupo"
    elif initial_lower is None or initial_upper is None or initial_lower >= initial_upper:
        no_curve_reason = "não há intervalo P10–P90 comum nos dois grupos dentro das células elegíveis"
    else:
        no_curve_reason = "cobertura das células com suporte ficou abaixo de 80% em pelo menos um grupo"
    return {
        "scenario": scenario,
        "minimum_group_n_per_uf_party": 10,
        "minimum_group_coverage_for_curve": 0.80,
        "eligible_uf_party_cells_n": len(eligible_cells),
        "eligible_group_counts": eligible_group_counts,
        "eligible_group_coverage": {
            group: eligible_group_counts[group] / max(1, total_group_counts[group])
            for group in ("brancas", "pretas_pardas")
        },
        "initial_common_support_lower_brl": initial_lower / 100 if initial_lower is not None else None,
        "initial_common_support_upper_brl": initial_upper / 100 if initial_upper is not None else None,
        "candidate_support_points": candidate_support,
        "points": curve_points,
        "no_curve_reason": no_curve_reason,
    }, local_support_rows, candidate_support


def _build_race_secondary(
    frame: pd.DataFrame,
    apto_candidates: list[dict[str, Any]],
) -> tuple[
    dict[str, Any],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    population = frame.copy()
    population["race_category"] = population["race"].map(_race_category)
    vote_observed_category_counts = {
        category: int(count)
        for category, count in population["race_category"].value_counts(dropna=False).sort_index().items()
    }
    apto_categories = [_race_category(candidate.get("race")) for candidate in apto_candidates]
    category_counts = {
        category: int(count)
        for category, count in pd.Series(apto_categories).value_counts().sort_index().items()
    }
    category_counts.setdefault("(ausente)", 0)
    vote_observed_category_counts.setdefault("(ausente)", 0)
    race_group = population["race"].map(
        lambda value: "brancas" if _race_category(value) == "BRANCA"
        else "pretas_pardas" if _race_category(value) in {"PRETA", "PARDA"}
        else None
    )
    population["race_group"] = race_group
    comparison_population = population.loc[population["race_group"].notna()].copy()
    controls = ["uf", "party_code", "age_at_election", "gender", "schooling"]
    complete_columns = [
        "expense_deduplicated_centavos",
        "expense_all_lines_centavos",
        "vote_share",
        *controls,
    ]
    complete_mask = (
        comparison_population[complete_columns].notna().all(axis=1)
        & comparison_population["race_group"].notna()
    )
    complete = comparison_population.loc[complete_mask].copy()
    complete["black_brown"] = complete["race_group"].eq("pretas_pardas").astype(int)
    comparison_group_counts = {
        "brancas": int(category_counts.get("BRANCA", 0)),
        "pretas_pardas": int(category_counts.get("PRETA", 0) + category_counts.get("PARDA", 0)),
    }
    comparison_group_counts_with_votes = {
        group: int((population["race_group"] == group).sum())
        for group in ("brancas", "pretas_pardas")
    }
    outside_comparison_counts = {
        category: count
        for category, count in category_counts.items()
        if category != "BRANCA" and category not in {"PRETA", "PARDA"}
    }
    binary_apto_candidate_ids = {
        str(candidate["sq_candidate"])
        for candidate in apto_candidates
        if _race_category(candidate.get("race")) in {"BRANCA", "PRETA", "PARDA"}
    }
    observed_candidate_ids = set(population["sq_candidate"].astype(str))
    binary_apto_n = len(binary_apto_candidate_ids)
    missing_vote_or_denominator_n = len(binary_apto_candidate_ids - observed_candidate_ids)
    missing_controls = comparison_population[controls].isna().any(axis=1)
    missing_either_expense = comparison_population[
        ["expense_deduplicated_centavos", "expense_all_lines_centavos"]
    ].isna().any(axis=1)
    models = []
    coefficients = []
    fitted_by_scenario: dict[str, tuple[Any, pd.DataFrame, str, np.ndarray]] = {}
    for scenario, name, expense_column in (
        ("deduplicado", "raca_deduplicado", "expense_deduplicated_centavos"),
        ("todas_as_linhas", "raca_todas_as_linhas", "expense_all_lines_centavos"),
    ):
        model, estimates, fitted, model_frame, covariance_hc1 = _fit_race_interaction(
            name,
            complete,
            expense_column,
        )
        model["expense_scenario"] = scenario
        models.append(model)
        coefficients.extend(estimates)
        fitted_by_scenario[scenario] = fitted, model_frame, expense_column, covariance_hc1

    descriptive_rows = []
    for group_name in ("brancas", "pretas_pardas"):
        group = complete.loc[complete["race_group"] == group_name]
        elected_n = int(group["candidate_total_status_code"].isin({"2", "3"}).sum())
        not_elected_n = int(group["candidate_total_status_code"].isin({"4", "5"}).sum())
        classified_n = elected_n + not_elected_n
        unclassified_n = len(group) - classified_n
        for scenario, expense_column in (
            ("deduplicado", "expense_deduplicated_centavos"),
            ("todas_as_linhas", "expense_all_lines_centavos"),
        ):
            expenses = group[expense_column].astype(float)
            votes = group["valid_nominal_votes"].astype(float)
            vote_share = group["vote_share"].astype(float) * 100
            descriptive_rows.append({
                "scenario": scenario,
                "race_group": group_name,
                "race_group_label": "Brancas" if group_name == "brancas" else "Pretas + pardas",
                "candidate_count": int(len(group)),
                "expense_observed_n": int(expenses.notna().sum()),
                "expense_median_brl": float(expenses.median() / 100),
                "expense_q25_brl": _race_quantile_brl(expenses, 0.25),
                "expense_q75_brl": _race_quantile_brl(expenses, 0.75),
                "nominal_votes_observed_n": int(votes.notna().sum()),
                "nominal_votes_median": float(votes.median()),
                "nominal_votes_q25": float(votes.quantile(0.25)),
                "nominal_votes_q75": float(votes.quantile(0.75)),
                "vote_share_observed_n": int(vote_share.notna().sum()),
                "vote_share_median_pct": float(vote_share.median()),
                "vote_share_q25_pct": float(vote_share.quantile(0.25)),
                "vote_share_q75_pct": float(vote_share.quantile(0.75)),
                "elected_count": elected_n,
                "not_elected_count": not_elected_n,
                "election_classified_n": classified_n,
                "unclassified_result_n": unclassified_n,
                "elected_proportion": elected_n / classified_n if classified_n else None,
                "election_denominator_definition": "candidaturas com código oficial 2, 3, 4 ou 5",
            })

    classified_election = complete.loc[
        complete["candidate_total_status_code"].isin({"2", "3", "4", "5"})
    ].copy()
    election_group_counts = {
        group: int((classified_election["race_group"] == group).sum())
        for group in ("brancas", "pretas_pardas")
    }
    election_counts = {
        group: int(
            (
                classified_election["race_group"].eq(group)
                & classified_election["candidate_total_status_code"].isin({"2", "3"})
            ).sum()
        )
        for group in ("brancas", "pretas_pardas")
    }
    observed_election_proportions = {
        group: election_counts[group] / election_group_counts[group]
        if election_group_counts[group]
        else None
        for group in ("brancas", "pretas_pardas")
    }
    observed_difference_pp = (
        (
            observed_election_proportions["pretas_pardas"]
            - observed_election_proportions["brancas"]
        )
        * 100
        if all(value is not None for value in observed_election_proportions.values())
        else None
    )
    eligible_election_cells = set()
    for key, cell in classified_election.groupby(["uf", "party_code"], sort=True):
        group_counts = cell["race_group"].value_counts()
        if group_counts.get("brancas", 0) >= 10 and group_counts.get("pretas_pardas", 0) >= 10:
            eligible_election_cells.add((str(key[0]), str(key[1])))
    election_cell_keys = list(
        zip(classified_election["uf"].astype(str), classified_election["party_code"].astype(str))
    )
    eligible_election_mask = pd.Series(
        [key in eligible_election_cells for key in election_cell_keys],
        index=classified_election.index,
    )
    eligible_election_frame = classified_election.loc[eligible_election_mask]
    eligible_election_group_counts = {
        group: int((eligible_election_frame["race_group"] == group).sum())
        for group in ("brancas", "pretas_pardas")
    }
    election_group_coverage = {
        group: eligible_election_group_counts[group] / max(1, election_group_counts[group])
        for group in ("brancas", "pretas_pardas")
    }
    election_support_sufficient = all(
        election_group_coverage[group] >= 0.80
        for group in ("brancas", "pretas_pardas")
    )
    eligible_elected_counts = {
        group: int(
            (
                eligible_election_frame["race_group"].eq(group)
                & eligible_election_frame["candidate_total_status_code"].isin({"2", "3"})
            ).sum()
        )
        for group in ("brancas", "pretas_pardas")
    }
    eligible_not_elected_counts = {
        group: eligible_election_group_counts[group] - eligible_elected_counts[group]
        for group in ("brancas", "pretas_pardas")
    }
    outcome_support_sufficient = all(
        eligible_elected_counts[group] >= 10 and eligible_not_elected_counts[group] >= 10
        for group in ("brancas", "pretas_pardas")
    )
    election_adjusted_models = []
    election_adjusted_estimates = []
    if not election_support_sufficient:
        election_adjustment_status = "adjustment_withheld_insufficient_common_support"
        election_withheld_reason = (
            "células UF×partido com pelo menos 10 candidaturas por grupo cobrem menos de 80% "
            "de pelo menos um grupo; probabilidades nacionais ajustadas dependeriam de extrapolação"
        )
    elif not outcome_support_sufficient:
        election_adjustment_status = "adjustment_withheld_sparse_election_outcomes"
        election_withheld_reason = (
            "a população com suporte tem menos de 10 candidaturas eleitas ou não eleitas em pelo "
            "menos um dos grupos"
        )
    else:
        election_model_frame = eligible_election_frame.copy()
        election_model_frame["elected"] = (
            election_model_frame["candidate_total_status_code"].isin({"2", "3"}).astype(int)
        )
        model_specs = (
            ("controls_only", None),
            ("controls_plus_deduplicated_expense", "expense_deduplicated_centavos"),
            ("controls_plus_all_lines_expense", "expense_all_lines_centavos"),
        )
        try:
            for model_name, expense_column in model_specs:
                model_summary, fitted, model_frame, covariance_hc1, categorical_levels = (
                    _fit_election_race_model(model_name, election_model_frame, expense_column)
                )
                include_expense = expense_column is not None
                white_prediction = _marginal_election_race_prediction(
                    fitted,
                    model_frame,
                    "brancas",
                    include_expense=include_expense,
                    categorical_levels=categorical_levels,
                    covariance_matrix=covariance_hc1,
                )
                black_prediction = _marginal_election_race_prediction(
                    fitted,
                    model_frame,
                    "pretas_pardas",
                    include_expense=include_expense,
                    categorical_levels=categorical_levels,
                    covariance_matrix=covariance_hc1,
                )
                difference_gradient = black_prediction["gradient"] - white_prediction["gradient"]
                difference_variance = max(
                    0.0,
                    float(difference_gradient @ covariance_hc1 @ difference_gradient),
                )
                difference_standard_error_pp = math.sqrt(difference_variance) * 100
                difference_pp = (
                    black_prediction["prediction"] - white_prediction["prediction"]
                ) * 100
                difference_margin_pp = 1.959963984540054 * difference_standard_error_pp
                if not all(np.isfinite(value) for value in (difference_pp, difference_standard_error_pp, difference_margin_pp)):
                    raise ValueError(f"modelo {model_name} tem diferença ajustada ou IC não finitos")
                model_summary["standardization_n"] = len(model_frame)
                election_adjusted_models.append(model_summary)
                election_adjusted_estimates.append({
                    "model": model_name,
                    "population_n": len(model_frame),
                    "brancas": {
                        key: white_prediction[key]
                        for key in ("prediction", "ci95_lower", "ci95_upper")
                    },
                    "pretas_pardas": {
                        key: black_prediction[key]
                        for key in ("prediction", "ci95_lower", "ci95_upper")
                    },
                    "difference_pretas_pardas_minus_brancas_pp": difference_pp,
                    "difference_ci95_lower_pp": difference_pp - difference_margin_pp,
                    "difference_ci95_upper_pp": difference_pp + difference_margin_pp,
                })
        except (ValueError, np.linalg.LinAlgError, FloatingPointError, OverflowError) as error:
            election_adjusted_models = []
            election_adjusted_estimates = []
            election_adjustment_status = "adjustment_withheld_model_instability"
            election_withheld_reason = f"instabilidade ou matriz não identificável: {error}"
        else:
            election_adjustment_status = "adjusted_models_estimated"
            election_withheld_reason = None
    election_adjusted_comparison = {
        "status": election_adjustment_status,
        "common_population_n": int(len(classified_election)),
        "group_counts": election_group_counts,
        "elected_counts": election_counts,
        "observed_proportions": observed_election_proportions,
        "observed_difference_pretas_pardas_minus_brancas_pp": observed_difference_pp,
        "support": {
            "minimum_group_n_per_uf_party_cell": 10,
            "minimum_coverage_per_group": 0.80,
            "eligible_uf_party_cells_n": len(eligible_election_cells),
            "supported_population_n": int(len(eligible_election_frame)),
            "eligible_group_counts": eligible_election_group_counts,
            "coverage_by_group": election_group_coverage,
            "elected_counts_in_supported_population": eligible_elected_counts,
            "not_elected_counts_in_supported_population": eligible_not_elected_counts,
            "minimum_elected_and_not_elected_per_group": 10,
            "common_support_sufficient": election_support_sufficient,
            "outcome_support_sufficient": outcome_support_sufficient,
            "sufficient": election_support_sufficient and outcome_support_sufficient,
        },
        "controls": ["UF", "partido", "idade na data da eleição", "sexo", "escolaridade"],
        "specifications": [
            {
                "name": name,
                "common_population_n": int(len(classified_election)),
                "model_population_n": (
                    int(len(eligible_election_frame))
                    if election_support_sufficient and outcome_support_sufficient
                    else None
                ),
            }
            for name, _ in (
                ("controls_only", None),
                ("controls_plus_deduplicated_expense", "expense_deduplicated_centavos"),
                ("controls_plus_all_lines_expense", "expense_all_lines_centavos"),
            )
        ],
        "models": election_adjusted_models,
        "adjusted_estimates": election_adjusted_estimates,
        "withheld_reason": election_withheld_reason,
    }

    curves = {}
    support_rows = []
    curve_support_rows = []
    for scenario, (fitted, model_frame, expense_column, covariance_hc1) in fitted_by_scenario.items():
        curve, support, candidate_support = _build_race_curve(
            scenario,
            fitted,
            model_frame,
            expense_column,
            covariance_hc1,
        )
        curves[scenario] = curve
        support_rows.extend(support)
        curve_support_rows.extend(candidate_support)
    result = {
        "population": {
            "apto_candidates_n": len(apto_candidates),
            "apto_with_votes_n": int(len(population)),
            "race_category_counts": category_counts,
            "race_category_counts_with_votes": vote_observed_category_counts,
            "comparison_group_counts": comparison_group_counts,
            "comparison_group_counts_with_votes": comparison_group_counts_with_votes,
            "outside_comparison_counts": outside_comparison_counts,
            "outside_comparison_counts_with_votes": {
                category: count
                for category, count in vote_observed_category_counts.items()
                if category != "BRANCA" and category not in {"PRETA", "PARDA"}
            },
            "comparison_groups": {
                "brancas": "autodeclaração BRANCA",
                "pretas_pardas": "autodeclarações PRETA + PARDA",
            },
        },
        "comparison_binary_apto_n": binary_apto_n,
        "comparison_binary_population_n": int(len(comparison_population)),
        "comparison_complete_case_n": int(len(complete)),
        "comparison_complete_case_group_counts": {
            group: int((complete["race_group"] == group).sum())
            for group in ("brancas", "pretas_pardas")
        },
        "comparison_exclusions": {
            "binary_group_candidates_without_complete_data": int(binary_apto_n - len(complete)),
            "missing_vote_or_denominator_n": missing_vote_or_denominator_n,
            "missing_either_expense_n": int(missing_either_expense.sum()),
            "missing_controls_n": int(missing_controls.sum()),
            "overlap_missing_expense_and_controls_n": int((missing_either_expense & missing_controls).sum()),
        },
        "official_result_codes": {
            "elected": {"2": "ELEITO POR QP", "3": "ELEITO POR MÉDIA"},
            "not_elected": {"4": "NÃO ELEITO", "5": "SUPLENTE"},
        },
        "models": models,
        "coefficients": coefficients,
        "descriptive_by_group": descriptive_rows,
        "election_adjusted_comparison": election_adjusted_comparison,
        "curves": curves,
        "support_method": (
            "células UF×partido com N≥10 em cada grupo; faixas locais P10–P90; "
            "pontos publicados somente quando as células sustentam ≥80% de cada grupo"
        ),
        "interpretation": (
            "análise secundária acrescentada após os primeiros resultados; associação ajustada, não causal; "
            "despesa contratada declarada não implica pagamento ou recurso público"
        ),
    }
    return result, descriptive_rows, coefficients, support_rows, curve_support_rows


def _race_curve_svg(curve: dict[str, Any]) -> str:
    width, height = 820, 500
    left, right, top, bottom = 88, 28, 54, 78
    points = curve["points"]
    title = "Participação de votos prevista por despesa e raça/cor"
    if not points:
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" '
            f'aria-label="{title}"><text x="{width / 2}" y="70" text-anchor="middle" font-size="20">{title}</text>'
            f'<text x="{width / 2}" y="{height / 2}" text-anchor="middle" font-size="17">Curva não exibida: {curve["no_curve_reason"]}.</text>'
            f'<text x="{width / 2}" y="{height / 2 + 32}" text-anchor="middle" font-size="14">Ver tabela de suporte UF × partido para contagens e cobertura.</text></svg>'
        )
    point_by_expense = {round(row["expense_brl"], 2): row for row in points}
    segments: list[list[dict[str, Any]]] = []
    current_segment: list[dict[str, Any]] = []
    for support in curve["candidate_support_points"]:
        point = point_by_expense.get(round(support["expense_brl"], 2))
        if support["published"] and point is not None:
            current_segment.append(point)
        elif current_segment:
            segments.append(current_segment)
            current_segment = []
    if current_segment:
        segments.append(current_segment)
    x_values = [row["expense_brl"] for row in points]
    y_values = [
        value
        for row in points
        for value in (
            row["brancas_ci95_lower"],
            row["brancas_ci95_upper"],
            row["pretas_pardas_ci95_lower"],
            row["pretas_pardas_ci95_upper"],
        )
    ]
    x_min, x_max = min(x_values), max(x_values)
    y_min = max(0.0, min(y_values) - 0.02)
    y_max = min(1.0, max(y_values) + 0.02)
    if y_min >= y_max:
        y_min, y_max = 0.0, 1.0
    plot_width, plot_height = width - left - right, height - top - bottom
    sx = lambda value: left + (value - x_min) / max(1e-9, x_max - x_min) * plot_width
    sy = lambda value: top + (y_max - value) / (y_max - y_min) * plot_height
    pieces = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-label="{title}">',
        f'<text x="{width / 2}" y="28" text-anchor="middle" font-size="20">{title}</text>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height - bottom}" stroke="currentColor"/>',
        f'<line x1="{left}" y1="{height - bottom}" x2="{width - right}" y2="{height - bottom}" stroke="currentColor"/>',
        f'<text x="{left - 12}" y="{top + 6}" text-anchor="end" font-size="13">{_pt_decimal(y_max * 100, 1)}%</text>',
        f'<text x="{left - 12}" y="{height - bottom + 5}" text-anchor="end" font-size="13">{_pt_decimal(y_min * 100, 1)}%</text>',
        f'<text x="{width / 2}" y="{height - 20}" text-anchor="middle" font-size="14">Despesa contratada declarada (R$)</text>',
        f'<text x="22" y="{height / 2}" text-anchor="middle" font-size="14" transform="rotate(-90 22 {height / 2})">Participação de votos nominais válidos</text>',
        f'<text x="{left}" y="{height - bottom + 25}" text-anchor="start" font-size="13">R$ {_pt_decimal(x_min, 0)}</text>',
        f'<text x="{width - right}" y="{height - bottom + 25}" text-anchor="end" font-size="13">R$ {_pt_decimal(x_max, 0)}</text>',
    ]
    for prefix, label, dash, opacity in (
        ("brancas", "Brancas", "", "0.18"),
        ("pretas_pardas", "Pretas + pardas", ' stroke-dasharray="7 4"', "0.10"),
    ):
        for segment in segments:
            upper = " ".join(
                f"{sx(row['expense_brl']):.1f},{sy(row[f'{prefix}_ci95_upper']):.1f}"
                for row in segment
            )
            lower = " ".join(
                f"{sx(row['expense_brl']):.1f},{sy(row[f'{prefix}_ci95_lower']):.1f}"
                for row in reversed(segment)
            )
            line = " ".join(
                f"{sx(row['expense_brl']):.1f},{sy(row[f'{prefix}_prediction']):.1f}"
                for row in segment
            )
            if len(segment) > 1:
                pieces.append(f'<polygon points="{upper} {lower}" fill="currentColor" fill-opacity="{opacity}"/>')
                pieces.append(
                    f'<polyline points="{line}" fill="none" stroke="currentColor" stroke-width="3"{dash}/>'
                )
            else:
                row = segment[0]
                pieces.append(
                    f'<circle cx="{sx(row["expense_brl"]):.1f}" cy="{sy(row[f"{prefix}_prediction"]):.1f}" r="4" fill="currentColor"/>'
                )
    pieces.extend([
        f'<line x1="{left + 15}" y1="{top + 20}" x2="{left + 47}" y2="{top + 20}" stroke="currentColor" stroke-width="3"/>',
        f'<text x="{left + 54}" y="{top + 25}" font-size="14">Brancas</text>',
        f'<line x1="{left + 150}" y1="{top + 20}" x2="{left + 182}" y2="{top + 20}" stroke="currentColor" stroke-width="3" stroke-dasharray="7 4"/>',
        f'<text x="{left + 189}" y="{top + 25}" font-size="14">Pretas + pardas</text>',
        '<text x="50%" y="97%" text-anchor="middle" font-size="12">Médias ajustadas; faixas = IC pontual de 95%; linhas separadas onde falta suporte.</text>',
        '</svg>',
    ])
    return "".join(pieces)




def run_financial_analysis(database_path: Path, validation_path: Path, output_dir: Path) -> dict[str, Any]:
    validation = _read_validation(Path(validation_path))
    validation_path = Path(validation_path)
    data_root = validation_path.parent.parent.parent
    manifest_path = data_root / "manifests" / f"manifest-{validation.get('manifest_id')}.json"
    source_resource: dict[str, Any] = {}
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        source_resource = next(
            (resource for resource in manifest.get("resources", []) if resource.get("resource_key") == "vote_totals_2022"),
            {},
        )
    source_metadata = {
        "manifest_file": str(manifest_path) if manifest_path.is_file() else None,
        "official_source_url": source_resource.get("url"),
        "frozen_zip": source_resource.get("local_path"),
        "sha256": source_resource.get("file", {}).get("sha256"),
        "size_bytes": source_resource.get("file", {}).get("size_bytes"),
    }
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    try:
        table_names = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        payment_tables = sorted(name for name in table_names if "pag" in name.casefold() or "paid" in name.casefold())
        required = {"candidates", "votes", "vote_denominators", "expense_occurrences", "expenses"}
        if missing := required - table_names:
            raise ValueError(f"base derivada sem tabelas exigidas: {', '.join(sorted(missing))}")
        candidates = [dict(row) for row in connection.execute(
            """
            SELECT sq_candidate, uf, party_code, birth_date, gender, race, schooling,
                   candidate_status_code, candidate_total_status_code, candidate_total_status,
                   election_year, turn, cargo_code
            FROM candidates
            WHERE election_year = 2022 AND turn = 1 AND cargo_code = '6'
            ORDER BY sq_candidate
            """
        )]
        apto = [candidate for candidate in candidates if candidate["candidate_status_code"] == "12"]
        inapto = [candidate for candidate in candidates if candidate["candidate_status_code"] == "3"]
        vote_totals = {
            row[0]: int(row[1])
            for row in connection.execute("SELECT sq_candidate, SUM(valid_votes) FROM votes GROUP BY sq_candidate")
        }
        denominators = {row[0]: int(row[1]) for row in connection.execute("SELECT uf, valid_votes_total FROM vote_denominators")}
        vote_denominator_rows = [
            dict(row)
            for row in connection.execute(
                """
                SELECT uf, election_year, turn, cargo_code, cargo, valid_nominal_votes,
                       valid_legend_votes, valid_votes_total, source_row_count,
                       source_archive, source_member
                FROM vote_denominators ORDER BY uf
                """
            )
        ]
        if len(vote_denominator_rows) != 27 or any(
            row["valid_nominal_votes"] + row["valid_legend_votes"] != row["valid_votes_total"]
            for row in vote_denominator_rows
        ):
            raise ValueError("denominadores da base não cobrem 27 UFs com totais nominais + legenda reconciliados")
        deduplicated_expenses = _expense_totals(connection, deduplicated=True)
        all_expenses = _expense_totals(connection, deduplicated=False)
        apto_rows, apto_expense_summary = _expense_survey_by_type(connection, "12")
        inapto_rows, inapto_summary = _expense_survey_by_type(connection, "3")
        candidate_rows: list[dict[str, Any]] = []
        for candidate in apto:
            candidate_id = candidate["sq_candidate"]
            denominator = denominators.get(candidate["uf"])
            votes = vote_totals.get(candidate_id)
            if denominator is None or denominator <= 0 or votes is None or votes < 0 or votes > denominator:
                continue
            age = _age_at_election(candidate["birth_date"])
            candidate_rows.append({
                "sq_candidate": candidate_id,
                "uf": candidate["uf"],
                "party_code": None if _missing(candidate["party_code"]) else str(candidate["party_code"]),
                "age_at_election": age,
                "gender": None if _missing(candidate["gender"]) else str(candidate["gender"]).strip().upper(),
                "race": None if _missing(candidate["race"]) else str(candidate["race"]).strip().upper(),
                "schooling": None if _missing(candidate["schooling"]) else str(candidate["schooling"]).strip().upper(),
                "valid_nominal_votes": votes,
                "official_valid_votes": denominator,
                "vote_share": votes / denominator,
                "candidate_total_status_code": candidate["candidate_total_status_code"],
                "candidate_total_status": candidate["candidate_total_status"],
                "expense_deduplicated_centavos": deduplicated_expenses.get(candidate_id),
                "expense_all_lines_centavos": all_expenses.get(candidate_id),
            })
        frame = pd.DataFrame(candidate_rows)
        if frame.empty:
            raise ValueError("nenhuma candidatura APTO tem denominador e votos nominais válidos observados")
        complete_mask = frame[["expense_deduplicated_centavos", "expense_all_lines_centavos", "uf", "party_code", "age_at_election", "gender", "race", "schooling"]].notna().all(axis=1)
        model_frame = frame.loc[complete_mask].copy()
        missing_final_expense = frame["expense_deduplicated_centavos"].isna()
        control_columns = ["uf", "party_code", "age_at_election", "gender", "race", "schooling"]
        missing_controls = frame[control_columns].isna().any(axis=1)
        missing_controls_by_field = {column: int(frame[column].isna().sum()) for column in control_columns}
        exclusion_overlap = int((missing_final_expense & missing_controls).sum())
        zero_nominal_votes_apto = int(frame["valid_nominal_votes"].eq(0).sum())
        if model_frame.empty:
            raise ValueError("nenhuma candidatura completa para os modelos definidos no protocolo")
        election_frame = model_frame.loc[
            model_frame["candidate_total_status_code"].isin({"2", "3", "4", "5"})
        ].copy()
        election_frame["elected"] = election_frame["candidate_total_status_code"].isin({"2", "3"}).astype(int)
        election_models = []
        election_coefficients = []
        for name, expense_column in (
            ("eleicao_deduplicado", "expense_deduplicated_centavos"),
            ("eleicao_todas_as_linhas", "expense_all_lines_centavos"),
        ):
            model, coefficient = _fit_election_model(name, election_frame, expense_column)
            election_models.append(model)
            election_coefficients.append(coefficient)
        election_expense_comparison = []
        for elected, label in ((1, "eleitos"), (0, "nao_eleitos")):
            group = election_frame.loc[election_frame["elected"] == elected]
            for scenario, expense_column in (
                ("deduplicado", "expense_deduplicated_centavos"),
                ("todas_as_linhas", "expense_all_lines_centavos"),
            ):
                expenses = group[expense_column].astype(float) / 100
                positive_votes = group["valid_nominal_votes"] > 0
                costs = expenses.loc[positive_votes] / group.loc[positive_votes, "valid_nominal_votes"]
                election_expense_comparison.append({
                    "outcome": label,
                    "scenario": scenario,
                    "candidate_count": int(len(group)),
                    "expense_mean_brl": float(expenses.mean()),
                    "expense_median_brl": float(expenses.median()),
                    "cost_per_vote_n_positive_votes": int(positive_votes.sum()),
                    "cost_per_vote_excluded_zero_votes": int((~positive_votes).sum()),
                    "cost_per_vote_mean_brl": float(costs.mean()) if len(costs) else None,
                    "cost_per_vote_median_brl": float(costs.median()) if len(costs) else None,
                })
        band_frame = election_frame.copy()
        band_frame["expense_band_within_uf"] = band_frame.groupby("uf")[
            "expense_deduplicated_centavos"
        ].rank(method="first", pct=True).map(
            lambda percentile: min(4, int(math.ceil(percentile * 4)))
        )
        election_rates_by_uf_band = [
            {
                "uf": str(uf),
                "expense_band_within_uf": int(band),
                "candidate_count": int(len(group)),
                "elected_count": int(group["elected"].sum()),
                "elected_share": float(group["elected"].mean()),
                "expense_basis": "despesa Final deduplicada; quartis ranqueados dentro da UF",
            }
            for (uf, band), group in band_frame.groupby(["uf", "expense_band_within_uf"], sort=True)
        ]
        election_band_definitions = [
            {"expense_band_code": "ate_50_mil", "expense_band_label": "Até R$ 50 mil", "lower_exclusive_centavos": None, "upper_inclusive_centavos": 5_000_000},
            {"expense_band_code": "50_a_200_mil", "expense_band_label": "Acima de R$ 50 mil até R$ 200 mil", "lower_exclusive_centavos": 5_000_000, "upper_inclusive_centavos": 20_000_000},
            {"expense_band_code": "200_mil_a_1_milhao", "expense_band_label": "Acima de R$ 200 mil até R$ 1 milhão", "lower_exclusive_centavos": 20_000_000, "upper_inclusive_centavos": 100_000_000},
            {"expense_band_code": "acima_1_milhao", "expense_band_label": "Acima de R$ 1 milhão", "lower_exclusive_centavos": 100_000_000, "upper_inclusive_centavos": None},
        ]
        election_band_labels = {
            item["expense_band_code"]: item["expense_band_label"]
            for item in election_band_definitions
        }

        fixed_band_frame = election_frame.copy()
        fixed_band_frame["expense_band_code"] = fixed_band_frame["expense_deduplicated_centavos"].map(_fixed_expense_band)
        fixed_band_frame["expense_band_label"] = fixed_band_frame["expense_band_code"].map(election_band_labels)
        fixed_band_candidate_rows = [
            {
                "election_year": 2022,
                "turn": 1,
                "cargo": "Deputado Federal",
                "sq_candidate": str(row.sq_candidate),
                "uf": str(row.uf),
                "candidate_total_status_code": str(row.candidate_total_status_code),
                "expense_deduplicated_centavos": int(row.expense_deduplicated_centavos),
                "expense_all_lines_centavos": int(row.expense_all_lines_centavos),
                "expense_band_code": row.expense_band_code,
                "expense_band_label": row.expense_band_label,
                "elected": int(row.elected),
            }
            for row in fixed_band_frame.sort_values(["uf", "sq_candidate"]).itertuples(index=False)
        ]
        fixed_band_summary_rows = []
        for geography_type, geography_code, group in [
            ("BRASIL", "BR", fixed_band_frame),
            *[
                ("UF", str(uf), group)
                for uf, group in fixed_band_frame.groupby("uf", sort=True)
            ],
        ]:
            for definition in election_band_definitions:
                band_group = group.loc[group["expense_band_code"] == definition["expense_band_code"]]
                candidate_count = int(len(band_group))
                elected_count = int(band_group["elected"].sum())
                fixed_band_summary_rows.append({
                    "election_year": 2022,
                    "turn": 1,
                    "cargo": "Deputado Federal",
                    "geography_type": geography_type,
                    "geography_code": geography_code,
                    "expense_band_code": definition["expense_band_code"],
                    "expense_band_label": definition["expense_band_label"],
                    "lower_exclusive_centavos": definition["lower_exclusive_centavos"],
                    "upper_inclusive_centavos": definition["upper_inclusive_centavos"],
                    "candidate_count": candidate_count,
                    "elected_count": elected_count,
                    "elected_share": elected_count / candidate_count if candidate_count else None,
                    "denominator_definition": "candidaturas APTO com resultado oficial 2/3/4/5, despesa Final deduplicada e todas as covariáveis do recorte dos modelos eleitorais",
                    "expense_basis": "despesa Final deduplicada",
                })
        election_powerbi_recut = {
            "election_year": 2022,
            "turn": 1,
            "cargo": "Deputado Federal",
            "candidate_status": "APTO",
            "included_result_codes": {"2": "ELEITO POR QP", "3": "ELEITO POR MÉDIA", "4": "NÃO ELEITO", "5": "SUPLENTE"},
            "included_candidates": int(len(fixed_band_frame)),
            "elected_numerator": int(fixed_band_frame["elected"].sum()),
            "excluded_classified_results_for_missing_expense_or_controls": int(
                frame["candidate_total_status_code"].isin({"2", "3", "4", "5"}).sum() - len(election_frame)
            ),
            "excluded_other_or_missing_official_result_codes": int(
                len(frame) - frame["candidate_total_status_code"].isin({"2", "3", "4", "5"}).sum()
            ),
            "expense_basis": "VR_DESPESA_CONTRATADA em prestação Final; deduplicação integral usada na análise principal",
            "election_denominator": "candidaturas com resultado oficial classificável, despesa Final deduplicada presente e covariáveis completas, igual ao recorte dos modelos eleitorais",
            "rate": "eleitos (códigos 2 e 3) / candidaturas (códigos 2, 3, 4 e 5) no recorte",
            "bands": election_band_definitions,
            "quartile_analysis_preserved": "tse-2022-election-rate-by-uf-expense-band.csv; quartis ranqueados dentro da UF",
        }

        election_powerbi_dictionary = [
            {"table": "tse-2022-election-powerbi-candidates.csv", "field": "election_year", "type": "integer", "definition": "Ano da eleição; 2022."},
            {"table": "tse-2022-election-powerbi-candidates.csv", "field": "turn", "type": "integer", "definition": "Turno eleitoral; primeiro turno."},
            {"table": "tse-2022-election-powerbi-candidates.csv", "field": "cargo", "type": "text", "definition": "Cargo; Deputado Federal."},
            {"table": "tse-2022-election-powerbi-candidates.csv", "field": "sq_candidate", "type": "text", "definition": "Identificador único da candidatura no TSE."},
            {"table": "tse-2022-election-powerbi-candidates.csv", "field": "uf", "type": "text", "definition": "UF da candidatura."},
            {"table": "tse-2022-election-powerbi-candidates.csv", "field": "candidate_total_status_code", "type": "text", "definition": "Código oficial do resultado total; somente 2, 3, 4 ou 5 no recorte."},
            {"table": "tse-2022-election-powerbi-candidates.csv", "field": "expense_deduplicated_centavos", "type": "integer", "definition": "Despesa Final deduplicada em centavos; base das faixas e da análise principal."},
            {"table": "tse-2022-election-powerbi-candidates.csv", "field": "expense_all_lines_centavos", "type": "integer", "definition": "Despesa Final com todas as linhas em centavos; sensibilidade."},
            {"table": "tse-2022-election-powerbi-candidates.csv", "field": "expense_band_code", "type": "text", "definition": "Faixa fixa de despesa deduplicada; limites descritos em tse-2022-election-powerbi-recut.json."},
            {"table": "tse-2022-election-powerbi-candidates.csv", "field": "expense_band_label", "type": "text", "definition": "Rótulo legível da faixa fixa de despesa."},
            {"table": "tse-2022-election-powerbi-candidates.csv", "field": "elected", "type": "integer", "definition": "Indicador: 1 para código 2 ou 3; 0 para código 4 ou 5."},
            {"table": "tse-2022-election-powerbi-summary.csv", "field": "geography_type", "type": "text", "definition": "Nível geográfico: BRASIL ou UF."},
            {"table": "tse-2022-election-powerbi-summary.csv", "field": "geography_code", "type": "text", "definition": "BR para Brasil; sigla da UF para nível estadual."},
            {"table": "tse-2022-election-powerbi-summary.csv", "field": "candidate_count", "type": "integer", "definition": "Denominador: candidaturas classificáveis no recorte e faixa."},
            {"table": "tse-2022-election-powerbi-summary.csv", "field": "elected_count", "type": "integer", "definition": "Numerador: eleitos pelos códigos 2 e 3 no denominador."},
            {"table": "tse-2022-election-powerbi-summary.csv", "field": "elected_share", "type": "decimal", "definition": "elected_count / candidate_count; vazio se denominador zero."},
            {"table": "tse-2022-election-powerbi-summary.csv", "field": "lower_exclusive_centavos", "type": "integer nullable", "definition": "Limite inferior estrito da faixa, em centavos; vazio na primeira faixa."},
            {"table": "tse-2022-election-powerbi-summary.csv", "field": "upper_inclusive_centavos", "type": "integer nullable", "definition": "Limite superior inclusivo da faixa, em centavos; vazio na última faixa."},
            {"table": "tse-2022-election-powerbi-summary.csv", "field": "election_year", "type": "integer", "definition": "Ano da eleição; 2022."},
            {"table": "tse-2022-election-powerbi-summary.csv", "field": "turn", "type": "integer", "definition": "Turno eleitoral; primeiro turno."},
            {"table": "tse-2022-election-powerbi-summary.csv", "field": "cargo", "type": "text", "definition": "Cargo; Deputado Federal."},
            {"table": "tse-2022-election-powerbi-summary.csv", "field": "expense_band_code", "type": "text", "definition": "Código estável da faixa fixa de despesa."},
            {"table": "tse-2022-election-powerbi-summary.csv", "field": "expense_band_label", "type": "text", "definition": "Rótulo legível da faixa fixa de despesa."},
            {"table": "tse-2022-election-powerbi-summary.csv", "field": "expense_basis", "type": "text", "definition": "Base monetária da faixa: despesa Final deduplicada."},
            {"table": "tse-2022-election-powerbi-summary.csv", "field": "denominator_definition", "type": "text", "definition": "Definição do denominador usado para a proporção."},
        ]
        official_result_counts = {
            str(code): int((frame["candidate_total_status_code"] == code).sum())
            for code in sorted(frame["candidate_total_status_code"].dropna().unique())
        }
        election_analysis = {
            "official_elected_codes": {"2": "ELEITO POR QP", "3": "ELEITO POR MÉDIA"},
            "official_not_elected_codes": {"4": "NÃO ELEITO", "5": "SUPLENTE"},
            "excluded_other_or_missing_result_codes": {
                str(code) if pd.notna(code) else "(ausente)": int(count)
                for code, count in frame["candidate_total_status_code"].value_counts(dropna=False).items()
                if code not in {"2", "3", "4", "5"}
            },
            "apto_official_result_counts_with_observed_votes": official_result_counts,
            "eligible_complete_case_n": int(len(election_frame)),
            "eligible_elected_n": int(election_frame["elected"].sum()),
            "eligible_not_elected_n": int(len(election_frame) - election_frame["elected"].sum()),
            "eligible_excluded_for_missing_expense_or_controls": int(
                frame["candidate_total_status_code"].isin({"2", "3", "4", "5"}).sum()
                - len(election_frame)
            ),
            "apto_elected_n": int(official_result_counts.get("2", 0) + official_result_counts.get("3", 0)),
            "apto_not_elected_n": int(official_result_counts.get("4", 0) + official_result_counts.get("5", 0)),
            "eligible_excluded_missing_final_expense": int(
                (frame["candidate_total_status_code"].isin({"2", "3", "4", "5"}) & frame["expense_deduplicated_centavos"].isna()).sum()
            ),
            "eligible_excluded_missing_controls": int(
                (frame["candidate_total_status_code"].isin({"2", "3", "4", "5"}) & frame[control_columns].isna().any(axis=1)).sum()
            ),
            "eligible_excluded_overlap_expense_and_controls": int(
                (frame["candidate_total_status_code"].isin({"2", "3", "4", "5"}) & frame["expense_deduplicated_centavos"].isna() & frame[control_columns].isna().any(axis=1)).sum()
            ),
            "models": election_models,
            "coefficients": election_coefficients,
            "expense_comparison": election_expense_comparison,
            "elected_share_by_uf_expense_band": election_rates_by_uf_band,
            "interpretation": "análise secundária acrescentada após os primeiros resultados; associação não causal; despesa declarada não implica recurso público",
        }
        election_analysis["fixed_expense_band_definitions"] = election_band_definitions
        election_analysis["elected_share_by_fixed_expense_band_brazil_and_uf"] = fixed_band_summary_rows
        election_analysis["powerbi_data_dictionary"] = election_powerbi_dictionary
        election_analysis["powerbi_recut"] = election_powerbi_recut
        coefficients: list[dict[str, Any]] = []
        models: list[dict[str, Any]] = []
        fitted_models: dict[str, tuple[Any, pd.DataFrame, str]] = {}
        model_specs = (
            ("deduplicado_completo", "expense_deduplicated_centavos", True, False, True),
            ("todas_as_linhas_completo", "expense_all_lines_centavos", True, False, True),
            ("deduplicado_uf_partido", "expense_deduplicated_centavos", False, False, False),
            ("deduplicado_interacao_sexo", "expense_deduplicated_centavos", True, True, True),
            ("todas_as_linhas_interacao_sexo", "expense_all_lines_centavos", True, True, True),
        )
        for name, expense_column, full_controls, interaction, include_age in model_specs:
            required_columns = [expense_column, "uf", "party_code"]
            if include_age:
                required_columns.append("age_at_election")
            if full_controls:
                required_columns.extend(["gender", "race", "schooling"])
            selected = frame.loc[frame[required_columns].notna().all(axis=1)].copy()
            selected["log1p_expense_brl"] = selected[expense_column].astype(float).div(100).map(math.log1p)
            model, estimates, fitted, fitted_frame = _fit_model(name, selected, full_controls, interaction, include_age)
            model["expense_scenario"] = "deduplicado" if "deduplicado" in name else "todas as linhas"
            models.append(model)
            coefficients.extend(estimates)
            fitted_models[name] = (fitted, fitted_frame, expense_column)
        ols_frame = model_frame.copy()
        ols_frame["log1p_expense_brl"] = ols_frame["expense_deduplicated_centavos"].astype(float).div(100).map(math.log1p)
        ols_frame["log1p_nominal_votes"] = ols_frame["valid_nominal_votes"].astype(float).map(math.log1p)
        for name, response in (
            ("deduplicado_ols_participacao", "vote_share"),
            ("deduplicado_votos_brutos_log1p", "log1p_nominal_votes"),
        ):
            model, estimates = _fit_ols_sensitivity(name, ols_frame, response)
            model["expense_scenario"] = "deduplicado"
            models.append(model)
            coefficients.extend(estimates)
        prediction_tables, model_diagnostics, calibration_rows, influence_rows = (
            _build_prediction_and_diagnostic_tables(fitted_models, model_frame)
        )
        race_analysis, race_descriptive_rows, race_coefficients, race_support_rows, race_curve_support_rows = (
            _build_race_secondary(frame, apto)
        )
        interaction_model = next(model for model in models if model["name"] == "deduplicado_interacao_sexo")
        gender_counts = model_frame["gender"].value_counts(dropna=False).to_dict()
        gender_analysis_n = int(model_frame["gender"].isin(["FEMININO", "MASCULINO"]).sum())
        expense_scenarios = {}
        for label, column in (("deduplicado", "expense_deduplicated_centavos"), ("todas_as_linhas", "expense_all_lines_centavos")):
            observed = [candidate.get(column) for candidate in candidate_rows if candidate.get(column) is not None]
            expense_scenarios[label] = {
                "total_centavos": int(sum(observed)),
                "candidates_with_final_expenses": len(observed),
                "observed_zero_candidates": sum(value == 0 for value in observed),
                "absent_candidates": len(apto) - len(observed),
            }
        expense_sensitivity_difference_centavos = (
            expense_scenarios["todas_as_linhas"]["total_centavos"]
            - expense_scenarios["deduplicado"]["total_centavos"]
        )
        payment_source = validation.get("source_details", {}).get("accounts_2022", {})
        paid_members = {
            member
            for member in payment_source.get("selected_members", []) + payment_source.get("excluded_aggregate_or_document_members", [])
            if "despesas_pagas" in member.casefold()
        }
        payment_archive_checked = False
        payment_archive_path = payment_source.get("archive")
        if payment_archive_path and Path(payment_archive_path).is_file():
            try:
                with zipfile.ZipFile(payment_archive_path) as archive:
                    paid_members = {name for name in archive.namelist() if "despesas_pagas" in name.casefold()}
                payment_archive_checked = True
            except zipfile.BadZipFile:
                payment_archive_checked = False
        paid_members = sorted(paid_members)
        vote_observed = sum(candidate["sq_candidate"] in vote_totals for candidate in apto)
        payments_integrated = bool(payment_tables)
        reconciliation = validation.get("reconciliation", {})
        nominal_by_uf = reconciliation.get("nominal_votes_by_uf", {})
        fatal_counts = validation.get("fatal_counts", {})
        pipeline_validation = {
            "status": validation.get("status"),
            "fatal_counts": fatal_counts,
            "fatal_count_total": sum(int(value) for value in fatal_counts.values()),
            "warnings": validation.get("warnings", {}),
            "expense_rows_reconciled": None
            if not reconciliation.get("expense_rows_source_vs_aggregate")
            else reconciliation["expense_rows_source_vs_aggregate"][0] == reconciliation["expense_rows_source_vs_aggregate"][1],
            "expense_amount_reconciled": None
            if not reconciliation.get("expense_centavos_source_vs_aggregate")
            else reconciliation["expense_centavos_source_vs_aggregate"][0] == reconciliation["expense_centavos_source_vs_aggregate"][1],
            "vote_rows_reconciled": None
            if not reconciliation.get("vote_rows_source_vs_aggregate")
            else reconciliation["vote_rows_source_vs_aggregate"][0] == reconciliation["vote_rows_source_vs_aggregate"][1],
            "vote_totals_reconciled": None
            if not reconciliation.get("vote_valid_votes_source_vs_aggregate")
            else reconciliation["vote_valid_votes_source_vs_aggregate"][0] == reconciliation["vote_valid_votes_source_vs_aggregate"][1],
            "nominal_votes_reconciled_by_uf": bool(nominal_by_uf)
            and all(row["party_source"] == row["candidate_source"] for row in nominal_by_uf.values()),
            "nominal_uf_count": len(nominal_by_uf),
        }
        result: dict[str, Any] = {
            "manifest_id": validation.get("manifest_id"),
            "source_metadata": source_metadata,
            "pipeline_validation": pipeline_validation,
            "population": {
                "apto_candidates": len(apto),
                "inapto_candidates": len(inapto),
                "apto_with_official_denominator_and_observed_votes": len(candidate_rows),
                "apto_without_official_denominator_or_observed_votes": len(apto) - len(candidate_rows),
                "apto_zero_nominal_votes": zero_nominal_votes_apto,
            },
            "outcome": "votos nominais válidos do candidato / total oficial de votos válidos por UF (nominais + legenda)",
            "vote_denominator_uf_count": len(vote_denominator_rows),
            "official_nominal_votes_national_total": sum(row["valid_nominal_votes"] for row in vote_denominator_rows),
            "official_legend_votes_national_total": sum(row["valid_legend_votes"] for row in vote_denominator_rows),
            "official_valid_votes_national_total": sum(row["valid_votes_total"] for row in vote_denominator_rows),
            "vote_denominators_by_uf": vote_denominator_rows,
            "expense_measure": "VR_DESPESA_CONTRATADA em prestações Final, BRL, transformação log(1 + despesa); zeros observados preservados; ausência excluída da regressão",
            "expense_scenarios": expense_scenarios,
            "expense_sensitivity_difference_centavos": expense_sensitivity_difference_centavos,
            "model_complete_case_n": len(model_frame),
            "model_complete_case_exclusions": len(apto) - len(model_frame),
            "model_exclusion_reasons": {
                "apto_without_final_expense": int(missing_final_expense.sum()),
                "apto_with_missing_controls": int(missing_controls.sum()),
                "overlap": exclusion_overlap,
            },
            "missing_controls_by_field": missing_controls_by_field,
            "gender_comparison": {
                "women_and_men_n": gender_analysis_n,
                "other_or_missing_gender_excluded_from_interaction": len(model_frame) - gender_analysis_n,
                "counts_in_main_complete_case": {str(key): int(value) for key, value in gender_counts.items()},
                "interaction_model": interaction_model["name"],
                "interpretation": "associação não causal; a inclinação pode variar entre mulheres e homens",
            },
            "prediction_tables": prediction_tables,
            "model_diagnostics": model_diagnostics,
            "calibration_deciles": calibration_rows,
            "influence_top_candidates": influence_rows,
            "models": models,
            "coefficients": coefficients,
            "secondary_election_analysis": election_analysis,
            "secondary_race_analysis": race_analysis,
            "apto_expenses_by_type": apto_rows,
            "apto_expense_survey": apto_expense_summary,
            "inapto_expenses_by_type": inapto_rows,
            "inapto_expense_survey": inapto_summary,
            "payment_integration": {
                "integrated_in_analysis_database": payments_integrated,
                "payment_related_tables": payment_tables,
                "frozen_archive_checked": payment_archive_checked,
                "frozen_archive_payment_members": paid_members,
                "status": (
                    "integrado"
                    if payments_integrated
                    else (
                        f"não integrado: {len(paid_members)} membros de despesas pagas estão no ZIP congelado; não há tabela de pagamentos na base derivada, e essa integração complementar não bloqueia a análise contratada"
                        if paid_members
                        else "não integrado; não foi identificado membro de despesas pagas no ZIP congelado; a integração complementar não bloqueia a análise contratada"
                    )
                ),
            },
            "vote_observations_for_apto": vote_observed,
            "limitations": [
                "A situação APTO é a registrada no snapshot; não prova elegibilidade jurídica na data da eleição.",
                "Despesas são valores declarados contratados, não pagamentos efetivos.",
                "Deduplicar igualdade integral nas 53 colunas originais é uma escolha metodológica; não confirma identidade econômica das repetições.",
                "Todas as linhas permanecem como sensibilidade. Diferença não significa desperdício ou irregularidade.",
                "Modelos observacionais não estimam efeito causal; qualidade do candidato, incumbência, apoio, geografia e competitividade podem confundir a associação.",
                "Votos por UF são agregados eleitorais; os resultados não descrevem decisões individuais de eleitores.",
            ],
        }
    finally:
        connection.close()

    _write_csv(
        output_dir / "tse-2022-vote-denominator-by-uf.csv",
        result["vote_denominators_by_uf"],
        ["uf", "election_year", "turn", "cargo_code", "cargo", "valid_nominal_votes", "valid_legend_votes", "valid_votes_total", "source_row_count", "source_archive", "source_member"],
    )
    _write_csv(
        output_dir / "tse-2022-financial-model-estimates.csv",
        result["coefficients"],
        ["model", "term", "coefficient", "robust_se_hc1", "ci95_low", "ci95_high", "p_value"],
    )
    _write_csv(
        output_dir / "tse-2022-predicted-expense-scenarios.csv",
        result["prediction_tables"]["scenario_comparison"],
        ["expense_level", "expense_quantile", "expense_brl", "deduplicated_prediction", "deduplicated_ci95_lower", "deduplicated_ci95_upper", "all_rows_prediction", "all_rows_ci95_lower", "all_rows_ci95_upper", "difference_percentage_points", "standardization_n"],
    )
    _write_csv(
        output_dir / "tse-2022-sex-interaction-curve.csv",
        result["prediction_tables"]["sex_interaction_curve"]["points"],
        ["expense_brl", "male_prediction", "male_ci95_lower", "male_ci95_upper", "female_prediction", "female_ci95_lower", "female_ci95_upper", "female_minus_male_percentage_points"],
    )
    _write_csv(
        output_dir / "tse-2022-model-calibration-deciles.csv",
        result["calibration_deciles"],
        ["model", "decile", "n", "mean_observed_vote_share", "mean_predicted_vote_share", "calibration_gap"],
    )
    _write_csv(
        output_dir / "tse-2022-model-influence-top-candidates.csv",
        result["influence_top_candidates"],
        ["model", "rank", "sq_candidate", "expense_brl", "observed_vote_share", "fitted_vote_share", "cooks_distance", "leverage", "dfbeta_log1p_expense"],
    )
    _write_csv(
        output_dir / "tse-2022-top-one-percent-expense-sensitivity.csv",
        result["model_diagnostics"]["top_one_percent_expense_sensitivity"],
        ["scenario", "cutoff_rule", "cutoff_brl", "excluded_candidates", "n_after_exclusion", "full_coefficient", "trimmed_coefficient", "trimmed_ci95_lower", "trimmed_ci95_upper", "coefficient_change", "full_ci95_lower", "full_ci95_upper"],
    )
    _write_csv(
        output_dir / "tse-2022-election-expense-comparison.csv",
        election_analysis["expense_comparison"],
        ["outcome", "scenario", "candidate_count", "expense_mean_brl", "expense_median_brl", "cost_per_vote_n_positive_votes", "cost_per_vote_excluded_zero_votes", "cost_per_vote_mean_brl", "cost_per_vote_median_brl"],
    )
    _write_csv(
        output_dir / "tse-2022-election-expense-models.csv",
        election_analysis["coefficients"],
        ["model", "term", "coefficient", "robust_se_hc1", "ci95_low", "ci95_high", "p_value"],
    )
    _write_csv(
        output_dir / "tse-2022-election-rate-by-uf-expense-band.csv",
        election_analysis["elected_share_by_uf_expense_band"],
        ["uf", "expense_band_within_uf", "candidate_count", "elected_count", "elected_share", "expense_basis"],
    )
    _write_csv(
        output_dir / "tse-2022-election-powerbi-candidates.csv",
        fixed_band_candidate_rows,
        [
            "election_year", "turn", "cargo", "sq_candidate", "uf",
            "candidate_total_status_code", "expense_deduplicated_centavos",
            "expense_all_lines_centavos", "expense_band_code", "expense_band_label", "elected",
        ],
    )
    _write_csv(
        output_dir / "tse-2022-election-powerbi-summary.csv",
        election_analysis["elected_share_by_fixed_expense_band_brazil_and_uf"],
        [
            "election_year", "turn", "cargo", "geography_type", "geography_code",
            "expense_band_code", "expense_band_label", "lower_exclusive_centavos",
            "upper_inclusive_centavos", "candidate_count", "elected_count", "elected_share",
            "denominator_definition", "expense_basis",
        ],
    )
    _write_csv(
        output_dir / "tse-2022-election-powerbi-dictionary.csv",
        election_analysis["powerbi_data_dictionary"],
        ["table", "field", "type", "definition"],
    )
    (output_dir / "tse-2022-election-powerbi-recut.json").write_text(
        json.dumps(election_analysis["powerbi_recut"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    _write_csv(
        output_dir / "tse-2022-race-population-counts.csv",
        [
            {
                "race_category": category,
                "candidate_count": count,
                "comparison_group": (
                    "brancas" if category == "BRANCA"
                    else "pretas_pardas" if category in {"PRETA", "PARDA"}
                    else "fora_da_comparacao"
                ),
            }
            for category, count in race_analysis["population"]["race_category_counts"].items()
        ],
        ["race_category", "candidate_count", "comparison_group"],
    )
    _write_csv(
        output_dir / "tse-2022-race-group-descriptives.csv",
        race_descriptive_rows,
        [
            "scenario", "race_group", "race_group_label", "candidate_count", "expense_observed_n",
            "expense_median_brl", "expense_q25_brl", "expense_q75_brl",
            "nominal_votes_observed_n", "nominal_votes_median", "nominal_votes_q25",
            "nominal_votes_q75", "vote_share_observed_n", "vote_share_median_pct",
            "vote_share_q25_pct", "vote_share_q75_pct", "elected_count",
            "not_elected_count", "election_classified_n", "unclassified_result_n",
            "elected_proportion", "election_denominator_definition",
        ],
    )
    _write_csv(
        output_dir / "tse-2022-race-interaction-coefficients.csv",
        race_coefficients,
        ["model", "term", "coefficient", "robust_se_hc1", "ci95_low", "ci95_high", "p_value"],
    )
    _write_csv(
        output_dir / "tse-2022-race-support-by-uf-party.csv",
        race_support_rows,
        [
            "scenario", "dimension", "stratum", "brancas_n", "pretas_pardas_n",
            "brancas_p10_brl", "brancas_p90_brl", "pretas_pardas_p10_brl",
            "pretas_pardas_p90_brl", "common_p10_p90_lower_brl",
            "common_p10_p90_upper_brl", "eligible_uf_party_cell",
            "brancas_share_of_group_in_stratum", "pretas_pardas_share_of_group_in_stratum",
        ],
    )
    race_curve_points = [
        point
        for curve in race_analysis["curves"].values()
        for point in curve["points"]
    ]
    _write_csv(
        output_dir / "tse-2022-race-interaction-curve.csv",
        race_curve_points,
        [
            "scenario", "expense_brl", "brancas_supported_n", "pretas_pardas_supported_n",
            "brancas_coverage", "pretas_pardas_coverage", "supported_uf_party_cells_n",
            "supported_uf_party_strata", "standardization_n", "published", "brancas_prediction", "brancas_ci95_lower",
            "brancas_ci95_upper", "pretas_pardas_prediction", "pretas_pardas_ci95_lower",
            "pretas_pardas_ci95_upper", "difference_pretas_pardas_minus_brancas_pp",
        ],
    )
    race_curve_support_csv_rows = [
        {
            **row,
            "supported_uf_party_strata": "; ".join(row["supported_uf_party_strata"]),
        }
        for row in race_curve_support_rows
    ]
    _write_csv(
        output_dir / "tse-2022-race-curve-support.csv",
        race_curve_support_csv_rows,
        [
            "scenario", "expense_brl", "brancas_supported_n", "pretas_pardas_supported_n",
            "brancas_coverage", "pretas_pardas_coverage", "supported_uf_party_cells_n",
            "standardization_n", "published", "supported_uf_party_strata",
        ],
    )
    for scenario, curve in race_analysis["curves"].items():
        suffix = "deduplicado" if scenario == "deduplicado" else "todas-as-linhas"
        (output_dir / f"tse-2022-race-interaction-curve-{suffix}.svg").write_text(
            _race_curve_svg(curve),
            encoding="utf-8",
        )
    submission_fields = [
        "tp_prestacao_contas", "candidate_status_code", "candidate_count",
        "candidates_with_rows", "candidates_without_rows", "candidates_with_zero_total",
        "all_lines_occurrence_rows", "all_lines_zero_amount_rows",
        "all_lines_declared_expense_centavos", "deduplicated_occurrence_rows",
        "deduplicated_candidates_with_rows", "deduplicated_declared_expense_centavos",
        "excluded_occurrence_rows", "excluded_amount_centavos",
        "excluded_affected_candidates",
    ]
    _write_csv(output_dir / "tse-2022-apto-expenses-by-type.csv", apto_rows, submission_fields)
    _write_csv(output_dir / "tse-2022-inapto-expenses-by-type.csv", inapto_rows, submission_fields)
    (output_dir / "tse-2022-financial-analysis.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    main_expense_estimate = next(
        estimate for estimate in result["coefficients"]
        if estimate["model"] == "deduplicado_completo" and estimate["term"] == "log1p_expense_brl"
    )
    all_rows_expense_estimate = next(
        estimate for estimate in result["coefficients"]
        if estimate["model"] == "todas_as_linhas_completo" and estimate["term"] == "log1p_expense_brl"
    )
    reduced_expense_estimate = next(
        estimate for estimate in result["coefficients"]
        if estimate["model"] == "deduplicado_uf_partido" and estimate["term"] == "log1p_expense_brl"
    )
    reduced_model_n = next(model["n"] for model in models if model["name"] == "deduplicado_uf_partido")
    female_slope_difference = next(
        estimate for estimate in result["coefficients"]
        if estimate["model"] == "deduplicado_interacao_sexo" and estimate["term"] == "expense_x_female"
    )
    missing_control_summary = ", ".join(
        f"{column}={_pt_int(count)}"
        for column, count in missing_controls_by_field.items()
        if count
    ) or "nenhum"
    report_lines = [
        "# Análise financeira TSE 2022 — deputado federal, 1º turno",
        "",
        f"Versão de dados: `{result['manifest_id']}`.",
        "",
        "## Escopo e método",
        "",
        f"População: {_pt_int(len(apto))} candidaturas APTO no snapshot; {_pt_int(len(inapto))} candidaturas INAPTO levantadas separadamente. A situação do snapshot não é uma conclusão jurídica sobre a data da eleição.",
        f"Desfecho: {result['outcome']}. O denominador oficial foi reconciliado antes dos filtros de situação e tipo de prestação.",
        f"Exposição: {result['expense_measure']}. Principal: despesas deduplicadas; sensibilidade: todas as linhas. A regra compara os 53 campos TSE no mesmo snapshot e membro, excluindo auditoria; não prova identidade econômica.",
        f"Denominador oficial: {_pt_int(result['official_valid_votes_national_total'])} votos válidos — {_pt_int(result['official_nominal_votes_national_total'])} nominais + {_pt_int(result['official_legend_votes_national_total'])} de legenda — nas 27 UFs. Origem congelada: `{result['source_metadata']['official_source_url'] or 'fonte registrada no manifesto'}`, ZIP `{result['source_metadata']['frozen_zip'] or 'manifesto'}`, SHA-256 `{result['source_metadata']['sha256'] or 'manifesto'}`, {_pt_int(result['source_metadata']['size_bytes']) if result['source_metadata']['size_bytes'] else 'tamanho registrado no manifesto'} bytes.",
        "Escopo da fonte: deputado federal, primeiro turno de 2022; votos nominais e de legenda incluídos.",
        f"Cobertura de votos em APTO: {_pt_int(result['population']['apto_with_official_denominator_and_observed_votes'])}/{_pt_int(result['population']['apto_candidates'])} com denominador e votos observados; {_pt_int(result['population']['apto_without_official_denominator_or_observed_votes'])} sem cobertura; {_pt_int(result['population']['apto_zero_nominal_votes'])} com zero voto nominal.",
        f"Validação do pipeline: {result['pipeline_validation']['status']}; {_pt_int(result['pipeline_validation']['fatal_count_total'])} contagens fatais. Reconciliações de linhas/valores de despesas e votos: {'/'.join(_pt_bool(result['pipeline_validation'][key]) for key in ('expense_rows_reconciled', 'expense_amount_reconciled', 'vote_rows_reconciled', 'vote_totals_reconciled'))}; votos nominais coincidem por UF: {_pt_bool(result['pipeline_validation']['nominal_votes_reconciled_by_uf'])} ({_pt_int(result['pipeline_validation']['nominal_uf_count'])} UFs).",
        "Modelo principal: GLM binomial/logit para participação fracionária, com erros-padrão robustos HC1. Modelo completo ajusta UF, partido, idade, sexo, raça e escolaridade; comparação reduzida ajusta UF e partido. Não se combina partido e federação.",
        "A análise é associação, não causalidade; confundimento por qualidade do candidato, incumbência, apoio partidário, geografia e competitividade permanece possível. Sexo não feminino/masculino e ausência de sexo ficam fora apenas da interação; o modelo completo mantém categorias informadas.",
        "",
        "## Cobertura, zeros e totais de despesas Final entre APTO",
        "",
        "| Cenário | Total declarado (R$) | Candidatos com despesa Final | Total observado zero | Sem linha Final |",
        "|---|---:|---:|---:|---:|",
    ]
    for label, key in (("Deduplicado (principal)", "deduplicado"), ("Todas as linhas (sensibilidade)", "todas_as_linhas")):
        value = expense_scenarios[key]
        report_lines.append(
            f"| {label} | {_pt_brl_centavos(value['total_centavos'])} | {_pt_int(value['candidates_with_final_expenses'])} | {_pt_int(value['observed_zero_candidates'])} | {_pt_int(value['absent_candidates'])} |"
        )
    report_lines.extend([
        "",
        "## Demais tipos de prestação entre APTO",
        "",
        "Os outros tipos são apresentados separados de `Final`; o critério não infere qual entrega foi recebida por último.",
        "",
        "| Tipo | Candidatos com linha | Sem linha | Linhas todas | Total todas (R$) | Linhas deduplicadas | Total deduplicado (R$) | Linhas excluídas | Candidatos afetados |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for row in apto_rows:
        report_lines.append(
            f"| {row['tp_prestacao_contas']} | {_pt_int(row['candidates_with_rows'])} | {_pt_int(row['candidates_without_rows'])} | {_pt_int(row['all_lines_occurrence_rows'])} | {_pt_brl_centavos(row['all_lines_declared_expense_centavos'])} | {_pt_int(row['deduplicated_occurrence_rows'])} | {_pt_brl_centavos(row['deduplicated_declared_expense_centavos'])} | {_pt_int(row['excluded_occurrence_rows'])} | {_pt_int(row['excluded_affected_candidates'])} |"
        )
    report_lines.extend([
        "",
        f"Modelos completos, interações e sensibilidades OLS usam {_pt_int(len(model_frame))} candidaturas com despesas Final, votos e controles completos; {_pt_int(len(apto) - len(model_frame))} APTO ficam fora desses modelos: {_pt_int(int(missing_final_expense.sum()))} sem linha Final, {_pt_int(int(missing_controls.sum()))} com algum controle ausente (sobreposição {_pt_int(exclusion_overlap)}; campos: {missing_control_summary}). Zero de despesa e {_pt_int(zero_nominal_votes_apto)} votos nominais iguais a zero são mantidos; ausência de linha não vira zero.",
        f"O modelo de comparação com ajuste apenas por UF/partido, sem idade, usa N={_pt_int(next(model['n'] for model in models if model['name'] == 'deduplicado_uf_partido'))}.",
        f"Entre APTO, preservar todas as ocorrências soma R$ {_pt_brl_centavos(expense_scenarios['todas_as_linhas']['total_centavos'])}; a base principal deduplicada soma R$ {_pt_brl_centavos(expense_scenarios['deduplicado']['total_centavos'])}. Diferença: R$ {_pt_brl_centavos(expense_sensitivity_difference_centavos)}; não é classificação de gasto indevido.",
        "",
        "## Modelos estimados",
        "",
        "| Modelo | N | Família | Desfecho | Controles |",
        "|---|---:|---|---|---|",
    ])
    for model in models:
        report_lines.append(f"| {model['name']} | {_pt_int(model['n'])} | {model['family']} | {model.get('outcome', 'participação de votos fracionária')} | {', '.join(model['controls'])}{'; interação despesa×mulher' if model['interaction'] else ''} |")
    report_lines.append(
        f"Diagnósticos: {_pt_int(sum(bool(model['converged']) for model in models))}/{_pt_int(len(models))} convergiram e todas as matrizes passaram a verificação de posto. Adequação, calibração e influência estão detalhadas abaixo; não há validação externa."
    )
    report_lines.extend([
        "",
        f"Na amostra completa, {_pt_int(gender_analysis_n)} candidaturas com sexo informado como feminino/masculino entram na interação; {_pt_int(len(model_frame) - gender_analysis_n)} com outra categoria/ausente ficam fora apenas dessa comparação.",
        f"No GLM completo, o coeficiente de `log1p(despesa)` foi {_pt_decimal(main_expense_estimate['coefficient'], 3)} (IC 95% HC1 {_pt_decimal(main_expense_estimate['ci95_low'], 3)} a {_pt_decimal(main_expense_estimate['ci95_high'], 3)}) no cenário deduplicado e {_pt_decimal(all_rows_expense_estimate['coefficient'], 3)} ({_pt_decimal(all_rows_expense_estimate['ci95_low'], 3)} a {_pt_decimal(all_rows_expense_estimate['ci95_high'], 3)}) com todas as linhas. Ambos indicam associação positiva ajustada na escala logit; isso não demonstra que mais despesa cause mais votos.",
        f"Com ajuste somente por UF/partido, sem idade (N={_pt_int(reduced_model_n)}), o coeficiente de `log1p(despesa)` foi {_pt_decimal(reduced_expense_estimate['coefficient'], 3)} (IC 95% HC1 {_pt_decimal(reduced_expense_estimate['ci95_low'], 3)} a {_pt_decimal(reduced_expense_estimate['ci95_high'], 3)}).",
        f"Na interação planejada, a diferença de inclinação mulheres–homens foi {_pt_decimal(female_slope_difference['coefficient'], 3)} na escala logit (IC 95% HC1 {_pt_decimal(female_slope_difference['ci95_low'], 3)} a {_pt_decimal(female_slope_difference['ci95_high'], 3)}). É uma diferença associativa, não causal.",
        "Consulte `tse-2022-financial-model-estimates.csv` para todos os coeficientes e valores-p. GLM está em escala logit; OLS está em escala linear do desfecho informado. As estimativas são associativas, não causais.",
        "",
    ])
    report_lines.extend([
        "",
        "## Participação prevista em níveis comparáveis de despesa",
        "",
        "As previsões são médias padronizadas: fixa-se a despesa no nível indicado e calcula-se a participação de votos prevista para cada candidatura da distribuição comum de controles completos, depois se tira a média. São associações ajustadas, não previsões causais nem resultados eleitorais individuais. ICs de 95% pontuais pelo método delta, usando a covariância sanduíche HC1; não são intervalos para candidaturas individuais. A diferença entre cenários é apresentada em pontos percentuais como diferença de estimativas pontuais, sem IC próprio.",
        "",
        "| Despesa contratada | Deduplicado: participação prevista (IC 95%) | Todas as linhas: participação prevista (IC 95%) | Diferença todas − deduplicado (p.p.) |",
        "|---|---:|---:|---:|",
    ])
    for row in prediction_tables["scenario_comparison"]:
        expense = f"R$ {_pt_decimal(row['expense_brl'], 2)} ({row['expense_level']})"
        dedup = f"{_pt_decimal(row['deduplicated_prediction'] * 100, 4)}% ({_pt_decimal(row['deduplicated_ci95_lower'] * 100, 4)}–{_pt_decimal(row['deduplicated_ci95_upper'] * 100, 4)}%)"
        all_lines = f"{_pt_decimal(row['all_rows_prediction'] * 100, 4)}% ({_pt_decimal(row['all_rows_ci95_lower'] * 100, 4)}–{_pt_decimal(row['all_rows_ci95_upper'] * 100, 4)}%)"
        report_lines.append(
            f"| {expense} | {dedup} | {all_lines} | {_pt_decimal(row['difference_percentage_points'], 5)} |"
        )
    curve = prediction_tables["sex_interaction_curve"]
    support = curve["common_support"]
    report_lines.extend([
        "",
        "## Comparação mulheres–homens dentro do suporte comum",
        "",
        f"A curva usa apenas despesas dentro da interseção das faixas P5–P95 dos dois grupos: R$ {_pt_decimal(support['lower_brl'], 2)} a R$ {_pt_decimal(support['upper_brl'], 2)}. Em cada nível, fixa-se a despesa e alterna-se o sexo na mesma distribuição de controles; os ICs de 95% são pontuais e pelo método delta/HC1.",
        "Na codificação, homens são a referência (indicador `female=0`); `log1p(despesa)` é a inclinação associativa masculina e `expense_x_female` acrescenta a diferença de inclinação para mulheres na escala logit. A inclinação feminina é a soma dos dois coeficientes. Como o logit inverso é não linear, o coeficiente de interação não equivale a uma porcentagem de gasto necessária; compare as curvas previstas.",
        "",
        "| Despesa (R$) | Homens: participação prevista (IC 95%) | Mulheres: participação prevista (IC 95%) | Diferença mulheres − homens (p.p.) |",
        "|---:|---:|---:|---:|",
    ])
    for row in curve["points"]:
        male = f"{_pt_decimal(row['male_prediction'] * 100, 2)}% ({_pt_decimal(row['male_ci95_lower'] * 100, 2)}–{_pt_decimal(row['male_ci95_upper'] * 100, 2)}%)"
        female = f"{_pt_decimal(row['female_prediction'] * 100, 2)}% ({_pt_decimal(row['female_ci95_lower'] * 100, 2)}–{_pt_decimal(row['female_ci95_upper'] * 100, 2)}%)"
        report_lines.append(
            f"| {_pt_decimal(row['expense_brl'], 2)} | {male} | {female} | {_pt_decimal(row['female_minus_male_percentage_points'], 2)} |"
        )
    report_lines.extend([
        "",
        "## Adequação do ajuste e influência",
        "",
        "RMSE e MAE medem o erro médio entre participação observada e ajustada, em pontos percentuais; a calibração agrupa as previsões em decis e compara médias observadas e previstas. São verificações dentro da própria amostra, não validação fora da amostra. Influência: distância de Cook, alavancagem e DFBETA do coeficiente de despesa. O limite Cook > 4/N é apenas uma triagem heurística; nenhum caso foi excluído automaticamente.",
        "",
        "| Cenário | RMSE (p.p.) | MAE (p.p.) | Maior diferença de calibração por decil (p.p.) | Cook > 4/N | Maior Cook | Maior alavancagem | Maior valor absoluto de DFBETA da despesa |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for model_name in ("deduplicado_completo", "todas_as_linhas_completo"):
        diagnostic = model_diagnostics[model_name]
        fit = diagnostic["fit"]
        influence = diagnostic["influence"]
        max_dfbeta = influence["maximum_absolute_expense_dfbeta"]
        report_lines.append(
            f"| {model_name} | {_pt_decimal(fit['rmse'] * 100, 2)} | {_pt_decimal(fit['mae'] * 100, 2)} | {_pt_decimal(fit['max_absolute_decile_calibration_gap'] * 100, 2)} | {_pt_int(influence['candidates_above_cook_screen'])} (limite {_pt_decimal(influence['cook_distance_screen_threshold'], 4)}) | {_pt_decimal(influence['maximum_cook_distance'], 4)} | {_pt_decimal(influence['maximum_leverage'], 4)} | {_pt_decimal(max_dfbeta, 4)} |"
        )
    report_lines.extend([
        "",
        "A sensibilidade abaixo remove somente candidaturas acima do P99 da despesa deduplicada, para verificar a estabilidade da inclinação de despesa. A amostra principal permanece intacta; a regra não identifica erro nem gasto indevido. As listas de calibração por decil e os 10 casos de maior Cook por cenário estão nos CSVs de diagnóstico.",
        "",
        "| Cenário | Corte P99 (R$) | Excluídos na sensibilidade | N após corte | Coeficiente principal | Coeficiente sem cauda (IC 95% HC1) | Mudança |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ])
    for row in model_diagnostics["top_one_percent_expense_sensitivity"]:
        trimmed_ci = f"{_pt_decimal(row['trimmed_coefficient'], 3)} ({_pt_decimal(row['trimmed_ci95_lower'], 3)}–{_pt_decimal(row['trimmed_ci95_upper'], 3)})"
        report_lines.append(
            f"| {row['scenario']} | {_pt_decimal(row['cutoff_brl'], 2)} | {_pt_int(row['excluded_candidates'])} | {_pt_int(row['n_after_exclusion'])} | {_pt_decimal(row['full_coefficient'], 3)} | {trimmed_ci} | {_pt_decimal(row['coefficient_change'], 3)} |"
        )
    report_lines.extend([
        "",
        "Arquivos: `tse-2022-predicted-expense-scenarios.csv`, `tse-2022-sex-interaction-curve.csv`, `tse-2022-model-calibration-deciles.csv`, `tse-2022-model-influence-top-candidates.csv` e `tse-2022-top-one-percent-expense-sensitivity.csv`. As curvas mostram médias previstas ajustadas; toda interpretação é associativa.",
        "",
    ])
    secondary = election_analysis
    report_lines.extend([
        "",
        "## Análise secundária acrescentada após os primeiros resultados: despesas e eleição",
        "",
        "Esta análise secundária não substitui a análise principal de participação de votos. Eleito é definido pelos códigos oficiais 2 (ELEITO POR QP) e 3 (ELEITO POR MÉDIA); códigos 4 (NÃO ELEITO) e 5 (SUPLENTE) são não eleitos. Códigos ausentes, nulos ou outros não são forçados a nenhuma classe.",
        f"No recorte APTO com votos observados, {_pt_int(secondary['apto_elected_n'])} candidaturas têm código oficial eleito e {_pt_int(secondary['apto_not_elected_n'])} têm código não eleito; {_pt_int(sum(secondary['excluded_other_or_missing_result_codes'].values()))} têm código ausente/outro. A amostra completa usada nos modelos contém {_pt_int(secondary['eligible_elected_n'])} eleitos e {_pt_int(secondary['eligible_not_elected_n'])} não eleitos ({_pt_int(secondary['eligible_complete_case_n'])} candidaturas).",
        f"Foram excluídas da amostra completa de eleição {_pt_int(secondary['eligible_excluded_for_missing_expense_or_controls'])} candidaturas com código oficial classificável por falta de despesa Final ou controle ({_pt_int(secondary['eligible_excluded_missing_final_expense'])} sem despesa Final; {_pt_int(secondary['eligible_excluded_missing_controls'])} com controle ausente; sobreposição: {_pt_int(secondary['eligible_excluded_overlap_expense_and_controls'])}); contagens de resultados no universo APTO com votos observados: {', '.join(f'código {code}: {_pt_int(count)}' for code, count in sorted(secondary['apto_official_result_counts_with_observed_votes'].items()))}. Códigos fora da classificação: {', '.join(f'{code}: {_pt_int(count)}' for code, count in sorted(secondary['excluded_other_or_missing_result_codes'].items())) or 'nenhum'}.",
        "Comparação descritiva usa apenas as observações completas com resultado classificável; custo por voto é despesa declarada dividida por votos nominais, portanto fica indefinido para voto zero e não entra como preditor. A tabela mostra deduplicado e todas as linhas.",
        "",
        "| Resultado | Base | N | Despesa média (R$) | Despesa mediana (R$) | N com votos positivos | N com custo indefinido por voto zero | Custo médio por voto (R$) | Custo mediano por voto (R$) |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for row in secondary["expense_comparison"]:
        report_lines.append(
            f"| {row['outcome']} | {row['scenario']} | {_pt_int(row['candidate_count'])} | {_pt_decimal(row['expense_mean_brl'])} | {_pt_decimal(row['expense_median_brl'])} | {_pt_int(row['cost_per_vote_n_positive_votes'])} | {_pt_int(row['cost_per_vote_excluded_zero_votes'])} | {_pt_decimal(row['cost_per_vote_mean_brl']) if row['cost_per_vote_mean_brl'] is not None else 'n/a'} | {_pt_decimal(row['cost_per_vote_median_brl']) if row['cost_per_vote_median_brl'] is not None else 'n/a'} |"
        )
    report_lines.extend([
        "",
        "Modelos logísticos binários: log(1 + despesa contratada) com controles acordados — UF, partido, idade na eleição, sexo, raça e escolaridade — e erros-padrão HC1. Números abaixo são OR por unidade de log(1 + R$), não por real; votos/custo por voto não entram no modelo.",
        "",
        "| Cenário | N | Eleitos | Não eleitos | OR da despesa | IC 95% | p |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ])
    for row in secondary["models"]:
        p_value_display = "<0,0001" if row["p_value"] < 0.0001 else _pt_decimal(row["p_value"], 4)
        report_lines.append(
            f"| {row['name']} | {_pt_int(row['n'])} | {_pt_int(row['elected_n'])} | {_pt_int(row['not_elected_n'])} | {_pt_decimal(row['odds_ratio_per_log_unit'], 3)} | {_pt_decimal(row['odds_ratio_ci95_lower'], 3)}–{_pt_decimal(row['odds_ratio_ci95_upper'], 3)} | {p_value_display} |"
        )
    report_lines.extend([
        "",
        "Proporção eleita por quartil de despesa deduplicada dentro de cada UF; empates recebem ordem determinística por classificação sequencial. CSV traz contagens por faixa/UF. A associação é observacional, não causal. Despesas são declaradas contratadas e não são necessariamente recursos públicos.",
        "",
        "| UF | Faixa de despesa dentro da UF | Candidaturas | Eleitos | Proporção eleita |",
        "|---|---:|---:|---:|---:|",
    ])
    for row in secondary["elected_share_by_uf_expense_band"]:
        report_lines.append(
            f"| {row['uf']} | Q{row['expense_band_within_uf']} | {_pt_int(row['candidate_count'])} | {_pt_int(row['elected_count'])} | {_pt_decimal(row['elected_share'] * 100)}% |"
        )
    report_lines.extend([
        "",
        "Artefatos: `tse-2022-election-expense-comparison.csv`, `tse-2022-election-expense-models.csv` e `tse-2022-election-rate-by-uf-expense-band.csv`.",
        "",
    ])
    race_population = race_analysis["population"]
    race_category_summary = ", ".join(
        f"{category}: {_pt_int(count)}"
        for category, count in race_population["race_category_counts"].items()
    )
    race_outside_summary = ", ".join(
        f"{category}: {_pt_int(count)}"
        for category, count in race_population["outside_comparison_counts"].items()
    ) or "nenhuma categoria fora do recorte"
    race_election_comparison = race_analysis["election_adjusted_comparison"]
    race_estimates = {
        scenario: next(
            row for row in race_coefficients
            if row["model"] == model_name and row["term"] == "expense_x_black_brown"
        )
        for scenario, model_name in (
            ("deduplicado", "raca_deduplicado"),
            ("todas_as_linhas", "raca_todas_as_linhas"),
        )
    }
    report_lines.extend([
        "",
        "## Análise secundária acrescentada após os primeiros resultados: raça/cor",
        "",
        "A análise principal de votos permanece inalterada; raça/cor já era um controle categórico nela, mas isso não testa se a associação entre despesa e votação varia entre grupos. Esta análise binária adicional compara autodeclarações `BRANCA` com `PRETA`+`PARDA`. As demais categorias permanecem na base principal e são excluídas apenas desta comparação.",
        f"Entre as {_pt_int(race_population['apto_candidates_n'])} candidaturas APTO estão {_pt_int(race_population['apto_with_votes_n'])} com votos observados. As categorias autodeclaradas, contadas antes da restrição por votos, são: {race_category_summary}. A comparação considera {_pt_int(race_analysis['comparison_binary_apto_n'])} candidaturas BRANCA/PRETA/PARDA: brancas {_pt_int(race_population['comparison_group_counts']['brancas'])}, pretas+pardas {_pt_int(race_population['comparison_group_counts']['pretas_pardas'])}. Fora dela, sem recodificação: {race_outside_summary}.",
        f"Das candidaturas binárias APTO, {_pt_int(race_analysis['comparison_binary_population_n'])} têm voto/denominador observado; {_pt_int(race_analysis['comparison_exclusions']['missing_vote_or_denominator_n'])} foram excluídas por ausência de voto/denominador. A coorte completa pareada nas duas medidas de despesa e controles tem N={_pt_int(race_analysis['comparison_complete_case_n'])}: brancas {_pt_int(race_analysis['comparison_complete_case_group_counts']['brancas'])}, pretas+pardas {_pt_int(race_analysis['comparison_complete_case_group_counts']['pretas_pardas'])}. Das observadas, {_pt_int(race_analysis['comparison_exclusions']['missing_either_expense_n'])} não tinham uma das despesas Final e {_pt_int(race_analysis['comparison_exclusions']['missing_controls_n'])} tinham controle ausente; sobreposição {_pt_int(race_analysis['comparison_exclusions']['overlap_missing_expense_and_controls_n'])}.",
        "A tabela descritiva usa essa mesma coorte em ambos os cenários. Medianas e intervalos interquartis resumem despesa contratada, votos nominais e participação nos votos válidos da UF. A proporção eleita tem como denominador somente resultados classificáveis (códigos 2, 3, 4 ou 5); ausentes/outros resultados aparecem à parte.",
        "",
        "| Grupo | Despesa Final | N | Despesa mediana (Q25–Q75, R$) | Votos nominais mediana (Q25–Q75) | Votos válidos da UF: mediana (Q25–Q75) | Eleitos / classificáveis | Proporção eleita | Resultado ausente/outro |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for row in race_descriptive_rows:
        expense_summary = (
            f"{_pt_decimal(row['expense_median_brl'])} "
            f"({_pt_decimal(row['expense_q25_brl'])}–{_pt_decimal(row['expense_q75_brl'])})"
        )
        vote_summary = (
            f"{_pt_int(round(row['nominal_votes_median']))} "
            f"({_pt_int(round(row['nominal_votes_q25']))}–{_pt_int(round(row['nominal_votes_q75']))})"
        )
        share_summary = (
            f"{_pt_decimal(row['vote_share_median_pct'], 4)}% "
            f"({_pt_decimal(row['vote_share_q25_pct'], 4)}–{_pt_decimal(row['vote_share_q75_pct'], 4)}%)"
        )
        elected_share = (
            f"{_pt_decimal(row['elected_proportion'] * 100)}%"
            if row["elected_proportion"] is not None else "n/a"
        )
        report_lines.append(
            f"| {row['race_group_label']} | {row['scenario']} | {_pt_int(row['candidate_count'])} | {expense_summary} | {vote_summary} | {share_summary} | {_pt_int(row['elected_count'])}/{_pt_int(row['election_classified_n'])} | {elected_share} | {_pt_int(row['unclassified_result_n'])} |"
        )
    election_group_counts = race_election_comparison["group_counts"]
    election_counts = race_election_comparison["elected_counts"]
    election_proportions = race_election_comparison["observed_proportions"]
    election_support = race_election_comparison["support"]
    report_lines.extend([
        "",
        "### Comparação ajustada de eleição por raça/cor",
        f"Na população comum classificável (N={_pt_int(race_election_comparison['common_population_n'])}), as taxas observadas foram {_pt_int(election_counts['brancas'])}/{_pt_int(election_group_counts['brancas'])} ({_pt_decimal(election_proportions['brancas'] * 100, 2)}%) entre brancas e {_pt_int(election_counts['pretas_pardas'])}/{_pt_int(election_group_counts['pretas_pardas'])} ({_pt_decimal(election_proportions['pretas_pardas'] * 100, 2)}%) entre pretas+pardas; diferença bruta: {_pt_decimal(race_election_comparison['observed_difference_pretas_pardas_minus_brancas_pp'], 2)} pontos percentuais.",
        "As especificações comparáveis usam os mesmos perfis: primeiro ajuste por UF, partido, idade, sexo e escolaridade; depois acrescenta-se a despesa Final deduplicada (principal) ou todas as linhas (sensibilidade). Quando o gate passa, ambas as especificações ficam restritas à mesma população nas células com suporte.",
    ])
    adjusted_election_estimates = race_election_comparison["adjusted_estimates"]
    if adjusted_election_estimates:
        report_lines.extend([
            "",
            "| Especificação | N comum | Brancas: probabilidade eleita ajustada (IC 95%) | Pretas+pardas: probabilidade eleita ajustada (IC 95%) | Diferença pretas+pardas − brancas (p.p.; IC 95%) |",
            "|---|---:|---:|---:|---:|",
        ])
        specification_labels = {
            "controls_only": "Controles, sem despesa",
            "controls_plus_deduplicated_expense": "Controles + despesa deduplicada",
            "controls_plus_all_lines_expense": "Controles + todas as linhas",
        }
        for estimate in adjusted_election_estimates:
            white = estimate["brancas"]
            black_brown = estimate["pretas_pardas"]
            report_lines.append(
                f"| {specification_labels[estimate['model']]} | {_pt_int(estimate['population_n'])} | "
                f"{_pt_decimal(white['prediction'] * 100, 2)}% ({_pt_decimal(white['ci95_lower'] * 100, 2)}–{_pt_decimal(white['ci95_upper'] * 100, 2)}%) | "
                f"{_pt_decimal(black_brown['prediction'] * 100, 2)}% ({_pt_decimal(black_brown['ci95_lower'] * 100, 2)}–{_pt_decimal(black_brown['ci95_upper'] * 100, 2)}%) | "
                f"{_pt_decimal(estimate['difference_pretas_pardas_minus_brancas_pp'], 2)} ({_pt_decimal(estimate['difference_ci95_lower_pp'], 2)}–{_pt_decimal(estimate['difference_ci95_upper_pp'], 2)}) |"
            )
        report_lines.append(
            "As probabilidades são médias padronizadas sobre os mesmos perfis; ICs pontuais de 95% por método delta/HC1. A mudança ao acrescentar despesas é associativa, não explica causalmente a diferença nem prova discriminação."
        )
    else:
        if not election_support["common_support_sufficient"]:
            reason = (
                f"somente {_pt_int(election_support['eligible_uf_party_cells_n'])} células UF×partido têm ao menos 10 candidaturas de cada grupo; "
                f"cobrem {_pt_decimal(election_support['coverage_by_group']['brancas'] * 100, 1)}% das brancas e "
                f"{_pt_decimal(election_support['coverage_by_group']['pretas_pardas'] * 100, 1)}% das pretas+pardas, abaixo do mínimo pré-fixado de 80% para ambos"
            )
        elif not election_support["outcome_support_sufficient"]:
            reason = "o subconjunto comum não tem ao menos 10 eleitas e 10 não eleitas em cada grupo"
        else:
            reason = race_election_comparison["withheld_reason"]
        report_lines.append(
            f"Não estimamos probabilidades ajustadas nem ICs: {reason}. A diferença observada permanece descritiva; sem suporte não é possível comparar validamente as especificações sem e com despesa."
        )
        report_lines.append(
            "Uma mudança após acrescentar despesas não seria, de todo modo, explicação causal nem prova de discriminação."
        )
    report_lines.extend([
        "",
        "Interação ajustada: GLM Binomial/logit fracionário para participação de votos, com `log1p(despesa em R$)`, indicador pretas+pardas e interação entre os dois; referência: brancas. Controles: UF, partido, idade na eleição, sexo e escolaridade; erros-padrão HC1. Deduplicado é principal; todas as linhas, sensibilidade. Custo por voto não é preditor porque usa votos no denominador.",
        "",
        "| Cenário | N | Interação despesa×pretas+pardas (logit) | IC 95% HC1 | p |",
        "|---|---:|---:|---:|---:|",
    ])
    for scenario, estimate in race_estimates.items():
        p_display = "<0,0001" if estimate["p_value"] < 0.0001 else _pt_decimal(estimate["p_value"], 4)
        model_name = "raca_deduplicado" if scenario == "deduplicado" else "raca_todas_as_linhas"
        model_n = next(model["n"] for model in race_analysis["models"] if model["name"] == model_name)
        report_lines.append(
            f"| {scenario} | {_pt_int(model_n)} | {_pt_decimal(estimate['coefficient'], 4)} | {_pt_decimal(estimate['ci95_low'], 4)}–{_pt_decimal(estimate['ci95_high'], 4)} | {p_display} |"
        )
    report_lines.append(
        "O coeficiente de interação resume a diferença entre inclinações na escala logit; não é uma diferença causal nem uma mudança direta em pontos percentuais. Os demais coeficientes e seus intervalos estão no CSV."
    )
    for scenario, estimate in race_estimates.items():
        if estimate["ci95_low"] > 0:
            interpretation = "o IC 95% ficou acima de zero, compatível com inclinação associativa maior no grupo pretas+pardas"
        elif estimate["ci95_high"] < 0:
            interpretation = "o IC 95% ficou abaixo de zero, compatível com inclinação associativa menor no grupo pretas+pardas"
        else:
            interpretation = "o IC 95% inclui zero; estes dados não distinguem com clareza as inclinações dos grupos"
        report_lines.append(f"No cenário {scenario}, {interpretation}.")
    report_lines.extend([
        "",
        "Curvas padronizadas usam os mesmos perfis de UF, partido, idade, sexo e escolaridade em ambos os grupos, mas apenas em faixas de despesa com suporte contextual pré-especificado. Sombras mostram ICs pontuais de 95% pelo método delta/HC1; não são intervalos individuais.",
    ])
    for scenario, curve in race_analysis["curves"].items():
        coverage = curve["eligible_group_coverage"]
        candidate_points = curve["candidate_support_points"]
        max_white_point_coverage = max(
            (point["brancas_coverage"] for point in candidate_points),
            default=0.0,
        )
        max_black_brown_point_coverage = max(
            (point["pretas_pardas_coverage"] for point in candidate_points),
            default=0.0,
        )
        report_lines.append(
            f"Suporte {scenario}: {_pt_int(curve['eligible_uf_party_cells_n'])} células UF×partido elegíveis (N≥10 em cada grupo), cobrindo {_pt_decimal(coverage['brancas'] * 100, 1)}% das brancas e {_pt_decimal(coverage['pretas_pardas'] * 100, 1)}% das pretas+pardas. A maior cobertura de qualquer ponto candidato foi {_pt_decimal(max_white_point_coverage * 100, 1)}% e {_pt_decimal(max_black_brown_point_coverage * 100, 1)}%, respectivamente; {_pt_int(len(curve['points']))} pontos publicados."
        )
        if not curve["points"]:
            report_lines.append(f"Sem curva por suporte insuficiente: {curve['no_curve_reason']}. Não houve extrapolação.")
        elif curve["initial_common_support_lower_brl"] is not None:
            report_lines.append(
                f"Faixa nacional inicial P10–P90 comum nas células elegíveis: R$ {_pt_decimal(curve['initial_common_support_lower_brl'])}–R$ {_pt_decimal(curve['initial_common_support_upper_brl'])}; cada ponto publicado também cumpre cobertura mínima de 80% em ambos os grupos."
            )
    report_lines.extend([
        "",
        "| Cenário | Despesa (R$) | Brancas: participação prevista (IC 95%) | Pretas+pardas: participação prevista (IC 95%) | Cobertura brancas | Cobertura pretas+pardas |",
        "|---|---:|---:|---:|---:|---:|",
    ])
    for scenario, curve in race_analysis["curves"].items():
        for row in curve["points"]:
            white = f"{_pt_decimal(row['brancas_prediction'] * 100, 4)}% ({_pt_decimal(row['brancas_ci95_lower'] * 100, 4)}–{_pt_decimal(row['brancas_ci95_upper'] * 100, 4)}%)"
            black_brown = f"{_pt_decimal(row['pretas_pardas_prediction'] * 100, 4)}% ({_pt_decimal(row['pretas_pardas_ci95_lower'] * 100, 4)}–{_pt_decimal(row['pretas_pardas_ci95_upper'] * 100, 4)}%)"
            report_lines.append(
                f"| {scenario} | {_pt_decimal(row['expense_brl'])} | {white} | {black_brown} | {_pt_decimal(row['brancas_coverage'] * 100, 1)}% | {_pt_decimal(row['pretas_pardas_coverage'] * 100, 1)}% |"
            )
    report_lines.extend([
        "",
        "![Curva raça/cor — despesas deduplicadas](tse-2022-race-interaction-curve-deduplicado.svg)",
        "",
        "![Curva raça/cor — todas as linhas](tse-2022-race-interaction-curve-todas-as-linhas.svg)",
        "",
        "A tabela de suporte apresenta contagens, faixas P10–P90 e proporção da coorte por UF, partido e célula UF×partido; a tabela de suporte por ponto registra a cobertura usada para aceitar ou suprimir cada ponto. Diferenças são associações ajustadas, não efeitos causais ou prova de discriminação. Despesa declarada contratada não significa pagamento efetivo nem recurso necessariamente público.",
        "A comparação financeira com 2026 permanece adiada. Depois de 3 de novembro, verificar novamente disponibilidade e cobertura das prestações `Final`; a data não aprova automaticamente a base.",
        "",
        "Artefatos: `tse-2022-race-population-counts.csv`, `tse-2022-race-group-descriptives.csv`, `tse-2022-race-interaction-coefficients.csv`, `tse-2022-race-interaction-curve.csv`, `tse-2022-race-curve-support.csv` e `tse-2022-race-support-by-uf-party.csv`.",
        "",
    ])
    report_lines.extend([
        "## INAPTO — levantamento separado por tipo de prestação",
        "",
        f"Entre {_pt_int(inapto_summary['candidate_count'])} candidaturas INAPTO, {_pt_int(inapto_summary['candidates_with_any_expense_rows'])} têm ao menos uma ocorrência e {_pt_int(inapto_summary['candidates_without_any_expense_rows'])} não têm linha de despesa na base. A tabela usa ocorrências intactas e também mostra o cenário deduplicado; não mistura INAPTO à regressão APTO.",
        "",
        "| Tipo | Candidatos com linha | Sem linha | Linhas todas | Linhas zero | Total todas (R$) | Linhas deduplicadas | Total deduplicado (R$) | Linhas excluídas | Candidatos afetados |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for row in inapto_rows:
        report_lines.append(
            f"| {row['tp_prestacao_contas']} | {_pt_int(row['candidates_with_rows'])} | {_pt_int(row['candidates_without_rows'])} | {_pt_int(row['all_lines_occurrence_rows'])} | {_pt_int(row['all_lines_zero_amount_rows'])} | {_pt_brl_centavos(row['all_lines_declared_expense_centavos'])} | {_pt_int(row['deduplicated_occurrence_rows'])} | {_pt_brl_centavos(row['deduplicated_declared_expense_centavos'])} | {_pt_int(row['excluded_occurrence_rows'])} | {_pt_int(row['excluded_affected_candidates'])} |"
        )
    report_lines.extend([
        "",
        "## Pagamentos e limitações",
        "",
        result["payment_integration"]["status"] + ".",
    ])
    report_lines.extend(f"- {limitation}" for limitation in result["limitations"])
    report_lines.extend([
        "",
        "## Reprodução",
        "",
        "```sh",
        "python -m tse_pilot analyze --database data/derived/2022/pilot.sqlite --validation data/derived/2022/validation.json --output reports",
        "```",
        "",
        "A saída JSON registra contagens, modelos, metadados de execução e limitações; os coeficientes e o levantamento INAPTO também são arquivos CSV.",
        "",
    ])
    (output_dir / "tse-2022-financial-analysis.md").write_text("\n".join(report_lines), encoding="utf-8")
    return result
