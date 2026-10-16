from __future__ import annotations

import csv
import hashlib
import html
import json
import math
import sqlite3
import zipfile
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable

from .pipeline import FEDERAL_CARGO, UF_CODES

SCENARIO_DEDUPLICATED = "deduplicado_principal"
SCENARIO_ALL_ROWS = "todas_as_linhas_sensibilidade"
CSV_COLUMN_NAMES = {
    "sq_candidate": "sq_candidato",
    "uf": "uf",
    "candidate_number": "numero_candidato",
    "candidate_name": "nome_candidato",
    "candidate_status_code": "codigo_situacao_candidatura",
    "candidate_status": "situacao_candidatura",
    "total_status_code": "codigo_resultado_turno",
    "total_status": "resultado_turno",
    "source_member": "arquivo_origem",
    "source_row": "linha_origem",
    "population": "populacao",
    "scenario_status": "status_cenario",
    "expense_row_count": "quantidade_linhas_despesa",
    "declared_expense_centavos": "despesa_declarada_centavos",
    "expense_observation": "observacao_despesa",
    "exact_repeat_rows": "repeticoes_exatas",
    "vote_row_count": "quantidade_registros_voto",
    "valid_nominal_votes": "votos_nominais_validos",
    "vote_observation": "observacao_votacao",
    "cost_per_vote_brl": "custo_por_voto_reais",
    "expense_deduplicated_centavos": "despesa_tratamento_deduplicado_centavos",
    "expense_all_rows_centavos": "despesa_todas_as_linhas_centavos",
    "difference_all_rows_minus_deduplicated_centavos": "diferenca_todas_as_linhas_menos_deduplicado_centavos",
    "difference_relative_to_deduplicated": "diferenca_relativa_ao_deduplicado",
    "cost_per_vote_deduplicated_brl": "custo_por_voto_reais_deduplicado",
    "cost_per_vote_all_rows_brl": "custo_por_voto_reais_todas_as_linhas",
    "exact_repeat_rows_all_rows_sensitivity": "repeticoes_exatas_todas_as_linhas_sensibilidade",
    "scenario": "cenario",
    "measure": "medida",
    "count_observed": "quantidade_observada",
    "count_zero": "quantidade_igual_a_zero",
    "count_absent": "quantidade_ausente",
    "total": "total",
    "p50": "percentil_50",
    "p90": "percentil_90",
    "p99": "percentil_99",
    "denominator_rule": "regra_do_denominador",
    "candidate_count_with_cost": "candidatos_com_custo",
    "expense_total_centavos_complete_pairs": "despesa_total_pares_completos_centavos",
    "votes_total_complete_pairs": "votos_totais_pares_completos",
    "aggregate_cost_brl_per_vote": "custo_agregado_reais_por_voto",
    "median_cost_brl_per_vote": "mediana_reais_por_voto",
    "p90_cost_brl_per_vote": "percentil_90_reais_por_voto",
    "p99_cost_brl_per_vote": "percentil_99_reais_por_voto",
    "mean_cost_brl_per_vote": "media_reais_por_voto",
    "candidate_population": "candidatos_na_populacao",
    "expense_observed": "despesas_observadas",
    "expense_zero": "despesas_iguais_a_zero",
    "expense_absent": "despesas_ausentes",
    "vote_observed": "votacoes_observadas",
    "vote_zero": "votacoes_iguais_a_zero",
    "vote_absent": "votacoes_ausentes",
    "complete_pairs": "pares_completos",
    "expense_total_centavos": "despesa_total_centavos",
    "votes_total": "votos_totais",
    "expense_median_centavos": "mediana_despesa_centavos",
    "votes_median": "mediana_votos",
    "pearson_expense_votes": "correlacao_pearson_despesa_votos",
    "spearman_expense_votes": "correlacao_spearman_despesa_votos",
}


def _portuguese_value(field: str, value: object) -> object:
    if field in {"expense_observation", "vote_observation"}:
        return {
            "absent": "ausente",
            "observed": "observado",
            "observed_zero": "zero_observado",
        }.get(str(value), value)
    if field == "scenario_status" and value == "exploratory_only":
        return "somente_exploratorio"
    return value


GENERATED_FILES = (
    "exploratory_metadata.json",
    "exploratory_candidates.csv",
    "exploratory_deduplicated_primary.csv",
    "exploratory_all_rows_sensitivity.csv",
    "exploratory_deduplicated_vs_all_rows.csv",
    "exploratory_cost_per_vote.csv",
    "exploratory_distributions.csv",
    "exploratory_uf_associations.csv",
    "exploratory_report.md",
)
OBSOLETE_FILES = (
    "exploratory_scenario_a_deduplicated_primary.csv",
    "exploratory_scenario_b_preserve_all_sensitivity.csv",
    "exploratory_scenario_comparison.csv",
    "exploratory_scenario_a_preserve_all.csv",
    "exploratory_scenario_b_remove_exact_repeats.csv",
)


def _text(row: dict[str, str], field: str) -> str:
    return (row.get(field) or "").strip()


def _missing(value: str | None) -> bool:
    return value is None or value.strip() in {"", "#NULO", "#NE"}


def _centavos(value: str) -> int:
    normalized = value.strip().replace(".", "").replace(",", ".")
    amount = Decimal(normalized)
    if not amount.is_finite() or amount < 0 or amount.as_tuple().exponent < -2:
        raise ValueError(f"valor monetário inválido: {value}")
    return int(amount * 100)


def _money(centavos: int | None) -> str:
    if centavos is None:
        return "ausente"
    value = Decimal(centavos) / Decimal(100)
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _resource_path(manifest: dict, resource_key: str) -> Path:
    for resource in manifest["resources"]:
        if resource["resource_key"] == resource_key:
            return Path(resource["local_path"])
    raise ValueError(f"recurso ausente no manifesto: {resource_key}")


def _selected_member(name: str, prefix: str) -> bool:
    if not name.startswith(prefix) or not name.casefold().endswith(".csv"):
        return False
    suffix = name.rsplit("_", 1)[-1][:-4]
    return suffix in UF_CODES


def _iter_rows(archive_path: Path, prefix: str) -> Iterable[tuple[dict[str, str], str, int]]:
    with zipfile.ZipFile(archive_path) as archive:
        for info in sorted(archive.infolist(), key=lambda item: item.filename):
            if not _selected_member(info.filename, prefix):
                continue
            with archive.open(info) as raw:
                text = (line.decode("latin-1") for line in raw)
                reader = csv.DictReader(text, delimiter=";")
                for row_number, row in enumerate(reader, start=2):
                    yield row, info.filename, row_number


def _row_signature(row: dict[str, str]) -> str:
    payload = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, object]]) -> None:
    portuguese_fields = [CSV_COLUMN_NAMES[field] for field in fieldnames]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=portuguese_fields)
        writer.writeheader()
        for row in rows:
            localized = {
                CSV_COLUMN_NAMES[field]: _portuguese_value(field, value)
                for field, value in row.items()
            }
            writer.writerow(localized)


def _observation(row_count: int, amount_centavos: int) -> tuple[str, str]:
    if row_count == 0:
        return "absent", ""
    if amount_centavos == 0:
        return "observed_zero", "0"
    return "observed", str(amount_centavos)


def _quantile(values: list[int], fraction: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return round(ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower))


def _pearson(pairs: list[tuple[int, int]]) -> str:
    if len(pairs) < 2:
        return ""
    xs = [pair[0] for pair in pairs]
    ys = [pair[1] for pair in pairs]
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in pairs)
    denominator_x = sum((x - mean_x) ** 2 for x in xs)
    denominator_y = sum((y - mean_y) ** 2 for y in ys)
    denominator = math.sqrt(denominator_x * denominator_y)
    if denominator == 0:
        return ""
    return f"{numerator / denominator:.6f}"


def _rank(values: list[int]) -> list[float]:
    ranks = [0.0] * len(values)
    ordered = sorted(range(len(values)), key=values.__getitem__)
    start = 0
    while start < len(ordered):
        end = start + 1
        while end < len(ordered) and values[ordered[end]] == values[ordered[start]]:
            end += 1
        average_rank = (start + 1 + end) / 2
        for index in ordered[start:end]:
            ranks[index] = average_rank
        start = end
    return ranks


def _spearman(pairs: list[tuple[int, int]]) -> str:
    if len(pairs) < 2:
        return ""
    ranked_pairs = list(zip(_rank([x for x, _ in pairs]), _rank([y for _, y in pairs])))
    return _pearson(ranked_pairs)


def _load_validation(validation_path: Path) -> dict:
    validation = json.loads(Path(validation_path).read_text(encoding="utf-8"))
    if validation.get("status") != "approved":
        raise ValueError("exploração exige uma base aprovada pela validação do pipeline")
    fatal_counts = validation.get("fatal_counts", {})
    unexpected = {key: value for key, value in fatal_counts.items() if value}
    if unexpected:
        raise ValueError(f"exploração recusada: há falhas críticas de validação: {unexpected}")
    return validation


def _load_candidates(manifest: dict) -> dict[str, dict[str, str]]:
    candidates: dict[str, dict[str, str]] = {}
    archive = _resource_path(manifest, "candidates_2022")
    for row, member, row_number in _iter_rows(archive, "consulta_cand_2022_"):
        if _text(row, "ANO_ELEICAO") != "2022" or _text(row, "NR_TURNO") != "1" or _text(row, "DS_CARGO").casefold() != FEDERAL_CARGO:
            continue
        candidate_id = _text(row, "SQ_CANDIDATO")
        if not candidate_id:
            raise ValueError(f"candidato sem SQ_CANDIDATO: {member}:{row_number}")
        if candidate_id in candidates:
            raise ValueError(f"candidato repetido no inventário exploratório: {candidate_id}")
        candidates[candidate_id] = {
            "sq_candidate": candidate_id,
            "uf": _text(row, "SG_UF"),
            "candidate_number": _text(row, "NR_CANDIDATO"),
            "candidate_name": _text(row, "NM_CANDIDATO"),
            "candidate_status_code": _text(row, "CD_SITUACAO_CANDIDATURA"),
            "candidate_status": _text(row, "DS_SITUACAO_CANDIDATURA"),
            "total_status_code": _text(row, "CD_SIT_TOT_TURNO"),
            "total_status": _text(row, "DS_SIT_TOT_TURNO"),
            "source_member": member,
            "source_row": str(row_number),
        }
    return candidates


def _load_votes(validation: dict, validation_path: Path, candidates: dict[str, dict[str, str]]) -> dict[str, tuple[int, int]]:
    database_path = Path(validation.get("database", "")) if validation.get("database") else validation_path.parent / "pilot.sqlite"
    if not database_path.is_file() or database_path.suffix.casefold() != ".sqlite":
        raise ValueError("validation.json não aponta para o SQLite validado do piloto")
    connection = sqlite3.connect(database_path)
    result: dict[str, tuple[int, int]] = {}
    for candidate_id, row_count, valid_votes in connection.execute(
        "SELECT sq_candidate, COUNT(*), COALESCE(SUM(valid_votes), 0) FROM votes GROUP BY sq_candidate"
    ):
        if candidate_id in candidates:
            result[candidate_id] = (int(row_count), int(valid_votes))
    connection.close()
    return result


def _empty_scenario(candidates: dict[str, dict[str, str]]) -> dict[str, dict[str, int]]:
    return {candidate_id: {"expense_row_count": 0, "declared_expense_centavos": 0, "exact_repeat_rows": 0} for candidate_id in candidates}


def _load_final_expenses(
    manifest: dict,
    candidates: dict[str, dict[str, str]],
    database_path: Path,
) -> tuple[dict[str, dict[str, int]], dict[str, int]]:
    primary = _empty_scenario(candidates)
    sensitivity = _empty_scenario(candidates)
    seen_signatures = sqlite3.connect(":memory:")
    seen_signatures.execute(
        "CREATE TABLE seen_signatures (source_member TEXT, signature TEXT, source_row INTEGER)"
    )
    seen_signatures.execute(
        "CREATE INDEX seen_signatures_key ON seen_signatures (source_member, signature)"
    )
    occurrences = sqlite3.connect(database_path)
    occurrence_columns = [
        row[1]
        for row in occurrences.execute("PRAGMA table_info(expense_occurrences)")
        if not row[1].startswith("_")
    ]
    if not occurrence_columns:
        raise ValueError("a comparação exige expense_occurrences com os campos originais")
    quoted_fields = ", ".join(
        '"' + field.replace('"', '""') + '"' for field in occurrence_columns
    )
    counters = Counter()
    affected_candidates: set[str] = set()
    archive = _resource_path(manifest, "accounts_2022")
    for row, member, row_number in _iter_rows(archive, "despesas_contratadas_candidatos_2022_"):
        if _text(row, "AA_ELEICAO") != "2022" or _text(row, "ST_TURNO") != "1" or _text(row, "DS_CARGO").casefold() != FEDERAL_CARGO:
            continue
        counters["expense_rows_selected_all_types"] += 1
        if _text(row, "TP_PRESTACAO_CONTAS").casefold() != "final":
            continue
        counters["expense_rows_selected_final_all_statuses"] += 1
        candidate_id = _text(row, "SQ_CANDIDATO")
        if candidate_id not in candidates:
            continue
        counters["expense_rows_selected_final_apto"] += 1
        amount_text = row.get("VR_DESPESA_CONTRATADA")
        if _missing(amount_text):
            raise ValueError(f"despesa final sem valor no inventário exploratório: {member}:{row_number}")
        try:
            amount_centavos = _centavos(amount_text)
        except (InvalidOperation, ValueError) as error:
            raise ValueError(f"valor inválido em {member}:{row_number}: {error}") from error
        sensitivity[candidate_id]["expense_row_count"] += 1
        sensitivity[candidate_id]["declared_expense_centavos"] += amount_centavos
        signature = _row_signature(row)
        raw_values = tuple(row.get(field) for field in occurrence_columns)
        duplicate = False
        matching_rows = seen_signatures.execute(
            "SELECT source_row FROM seen_signatures WHERE source_member = ? AND signature = ?",
            (member, signature),
        ).fetchall()
        for (seen_row_number,) in matching_rows:
            seen_values = occurrences.execute(
                f"""
                SELECT {quoted_fields} FROM expense_occurrences
                WHERE _source_member = ? AND _source_row = ?
                """,
                (member, seen_row_number),
            ).fetchone()
            if seen_values is not None and tuple(seen_values) == raw_values:
                duplicate = True
                break
        if duplicate:
            sensitivity[candidate_id]["exact_repeat_rows"] += 1
            counters["exact_repeat_rows_in_final_apto"] += 1
            affected_candidates.add(candidate_id)
            continue
        seen_signatures.execute(
            "INSERT INTO seen_signatures VALUES (?, ?, ?)",
            (member, signature, row_number),
        )
        primary[candidate_id]["expense_row_count"] += 1
        primary[candidate_id]["declared_expense_centavos"] += amount_centavos
    seen_signatures.close()
    occurrences.close()
    counters["candidates_affected_by_dedup_final_apto"] = len(affected_candidates)
    counters["preserve_all_total_centavos_final_apto"] = sum(
        row["declared_expense_centavos"] for row in sensitivity.values()
    )
    counters["deduplicated_total_centavos_final_apto"] = sum(
        row["declared_expense_centavos"] for row in primary.values()
    )
    counters["financial_difference_centavos_final_apto"] = (
        counters["preserve_all_total_centavos_final_apto"]
        - counters["deduplicated_total_centavos_final_apto"]
    )
    return (primary, sensitivity), dict(counters)


def _scenario_rows(
    candidates: dict[str, dict[str, str]],
    scenario: dict[str, dict[str, int]],
    votes: dict[str, tuple[int, int]],
) -> list[dict[str, object]]:
    rows = []
    for candidate_id, candidate in sorted(candidates.items(), key=lambda item: (item[1]["uf"], item[1]["candidate_number"], item[0])):
        expense = scenario[candidate_id]
        expense_observation, expense_value = _observation(expense["expense_row_count"], expense["declared_expense_centavos"])
        vote_row_count, valid_votes = votes.get(candidate_id, (0, 0))
        vote_observation = "absent" if not vote_row_count else ("observed_zero" if valid_votes == 0 else "observed")
        cost_per_vote = ""
        if expense_observation != "absent" and vote_observation == "observed":
            cost_per_vote = f"{(Decimal(expense_value) / Decimal(valid_votes) / Decimal(100)):.6f}"
        rows.append({
            **candidate,
            "population": "APTO",
            "scenario_status": "exploratory_only",
            "expense_row_count": expense["expense_row_count"],
            "declared_expense_centavos": expense_value,
            "expense_observation": expense_observation,
            "exact_repeat_rows": expense["exact_repeat_rows"],
            "vote_row_count": vote_row_count if vote_row_count else "",
            "valid_nominal_votes": valid_votes if vote_row_count else "",
            "vote_observation": vote_observation,
            "cost_per_vote_brl": cost_per_vote,
        })
    return rows


def _comparison_rows(rows_deduplicated: list[dict[str, object]], rows_all_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    def index_rows(rows: list[dict[str, object]], treatment: str) -> dict[str, dict[str, object]]:
        indexed = {}
        for row in rows:
            candidate_id = row.get("sq_candidate")
            if not isinstance(candidate_id, str) or not candidate_id:
                raise ValueError(f"candidato sem sq_candidate no tratamento {treatment}")
            if candidate_id in indexed:
                raise ValueError(f"chave de candidato duplicada no tratamento {treatment}: {candidate_id}")
            indexed[candidate_id] = row
        return indexed

    indexed_deduplicated = index_rows(rows_deduplicated, "deduplicado")
    indexed_all_rows = index_rows(rows_all_rows, "todas as linhas")
    if len(rows_deduplicated) != len(rows_all_rows):
        raise ValueError(
            "comprimentos diferentes entre tratamento deduplicado e todas as linhas: "
            f"{len(rows_deduplicated)} e {len(rows_all_rows)}"
        )
    keys_deduplicated = set(indexed_deduplicated)
    keys_all_rows = set(indexed_all_rows)
    if keys_deduplicated != keys_all_rows:
        missing_from_all_rows = sorted(keys_deduplicated - keys_all_rows)
        missing_from_deduplicated = sorted(keys_all_rows - keys_deduplicated)
        raise ValueError(
            "chaves de candidato diferentes entre tratamentos; "
            f"faltam em todas as linhas: {missing_from_all_rows}; "
            f"faltam no deduplicado: {missing_from_deduplicated}"
        )

    identity_fields = ("uf", "candidate_number", "candidate_name", "vote_observation", "valid_nominal_votes")
    result = []
    for row_deduplicated in rows_deduplicated:
        candidate_id = row_deduplicated["sq_candidate"]
        row_all_rows = indexed_all_rows[candidate_id]
        if any(row_deduplicated.get(field) != row_all_rows.get(field) for field in identity_fields):
            raise ValueError(f"identidade divergente para o candidato {candidate_id} entre deduplicado e todas as linhas")
        amount_deduplicated = int(row_deduplicated["declared_expense_centavos"]) if row_deduplicated["declared_expense_centavos"] != "" else None
        amount_all_rows = int(row_all_rows["declared_expense_centavos"]) if row_all_rows["declared_expense_centavos"] != "" else None
        delta = amount_all_rows - amount_deduplicated if amount_deduplicated is not None and amount_all_rows is not None else None
        relative = (delta / amount_deduplicated) if delta is not None and amount_deduplicated else None
        result.append({
            "sq_candidate": candidate_id,
            "uf": row_deduplicated["uf"],
            "candidate_number": row_deduplicated["candidate_number"],
            "candidate_name": row_deduplicated["candidate_name"],
            "expense_deduplicated_centavos": "" if amount_deduplicated is None else amount_deduplicated,
            "expense_all_rows_centavos": "" if amount_all_rows is None else amount_all_rows,
            "difference_all_rows_minus_deduplicated_centavos": "" if delta is None else delta,
            "difference_relative_to_deduplicated": "" if relative is None else f"{relative:.8f}",
            "cost_per_vote_deduplicated_brl": row_deduplicated["cost_per_vote_brl"],
            "cost_per_vote_all_rows_brl": row_all_rows["cost_per_vote_brl"],
            "exact_repeat_rows_all_rows_sensitivity": row_all_rows["exact_repeat_rows"],
            "vote_observation": row_deduplicated["vote_observation"],
            "valid_nominal_votes": row_deduplicated["valid_nominal_votes"],
        })
    return result


def _summary_rows(rows: list[dict[str, object]], scenario_name: str) -> list[dict[str, object]]:
    expenses = [int(row["declared_expense_centavos"]) for row in rows if row["expense_observation"] != "absent"]
    votes = [int(row["valid_nominal_votes"]) for row in rows if row["vote_observation"] != "absent"]
    return [
        {"scenario": scenario_name, "measure": "despesas_contratadas_declaradas_centavos", "count_observed": len(expenses), "count_zero": sum(value == 0 for value in expenses), "count_absent": sum(row["expense_observation"] == "absent" for row in rows), "total": sum(expenses), "p50": _quantile(expenses, 0.50), "p90": _quantile(expenses, 0.90), "p99": _quantile(expenses, 0.99)},
        {"scenario": scenario_name, "measure": "votos_nominais_validos", "count_observed": len(votes), "count_zero": sum(value == 0 for value in votes), "count_absent": sum(row["vote_observation"] == "absent" for row in rows), "total": sum(votes), "p50": _quantile(votes, 0.50), "p90": _quantile(votes, 0.90), "p99": _quantile(votes, 0.99)},
    ]


def _cost_rows(rows: list[dict[str, object]], scenario_name: str) -> list[dict[str, object]]:
    pairs = [
        (int(row["declared_expense_centavos"]), int(row["valid_nominal_votes"]))
        for row in rows
        if row["expense_observation"] != "absent" and row["vote_observation"] == "observed"
    ]
    costs = [Decimal(expense) / Decimal(votes) for expense, votes in pairs]
    total_expense = sum(expense for expense, _ in pairs)
    total_votes = sum(votes for _, votes in pairs)
    aggregate = Decimal(total_expense) / Decimal(total_votes) if total_votes else None
    return [{
        "scenario": scenario_name,
        "denominator_rule": "somente candidatos com despesa observada e votos > 0; zero de despesa preservado",
        "candidate_count_with_cost": len(pairs),
        "expense_total_centavos_complete_pairs": total_expense,
        "votes_total_complete_pairs": total_votes,
        "aggregate_cost_brl_per_vote": "" if aggregate is None else f"{aggregate / Decimal(100):.2f}",
        "median_cost_brl_per_vote": "" if not costs else f"{Decimal(str(_quantile([float(value) for value in costs], 0.5))) / Decimal(100):.2f}",
        "p90_cost_brl_per_vote": "" if not costs else f"{Decimal(str(_quantile([float(value) for value in costs], 0.9))) / Decimal(100):.2f}",
        "p99_cost_brl_per_vote": "" if not costs else f"{Decimal(str(_quantile([float(value) for value in costs], 0.99))) / Decimal(100):.2f}",
        "mean_cost_brl_per_vote": "" if not costs else f"{(sum(costs) / Decimal(len(costs))) / Decimal(100):.2f}",
    }]


def _uf_rows(rows: list[dict[str, object]], scenario_name: str) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["uf"])].append(row)
    result = []
    for uf in sorted(grouped):
        items = grouped[uf]
        expenses = [int(row["declared_expense_centavos"]) for row in items if row["expense_observation"] != "absent"]
        votes = [int(row["valid_nominal_votes"]) for row in items if row["vote_observation"] != "absent"]
        pairs = [(int(row["declared_expense_centavos"]), int(row["valid_nominal_votes"])) for row in items if row["expense_observation"] != "absent" and row["vote_observation"] != "absent"]
        result.append({
            "scenario": scenario_name,
            "uf": uf,
            "candidate_population": len(items),
            "expense_observed": len(expenses),
            "expense_zero": sum(value == 0 for value in expenses),
            "expense_absent": sum(row["expense_observation"] == "absent" for row in items),
            "vote_observed": len(votes),
            "vote_zero": sum(value == 0 for value in votes),
            "vote_absent": sum(row["vote_observation"] == "absent" for row in items),
            "complete_pairs": len(pairs),
            "expense_total_centavos": sum(expenses),
            "votes_total": sum(votes),
            "expense_median_centavos": _quantile(expenses, 0.50),
            "votes_median": _quantile(votes, 0.50),
            "pearson_expense_votes": _pearson(pairs),
            "spearman_expense_votes": _spearman(pairs),
        })
    return result


def _svg_scatter(rows: list[dict[str, object]], expense_field: str, path: Path, title: str) -> None:
    points = []
    for row in rows:
        if row["expense_observation"] == "absent" or row["vote_observation"] == "absent":
            continue
        expense_reais = int(row[expense_field]) / 100
        votes = int(row["valid_nominal_votes"])
        points.append((math.log10(1 + votes), math.log10(1 + expense_reais), str(row["uf"])))
    width, height = 900, 560
    left, top, plot_w, plot_h = 90, 55, 760, 410
    max_x = max((point[0] for point in points), default=1)
    max_y = max((point[1] for point in points), default=1)
    elements = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">', '<rect width="100%" height="100%" fill="white"/>', f'<text x="{width / 2}" y="28" text-anchor="middle" font-family="sans-serif" font-size="18">{html.escape(title)}</text>', f'<line x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}" stroke="black"/><line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" stroke="black"/>', f'<text x="{left + plot_w / 2}" y="530" text-anchor="middle" font-family="sans-serif">log10(1 + votos nominais válidos)</text>', f'<text x="20" y="{top + plot_h / 2}" text-anchor="middle" transform="rotate(-90 20 {top + plot_h / 2})" font-family="sans-serif">log10(1 + despesas em R$)</text>']
    for x, y, uf in points:
        px = left + (x / max_x) * plot_w if max_x else left
        py = top + plot_h - (y / max_y) * plot_h if max_y else top + plot_h
        elements.append(f'<circle cx="{px:.2f}" cy="{py:.2f}" r="2.5" fill="#2563eb" opacity="0.55"><title>{html.escape(uf)}</title></circle>')
    elements.append(f'<text x="{left}" y="{top + plot_h + 22}" font-family="sans-serif" font-size="11">0</text><text x="{left + plot_w}" y="{top + plot_h + 22}" text-anchor="end" font-family="sans-serif" font-size="11">máximo</text></svg>')
    path.write_text("".join(elements), encoding="utf-8")


def _svg_uf_totals(rows_deduplicated: list[dict[str, object]], rows_all_rows: list[dict[str, object]], path: Path) -> None:
    totals_deduplicated = {row["uf"]: int(row["expense_total_centavos"]) for row in rows_deduplicated}
    totals_all_rows = {row["uf"]: int(row["expense_total_centavos"]) for row in rows_all_rows}
    ufs = sorted(set(totals_deduplicated) | set(totals_all_rows))
    width, height = 1100, 560
    left, top, plot_w, plot_h = 55, 45, 1000, 410
    maximum = max([*totals_deduplicated.values(), *totals_all_rows.values(), 1])
    group_w = plot_w / max(len(ufs), 1)
    elements = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">', '<rect width="100%" height="100%" fill="white"/>', f'<text x="{width / 2}" y="25" text-anchor="middle" font-family="sans-serif" font-size="18">Despesas declaradas por UF — deduplicado e todas as linhas</text>']
    for index, uf in enumerate(ufs):
        x = left + index * group_w
        for offset, value, color in ((group_w * 0.18, totals_deduplicated.get(uf, 0), "#2563eb"), (group_w * 0.52, totals_all_rows.get(uf, 0), "#f97316")):
            bar_h = value / maximum * plot_h
            elements.append(f'<rect x="{x + offset:.2f}" y="{top + plot_h - bar_h:.2f}" width="{group_w * 0.24:.2f}" height="{bar_h:.2f}" fill="{color}"><title>{html.escape(uf)}: {_money(value)}</title></rect>')
        elements.append(f'<text x="{x + group_w / 2:.2f}" y="{top + plot_h + 18}" text-anchor="middle" font-family="sans-serif" font-size="11">{uf}</text>')
    elements.extend([f'<line x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}" stroke="black"/>', '<rect x="650" y="500" width="12" height="12" fill="#2563eb"/><text x="668" y="511" font-family="sans-serif">Tratamento deduplicado</text>', '<rect x="855" y="500" width="12" height="12" fill="#f97316"/><text x="873" y="511" font-family="sans-serif">Todas as linhas</text></svg>'])
    path.write_text("".join(elements), encoding="utf-8")


def _svg_uf_spearman(rows_deduplicated: list[dict[str, object]], rows_all_rows: list[dict[str, object]], path: Path) -> None:
    by_scenario = (("Tratamento deduplicado", rows_deduplicated, "#2563eb", -3), ("Todas as linhas", rows_all_rows, "#f97316", 3))
    ufs = sorted({str(row["uf"]) for _, rows, _, _ in by_scenario for row in rows})
    width, height = 1100, 590
    left, top, plot_w, plot_h = 70, 65, 990, 420
    x_step = plot_w / max(len(ufs), 1)
    y = lambda correlation: top + (1 - float(correlation)) * plot_h / 2
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'<text x="{width / 2}" y="28" text-anchor="middle" font-family="sans-serif" font-size="18">Associação de despesas e votos por UF — deduplicado e todas as linhas</text>',
        '<text x="70" y="48" font-family="sans-serif" font-size="12">Candidatos com despesa e votação observadas; zeros observados incluídos</text>',
    ]
    for correlation in (-1, -0.5, 0, 0.5, 1):
        line_y = y(correlation)
        elements.append(f'<line x1="{left}" y1="{line_y:.2f}" x2="{left + plot_w}" y2="{line_y:.2f}" stroke="{"#666" if correlation == 0 else "#ccc"}"/>')
        elements.append(f'<text x="{left - 10}" y="{line_y + 4:.2f}" text-anchor="end" font-family="sans-serif" font-size="11">{correlation:g}</text>')
    elements.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" stroke="black"/>')
    elements.append(f'<text x="18" y="{top + plot_h / 2}" text-anchor="middle" transform="rotate(-90 18 {top + plot_h / 2})" font-family="sans-serif" font-size="12">rho de Spearman</text>')
    for index, uf in enumerate(ufs):
        center = left + (index + 0.5) * x_step
        elements.append(f'<text x="{center:.2f}" y="{top + plot_h + 18}" text-anchor="middle" font-family="sans-serif" font-size="10">{html.escape(uf)}</text>')
        for scenario, rows, color, offset in by_scenario:
            row = next((item for item in rows if item["uf"] == uf), None)
            if row is None or row["spearman_expense_votes"] == "":
                continue
            point_y = y(row["spearman_expense_votes"])
            elements.append(f'<circle cx="{center + offset:.2f}" cy="{point_y:.2f}" r="3.5" fill="{color}"><title>{scenario}, {uf}: rho={row["spearman_expense_votes"]}, n={row["complete_pairs"]}</title></circle>')
    elements.extend([
        '<rect x="330" y="550" width="12" height="12" fill="#2563eb"/><text x="348" y="561" font-family="sans-serif" font-size="12">Tratamento deduplicado</text>',
        '<rect x="640" y="550" width="12" height="12" fill="#f97316"/><text x="658" y="561" font-family="sans-serif" font-size="12">Todas as linhas</text>',
        '</svg>',
    ])
    path.write_text("".join(elements), encoding="utf-8")

def _svg_distributions(rows_deduplicated: list[dict[str, object]], rows_all_rows: list[dict[str, object]], path: Path) -> None:
    series = []
    for label, rows, field in (("Despesas — deduplicado", rows_deduplicated, "declared_expense_centavos"), ("Despesas — todas as linhas", rows_all_rows, "declared_expense_centavos"), ("Votos nominais válidos", rows_deduplicated, "valid_nominal_votes")):
        if field == "valid_nominal_votes":
            values = [int(row[field]) for row in rows if row["vote_observation"] != "absent"]
        else:
            values = [int(row[field]) for row in rows if row["expense_observation"] != "absent"]
        buckets = Counter(min(9, int(math.log10(1 + value / (100 if field != "valid_nominal_votes" else 1)) * 2)) for value in values)
        series.append((label, buckets))
    width, height = 900, 500
    left, top, plot_w, plot_h = 70, 55, 760, 350
    maximum = max((max(buckets.values(), default=0) for _, buckets in series), default=1)
    colors = ("#2563eb", "#f97316", "#16a34a")
    elements = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">', '<rect width="100%" height="100%" fill="white"/>', f'<text x="{width / 2}" y="28" text-anchor="middle" font-family="sans-serif" font-size="18">Distribuições exploratórias com zeros observados</text>']
    bar_w = plot_w / 10
    for index, (label, buckets) in enumerate(series):
        for bucket in range(10):
            value = buckets.get(bucket, 0)
            x = left + bucket * bar_w + index * bar_w / 4
            bar_h = value / maximum * plot_h
            elements.append(f'<rect x="{x:.2f}" y="{top + plot_h - bar_h:.2f}" width="{bar_w / 4:.2f}" height="{bar_h:.2f}" fill="{colors[index]}" opacity="0.8"><title>{html.escape(label)}: classe {bucket}, {value}</title></rect>')
    elements.extend([f'<line x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}" stroke="black"/>', f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" stroke="black"/>'])
    for index, (label, _) in enumerate(series):
        x = left + index * 180
        elements.append(f'<rect x="{x}" y="450" width="12" height="12" fill="{colors[index]}"/><text x="{x + 18}" y="461" font-family="sans-serif">{html.escape(label)}</text>')
    elements.append("</svg>")
    path.write_text("".join(elements), encoding="utf-8")


def _write_report(
    output_path: Path,
    metadata: dict,
    summary_rows: list[dict[str, object]],
    comparison_rows: list[dict[str, object]],
    uf_rows: list[dict[str, object]],
    cost_rows: list[dict[str, object]],
) -> None:
    total_deduplicated = next(
        row["total"] for row in summary_rows
        if row["scenario"] == SCENARIO_DEDUPLICATED and row["measure"].startswith("despesas")
    )
    total_all_rows = next(
        row["total"] for row in summary_rows
        if row["scenario"] == SCENARIO_ALL_ROWS and row["measure"].startswith("despesas")
    )
    changed = [
        row for row in comparison_rows
        if row["difference_all_rows_minus_deduplicated_centavos"] not in ("", 0)
    ]
    top_changes = sorted(
        changed,
        key=lambda row: int(row["difference_all_rows_minus_deduplicated_centavos"]),
        reverse=True,
    )[:10]
    cost_deduplicated = next(row for row in cost_rows if row["scenario"] == SCENARIO_DEDUPLICATED)
    cost_all_rows = next(row for row in cost_rows if row["scenario"] == SCENARIO_ALL_ROWS)
    uf_by_scenario = {
        scenario: {str(row["uf"]): row for row in uf_rows if row["scenario"] == scenario}
        for scenario in (SCENARIO_DEDUPLICATED, SCENARIO_ALL_ROWS)
    }
    ufs = sorted(set(uf_by_scenario[SCENARIO_DEDUPLICATED]) | set(uf_by_scenario[SCENARIO_ALL_ROWS]))
    spearman_deduplicated = [
        row for row in uf_by_scenario[SCENARIO_DEDUPLICATED].values()
        if row["spearman_expense_votes"] != ""
    ]
    spearman_all_rows = [
        row for row in uf_by_scenario[SCENARIO_ALL_ROWS].values()
        if row["spearman_expense_votes"] != ""
    ]
    complete_pair_difference = (
        int(cost_all_rows["expense_total_centavos_complete_pairs"])
        - int(cost_deduplicated["expense_total_centavos_complete_pairs"])
    )
    zero_vote_count = next(
        row["count_zero"] for row in summary_rows
        if row["measure"] == "votos_nominais_validos" and row["scenario"] == SCENARIO_DEDUPLICATED
    )
    absent_vote_count = next(
        row["count_absent"] for row in summary_rows
        if row["measure"] == "votos_nominais_validos" and row["scenario"] == SCENARIO_DEDUPLICATED
    )
    cost_candidate_count = f"{int(cost_deduplicated['candidate_count_with_cost']):,}".replace(",", ".")
    lines = [
        "# Relatório exploratório provisório — TSE 2022",
        "",
        "> **Validação de ingestão aprovada; protocolo 2022 definido em [Fixar o protocolo da análise financeira do piloto TSE 2022](https://github.com/dargmiguel/dinheiro-compra-votos/issues/11). Este artefato continua exploratório: ainda não usa o denominador oficial incluindo legenda, os controles definidos nem a análise secundária por sexo.**",
        "",
        "## População e medidas",
        "",
        f"Este recorte exploratório inclui candidaturas `APTO` (`CD_SITUACAO_CANDIDATURA = 12`) no snapshot posterior à eleição: **{metadata['population_included']}** de {metadata['candidate_rows_selected']} registros. `INAPTO` será levantado separadamente por tipo de prestação; este artefato não contém esse levantamento.",
        "",
        "A medida exibida é despesa contratada declarada no snapshot para prestações `Final`; não equivale a pagamento nem à dívida oficial. O voto aqui é o total nominal válido por candidato, não a participação sobre o total oficial válido da UF/cargo incluindo legenda. Ausências continuam ausências e zeros observados continuam zeros.",
        "",
        "## Tratamentos",
        "",
        "- **Tratamento deduplicado (principal):** uma ocorrência por grupo com igualdade nos 53 campos originais do TSE, no mesmo snapshot e membro de origem; campos de auditoria ficam fora da comparação.",
        "- **Todas as linhas (sensibilidade):** preservar todas as ocorrências `Final`.",
        "",
        "A deduplicação é uma escolha metodológica. Não há confirmação oficial de identidade econômica das repetições.",
        "",
        "## Inclusões, exclusões e ausências",
        "",
        f"- candidatos selecionados no snapshot: **{metadata['candidate_rows_selected']}**;",
        f"- população `APTO`: **{metadata['population_included']}**;",
        f"- fora por `INAPTO`: **{metadata['population_excluded_by_reason']['inapto']}**;",
        f"- linhas financeiras `Final` no recorte: **{metadata['expense_rows_selected_final_apto']}**;",
        f"- ocorrências excluídas do tratamento deduplicado: **{metadata['exact_repeat_rows_in_final_apto']}**;",
        f"- candidatos afetados pelas exclusões: **{metadata['candidates_affected_by_dedup_final_apto']}**.",
        "",
        "Os CSVs têm uma linha por candidato `APTO`, inclusive quando despesa ou votação estão ausentes. Ausência não foi transformada em zero.",
        "",
        "## Totais e diferença metodológica — recorte Final/APTO",
        "",
        f"- tratamento deduplicado: **{_money(total_deduplicated)}** em {metadata['expense_rows_selected_final_apto'] - metadata['exact_repeat_rows_in_final_apto']} linhas;",
        f"- todas as linhas: **{_money(total_all_rows)}** em {metadata['expense_rows_selected_final_apto']} linhas;",
        f"- diferença todas as linhas menos deduplicado: **{_money(total_all_rows - total_deduplicated)}**;",
        f"- candidatos com total financeiro diferente: **{len(changed)}** de {metadata['population_included']}.",
        "",
        "## Custo exploratório por voto nominal",
        "",
        "O custo é calculado somente para candidatos com despesa observada e votos nominais válidos maiores que zero. Despesa zero observada produz custo R$ 0,00; despesa ausente continua fora do quociente. Esta métrica não substitui a participação sobre o total oficial válido definido no protocolo.",
        "No CSV, os custos estão em reais por voto nominal e usam ponto decimal. O custo agregado é a soma das despesas dividida pela soma dos votos nos pares completos, não a média simples dos custos individuais.",
        "",
        "| Tratamento | Candidatos | Despesa completa | Votos nominais completos | Custo agregado | Mediana | P90 | P99 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
        f"| Deduplicado | {cost_candidate_count} | {_money(int(cost_deduplicated['expense_total_centavos_complete_pairs']))} | {cost_deduplicated['votes_total_complete_pairs']} | {_money(round(Decimal(cost_deduplicated['aggregate_cost_brl_per_vote']) * 100))} | {_money(round(Decimal(cost_deduplicated['median_cost_brl_per_vote']) * 100))} | {_money(round(Decimal(cost_deduplicated['p90_cost_brl_per_vote']) * 100))} | {_money(round(Decimal(cost_deduplicated['p99_cost_brl_per_vote']) * 100))} |",
        f"| Todas as linhas | {cost_candidate_count} | {_money(int(cost_all_rows['expense_total_centavos_complete_pairs']))} | {cost_all_rows['votes_total_complete_pairs']} | {_money(round(Decimal(cost_all_rows['aggregate_cost_brl_per_vote']) * 100))} | {_money(round(Decimal(cost_all_rows['median_cost_brl_per_vote']) * 100))} | {_money(round(Decimal(cost_all_rows['p90_cost_brl_per_vote']) * 100))} | {_money(round(Decimal(cost_all_rows['p99_cost_brl_per_vote']) * 100))} |",
        f"A diferença todas as linhas menos deduplicado nas despesas observadas do recorte `Final`/`APTO` é {_money(total_all_rows - total_deduplicated)}. Nos {cost_candidate_count} candidatos com votos positivos, a diferença é {_money(complete_pair_difference)}. Os {_money((total_all_rows - total_deduplicated) - complete_pair_difference)} restantes vêm de candidatos com votação observada igual a zero ({zero_vote_count}); votos ausentes: {absent_vote_count}.",
        "",
        "| SQ_CANDIDATO | Candidato | UF | Diferença: todas as linhas menos deduplicado | Relativa ao deduplicado | Repetições em todas as linhas |",
        "|---|---|---|---:|---:|---:|",
    ]
    for row in top_changes:
        relative = row["difference_relative_to_deduplicated"]
        relative_text = "" if relative == "" else f"{float(relative) * 100:.4f}%".replace(".", ",")
        difference = int(row["difference_all_rows_minus_deduplicated_centavos"])
        lines.append(
            f"| {row['sq_candidate']} | {row['candidate_name']} | {row['uf']} | "
            f"{_money(difference)} | {relative_text} | {row['exact_repeat_rows_all_rows_sensitivity']} |"
        )
    lines.extend([
        "",
        "## Associação exploratória entre despesas e votação nominal por UF",
        "",
        "Spearman é calculado dentro de cada UF entre candidatos com despesa e votação observadas. Zeros observados permanecem na amostra; apenas ausências são excluídas. O custo por voto não participa desta associação.",
        "",
        f"Cobertura: {len(spearman_deduplicated)} de {len(ufs)} UFs têm coeficiente definido para o tratamento deduplicado e {len(spearman_all_rows)} de {len(ufs)} para todas as linhas. A tabela informa os pares completos de cada UF.",
        "",
        "| UF | Pares deduplicado | Spearman deduplicado | Pares todas as linhas | Spearman todas as linhas |",
        "|---|---:|---:|---:|---:|",
    ])
    for uf in ufs:
        row_deduplicated = uf_by_scenario[SCENARIO_DEDUPLICATED].get(uf)
        row_all_rows = uf_by_scenario[SCENARIO_ALL_ROWS].get(uf)
        rho_deduplicated = "—" if row_deduplicated is None or row_deduplicated["spearman_expense_votes"] == "" else row_deduplicated["spearman_expense_votes"]
        rho_all_rows = "—" if row_all_rows is None or row_all_rows["spearman_expense_votes"] == "" else row_all_rows["spearman_expense_votes"]
        pairs_deduplicated = 0 if row_deduplicated is None else row_deduplicated["complete_pairs"]
        pairs_all_rows = 0 if row_all_rows is None else row_all_rows["complete_pairs"]
        lines.append(f"| {uf} | {pairs_deduplicated} | {rho_deduplicated} | {pairs_all_rows} | {rho_all_rows} |")
    lines.extend([
        "",
        "Coeficiente indefinido significa menos de dois pares ou variância nula. As correlações são descritivas, não causais, e não selecionam tratamento.",
        "",
        "## Distribuições e artefatos",
        "",
        "Os gráficos usam `log10(1 + x)` nos eixos somente para visualização; os CSVs mantêm valores, zeros e ausências originais. Pontos sem despesa ou voto não foram colocados como zero.",
        "",
        "- [Despesas versus votos — tratamento deduplicado](plots/exploratory_expense_vs_votes_deduplicated.svg)",
        "- [Despesas versus votos — todas as linhas](plots/exploratory_expense_vs_votes_all_rows.svg)",
        "- [Associação por UF — deduplicado e todas as linhas](plots/exploratory_uf_spearman_deduplicated_vs_all_rows.svg)",
        "- [Distribuições](plots/exploratory_distributions.svg)",
        "- [Totais por UF](plots/exploratory_uf_expense_totals.svg)",
        "- [Distribuições em CSV](exploratory_distributions.csv)",
        "- [Associações por UF em CSV](exploratory_uf_associations.csv)",
        "- [Dados por candidato](exploratory_candidates.csv)",
        "- [Comparação deduplicado versus todas as linhas](exploratory_deduplicated_vs_all_rows.csv)",
        "- [Custo por voto nominal por tratamento](exploratory_cost_per_vote.csv)",
        "",
        "## Limitações",
        "",
        "- `APTO` é a situação disponível no snapshot posterior à eleição; não reconstrói situação na data da votação.",
        "- `Final` é identificada pelo campo `TP_PRESTACAO_CONTAS`; não se afirma que seja a última entrega recepcionada com sucesso.",
        "- O ZIP congelado contém arquivos de despesas pagas, mas este artefato não os integra. A integração paga é complementar e não bloqueia a análise contratada.",
        "- Este artefato usa voto nominal por candidato e não implementa o denominador oficial por UF/cargo incluindo legenda, os controles definidos nem a análise secundária por sexo.",
        "- A deduplicação é metodológica e não confirma identidade econômica; diferenças não são chamadas de desperdício ou gasto indevido. Este relatório permanece exploratório e não é o `analytical_base.csv`.",
        "",
        "Todos os artefatos têm prefixo `exploratory_` ou ficam em `plots/`; permanecem marcados como `exploratory_only`.",
    ])
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_exploratory_scenarios(manifest_path: Path, validation_path: Path, output_dir: Path) -> dict:
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    validation = _load_validation(Path(validation_path))
    output_dir = Path(output_dir)
    if any(part.casefold() == "derived" for part in output_dir.parts):
        raise ValueError("artefatos exploratórios exigem diretório próprio, fora de data/derived")
    output_dir.mkdir(parents=True, exist_ok=True)
    plots_dir = output_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    for filename in (*GENERATED_FILES, *OBSOLETE_FILES):
        path = output_dir / filename
        if path.exists():
            path.unlink()
    for path in plots_dir.glob("exploratory_*.svg"):
        path.unlink()

    candidates_all = _load_candidates(manifest)
    candidates = {key: value for key, value in candidates_all.items() if value["candidate_status_code"] == "12"}
    excluded = Counter((value["candidate_status"] or value["candidate_status_code"] or "ausente").casefold() for value in candidates_all.values() if value["candidate_status_code"] != "12")
    validation_database = Path(validation.get("database", "")) if validation.get("database") else Path(validation_path).parent / "pilot.sqlite"
    votes = _load_votes(validation, Path(validation_path), candidates)
    (scenario_data, expense_counters) = _load_final_expenses(manifest, candidates, validation_database)
    deduplicated, all_rows_sensitivity = scenario_data
    rows_deduplicated = _scenario_rows(candidates, deduplicated, votes)
    rows_all_rows = _scenario_rows(candidates, all_rows_sensitivity, votes)
    comparison = _comparison_rows(rows_deduplicated, rows_all_rows)
    summary = _summary_rows(rows_deduplicated, SCENARIO_DEDUPLICATED) + _summary_rows(rows_all_rows, SCENARIO_ALL_ROWS)
    cost_rows = _cost_rows(rows_deduplicated, SCENARIO_DEDUPLICATED) + _cost_rows(rows_all_rows, SCENARIO_ALL_ROWS)
    uf_deduplicated = _uf_rows(rows_deduplicated, SCENARIO_DEDUPLICATED)
    uf_all_rows = _uf_rows(rows_all_rows, SCENARIO_ALL_ROWS)
    uf_summary = uf_deduplicated + uf_all_rows

    metadata = {
        "schema_version": 3,
        "status": "exploratory_only",
        "validation_status": validation.get("status"),
        "analysis_protocol_status": "specified_pending_implementation",
        "not_approved": True,
        "manifest_id": manifest.get("manifest_id"),
        "population_definition": "candidaturas APTO no snapshot posterior à eleição; não reconstrói validade no dia do pleito",
        "candidate_rows_selected": len(candidates_all),
        "population_included": len(candidates),
        "population_excluded_by_reason": dict(excluded),
        "expense_measure": "VR_DESPESA_CONTRATADA declarada em prestações Final; despesas pagas são complementares e não estão integradas neste artefato",
        "vote_measure": "QT_VOTOS_NOMINAIS_VALIDOS por candidato; este artefato não aplica o denominador oficial incluindo legenda",
        "absence_rule": "ausência permanece ausente; zero observado permanece zero observado",
        "scenario_deduplicated": SCENARIO_DEDUPLICATED,
        "scenario_all_rows": SCENARIO_ALL_ROWS,
        "deduplication_rule": "uma ocorrência por grupo igual nos 53 campos originais, dentro do mesmo snapshot e membro; campos de auditoria excluídos da comparação",
        "methodological_uncertainty": "A regra é uma escolha metodológica; não há confirmação oficial de identidade econômica das repetições.",
        **expense_counters,
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }
    _write_csv(output_dir / "exploratory_candidates.csv", list(rows_deduplicated[0].keys()) if rows_deduplicated else [], rows_deduplicated)
    _write_csv(output_dir / "exploratory_deduplicated_primary.csv", list(rows_deduplicated[0].keys()) if rows_deduplicated else [], rows_deduplicated)
    _write_csv(output_dir / "exploratory_all_rows_sensitivity.csv", list(rows_all_rows[0].keys()) if rows_all_rows else [], rows_all_rows)
    _write_csv(output_dir / "exploratory_deduplicated_vs_all_rows.csv", list(comparison[0].keys()) if comparison else [], comparison)
    _write_csv(output_dir / "exploratory_cost_per_vote.csv", list(cost_rows[0].keys()) if cost_rows else [], cost_rows)
    _write_csv(output_dir / "exploratory_distributions.csv", list(summary[0].keys()) if summary else [], summary)
    _write_csv(output_dir / "exploratory_uf_associations.csv", list(uf_summary[0].keys()) if uf_summary else [], uf_summary)
    (output_dir / "exploratory_metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _svg_scatter(rows_deduplicated, "declared_expense_centavos", plots_dir / "exploratory_expense_vs_votes_deduplicated.svg", "Tratamento deduplicado — despesas declaradas versus votos nominais")
    _svg_scatter(rows_all_rows, "declared_expense_centavos", plots_dir / "exploratory_expense_vs_votes_all_rows.svg", "Todas as linhas — despesas declaradas versus votos nominais")
    _svg_distributions(rows_deduplicated, rows_all_rows, plots_dir / "exploratory_distributions.svg")
    _svg_uf_totals(uf_deduplicated, uf_all_rows, plots_dir / "exploratory_uf_expense_totals.svg")
    _write_report(output_dir / "exploratory_report.md", metadata, summary, comparison, uf_summary, cost_rows)
    _svg_uf_spearman(uf_deduplicated, uf_all_rows, plots_dir / "exploratory_uf_spearman_deduplicated_vs_all_rows.svg")
    return metadata
