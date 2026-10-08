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

SCENARIO_A = "A_preservar_todas_as_linhas"
SCENARIO_B = "B_remover_repeticoes_completas_exatas"
GENERATED_FILES = (
    "exploratory_metadata.json",
    "exploratory_candidates.csv",
    "exploratory_scenario_a_preserve_all.csv",
    "exploratory_scenario_b_remove_exact_repeats.csv",
    "exploratory_scenario_comparison.csv",
    "exploratory_distributions.csv",
    "exploratory_uf_associations.csv",
    "exploratory_report.md",
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
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


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


def _load_validation(validation_path: Path) -> dict:
    validation = json.loads(Path(validation_path).read_text(encoding="utf-8"))
    if validation.get("status") != "blocked":
        raise ValueError("exploração exige uma validação bloqueada; não substitui uma base aprovada")
    fatal_counts = validation.get("fatal_counts", {})
    unexpected = {key: value for key, value in fatal_counts.items() if value and key != "duplicate_expense_rows"}
    if unexpected:
        raise ValueError(f"exploração recusada: há falhas críticas além de repetições exatas: {unexpected}")
    if not fatal_counts.get("duplicate_expense_rows"):
        raise ValueError("exploração exige o bloqueio por duplicate_expense_rows no snapshot")
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


def _load_final_expenses(manifest: dict, candidates: dict[str, dict[str, str]]) -> tuple[dict[str, dict[str, int]], dict[str, int]]:
    preserve = _empty_scenario(candidates)
    remove = _empty_scenario(candidates)
    seen_signatures = sqlite3.connect(":memory:")
    seen_signatures.execute("CREATE TABLE seen_signatures (signature TEXT PRIMARY KEY)")
    counters = Counter()
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
        preserve[candidate_id]["expense_row_count"] += 1
        preserve[candidate_id]["declared_expense_centavos"] += amount_centavos
        signature = _row_signature(row)
        inserted = seen_signatures.execute("INSERT OR IGNORE INTO seen_signatures VALUES (?)", (signature,)).rowcount
        if inserted:
            remove[candidate_id]["expense_row_count"] += 1
            remove[candidate_id]["declared_expense_centavos"] += amount_centavos
        else:
            preserve[candidate_id]["exact_repeat_rows"] += 1
            counters["exact_repeat_rows_in_final_apto"] += 1
    seen_signatures.close()
    return (preserve, remove), dict(counters)


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
        })
    return rows


def _comparison_rows(rows_a: list[dict[str, object]], rows_b: list[dict[str, object]]) -> list[dict[str, object]]:
    rows = []
    for row_a, row_b in zip(rows_a, rows_b):
        amount_a = int(row_a["declared_expense_centavos"]) if row_a["declared_expense_centavos"] != "" else None
        amount_b = int(row_b["declared_expense_centavos"]) if row_b["declared_expense_centavos"] != "" else None
        delta = amount_a - amount_b if amount_a is not None and amount_b is not None else None
        relative = (delta / amount_a) if delta is not None and amount_a else None
        rows.append({
            "sq_candidate": row_a["sq_candidate"],
            "uf": row_a["uf"],
            "candidate_number": row_a["candidate_number"],
            "candidate_name": row_a["candidate_name"],
            "expense_a_centavos": "" if amount_a is None else amount_a,
            "expense_b_centavos": "" if amount_b is None else amount_b,
            "difference_centavos": "" if delta is None else delta,
            "difference_relative_to_a": "" if relative is None else f"{relative:.8f}",
            "exact_repeat_rows_a": row_a["exact_repeat_rows"],
            "vote_observation": row_a["vote_observation"],
            "valid_nominal_votes": row_a["valid_nominal_votes"],
        })
    return rows


def _summary_rows(rows: list[dict[str, object]], scenario_name: str) -> list[dict[str, object]]:
    expenses = [int(row["declared_expense_centavos"]) for row in rows if row["expense_observation"] != "absent"]
    votes = [int(row["valid_nominal_votes"]) for row in rows if row["vote_observation"] != "absent"]
    return [
        {"scenario": scenario_name, "measure": "despesas_contratadas_declaradas_centavos", "count_observed": len(expenses), "count_zero": sum(value == 0 for value in expenses), "count_absent": sum(row["expense_observation"] == "absent" for row in rows), "total": sum(expenses), "p50": _quantile(expenses, 0.50), "p90": _quantile(expenses, 0.90), "p99": _quantile(expenses, 0.99)},
        {"scenario": scenario_name, "measure": "votos_nominais_validos", "count_observed": len(votes), "count_zero": sum(value == 0 for value in votes), "count_absent": sum(row["vote_observation"] == "absent" for row in rows), "total": sum(votes), "p50": _quantile(votes, 0.50), "p90": _quantile(votes, 0.90), "p99": _quantile(votes, 0.99)},
    ]


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


def _svg_uf_totals(rows_a: list[dict[str, object]], rows_b: list[dict[str, object]], path: Path) -> None:
    by_uf = {row["uf"]: {"a": int(row["expense_total_centavos"]), "b": int(row["expense_total_centavos"])} for row in []}
    totals_a = {row["uf"]: int(row["expense_total_centavos"]) for row in rows_a}
    totals_b = {row["uf"]: int(row["expense_total_centavos"]) for row in rows_b}
    ufs = sorted(set(totals_a) | set(totals_b))
    width, height = 1100, 560
    left, top, plot_w, plot_h = 55, 45, 1000, 410
    maximum = max([*totals_a.values(), *totals_b.values(), 1])
    group_w = plot_w / max(len(ufs), 1)
    elements = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">', '<rect width="100%" height="100%" fill="white"/>', f'<text x="{width / 2}" y="25" text-anchor="middle" font-family="sans-serif" font-size="18">Despesas declaradas por UF — cenários exploratórios</text>']
    for index, uf in enumerate(ufs):
        x = left + index * group_w
        for offset, value, color in ((group_w * 0.18, totals_a.get(uf, 0), "#2563eb"), (group_w * 0.52, totals_b.get(uf, 0), "#f97316")):
            bar_h = value / maximum * plot_h
            elements.append(f'<rect x="{x + offset:.2f}" y="{top + plot_h - bar_h:.2f}" width="{group_w * 0.24:.2f}" height="{bar_h:.2f}" fill="{color}"><title>{html.escape(uf)}: {_money(value)}</title></rect>')
        elements.append(f'<text x="{x + group_w / 2:.2f}" y="{top + plot_h + 18}" text-anchor="middle" font-family="sans-serif" font-size="11">{uf}</text>')
    elements.extend([f'<line x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}" stroke="black"/>', '<rect x="850" y="500" width="12" height="12" fill="#2563eb"/><text x="868" y="511" font-family="sans-serif">A — preservar</text>', '<rect x="980" y="500" width="12" height="12" fill="#f97316"/><text x="998" y="511" font-family="sans-serif">B — remover exatas</text></svg>'])
    path.write_text("".join(elements), encoding="utf-8")


def _svg_distributions(rows_a: list[dict[str, object]], rows_b: list[dict[str, object]], path: Path) -> None:
    series = []
    for label, rows, field in (("A despesas", rows_a, "declared_expense_centavos"), ("B despesas", rows_b, "declared_expense_centavos"), ("Votos", rows_a, "valid_nominal_votes")):
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
) -> None:
    total_a = next(row["total"] for row in summary_rows if row["scenario"] == SCENARIO_A and row["measure"].startswith("despesas"))
    total_b = next(row["total"] for row in summary_rows if row["scenario"] == SCENARIO_B and row["measure"].startswith("despesas"))
    changed = [row for row in comparison_rows if row["difference_centavos"] not in ("", 0)]
    top_changes = sorted(changed, key=lambda row: int(row["difference_centavos"]), reverse=True)[:10]
    lines = [
        "# Relatório exploratório provisório — TSE 2022",
        "",
        "> **EXPLORATÓRIO / PROVISÓRIO. Não é base aprovada e não substitui `validation.json`.**",
        "",
        "## População e medidas",
        "",
        f"A população contém candidatos `APTO` no snapshot de candidaturas consultado após a eleição: **{metadata['population_included']}** de {metadata['candidate_rows_selected']} registros. `INAPTO` ficou fora da população principal; não foi convertido em ausência de gasto ou voto.",
        "",
        "A medida financeira é **despesas contratadas declaradas no snapshot**, restrita a entregas `Final`. Ela não é apresentada como equivalente a `Gastos Financeiros`. Ausências continuam ausências e zeros observados continuam zeros. A votação é `QT_VOTOS_NOMINAIS_VALIDOS`.",
        "",
        "## Cenários",
        "",
        "- **A — preservar todas as linhas:** mantém toda linha `Final` observada para candidatos `APTO`.",
        "- **B — remover repetições completas exatas:** mantém a primeira ocorrência de cada assinatura completa e remove apenas ocorrências posteriores iguais, exclusivamente para comparação.",
        "",
        "Nenhum cenário foi escolhido como correto. Estabilidade entre A e B mede sensibilidade do resultado ao tratamento, não prova de validade de qualquer tratamento.",
        "",
        "## Inclusões, exclusões e ausências",
        "",
        f"- candidatos selecionados no snapshot: **{metadata['candidate_rows_selected']}**;",
        f"- população `APTO`: **{metadata['population_included']}**;",
        f"- fora por `INAPTO`: **{metadata['population_excluded_by_reason']['inapto']}**;",
        f"- linhas financeiras `Final` para a população: **{metadata['expense_rows_selected_final_apto']}**;",
        f"- repetições completas exatas no recorte financeiro: **{metadata['exact_repeat_rows_in_final_apto']}**.",
        "",
        "Os CSVs de cenário têm uma linha por candidato `APTO`, inclusive quando a despesa ou a votação está ausente. Ausente não foi transformado em zero.",
        "",
        "## Totais e mudança entre cenários",
        "",
        f"- cenário A: **{_money(total_a)}**;",
        f"- cenário B: **{_money(total_b)}**;",
        f"- diferença diagnóstica: **{_money(total_a - total_b)}**;",
        f"- candidatos com valor financeiro diferente: **{len(changed)}** de {metadata['population_included']}.",
        "",
        "| SQ_CANDIDATO | Candidato | UF | Diferença | Relativa a A | Repetições exatas |",
        "|---|---|---|---:|---:|---:|",
    ]
    for row in top_changes:
        relative = row["difference_relative_to_a"]
        relative_text = "" if relative == "" else f"{float(relative) * 100:.4f}%".replace(".", ",")
        lines.append(f"| {row['sq_candidate']} | {row['candidate_name']} | {row['uf']} | {_money(int(row['difference_centavos']))} | {relative_text} | {row['exact_repeat_rows_a']} |")
    lines.extend([
        "",
        "## Distribuições e associações",
        "",
        "Os gráficos usam transformação `log10(1 + x)` somente nos eixos para tornar valores muito diferentes visíveis; os arquivos CSV mantêm os valores originais, zeros e ausências. Pontos sem despesa ou voto não foram colocados no gráfico como zero.",
        "",
        "- [Despesas versus votos — cenário A](plots/exploratory_expense_vs_votes_a.svg)",
        "- [Despesas versus votos — cenário B](plots/exploratory_expense_vs_votes_b.svg)",
        "- [Distribuições](plots/exploratory_distributions.svg)",
        "- [Totais por UF](plots/exploratory_uf_expense_totals.svg)",
        "- [Distribuições em CSV](exploratory_distributions.csv)",
        "- [Associações descritivas por UF em CSV](exploratory_uf_associations.csv)",
        "",
        "A associação por UF é descritiva: correlação de Pearson entre despesas observadas e votos observados, incluindo zeros observados e excluindo somente pares com ausência. Não é estimativa causal e não foi usada para escolher cenário.",
        "",
        "## Limitações",
        "",
        "- A população `APTO` é a situação disponível no snapshot posterior à eleição; não representa uma reconstrução histórica da situação no dia da votação.",
        "- A entrega `Final` foi identificada pelo campo textual `TP_PRESTACAO_CONTAS`; o comando não afirma que ela seja a última entrega recebida com sucesso.",
        "- A medida não inclui despesas pagas, dívida líquida, estimáveis ou regras de DRD.",
        "- A duplicidade completa é um sinal textual; o cenário B não é uma decisão de deduplicação.",
        "- Os artefatos são provisórios e não podem ser usados como `analytical_base.csv`.",
        "",
        "## Arquivos",
        "",
        "Todos os artefatos deste diretório têm prefixo `exploratory_` ou estão sob `plots/` e carregam a marca `exploratory_only` no manifesto.",
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
    for filename in GENERATED_FILES:
        path = output_dir / filename
        if path.exists():
            path.unlink()
    for path in plots_dir.glob("exploratory_*.svg"):
        path.unlink()

    candidates_all = _load_candidates(manifest)
    candidates = {key: value for key, value in candidates_all.items() if value["candidate_status_code"] == "12"}
    excluded = Counter((value["candidate_status"] or value["candidate_status_code"] or "ausente").casefold() for value in candidates_all.values() if value["candidate_status_code"] != "12")
    votes = _load_votes(validation, Path(validation_path), candidates)
    (scenario_data, expense_counters) = _load_final_expenses(manifest, candidates)
    preserve, remove = scenario_data
    rows_a = _scenario_rows(candidates, preserve, votes)
    rows_b = _scenario_rows(candidates, remove, votes)
    comparison = _comparison_rows(rows_a, rows_b)
    summary = _summary_rows(rows_a, SCENARIO_A) + _summary_rows(rows_b, SCENARIO_B)
    uf_a = _uf_rows(rows_a, SCENARIO_A)
    uf_b = _uf_rows(rows_b, SCENARIO_B)
    uf_summary = uf_a + uf_b

    metadata = {
        "schema_version": 1,
        "status": "exploratory_only",
        "approval_status": "blocked",
        "not_approved": True,
        "manifest_id": manifest.get("manifest_id"),
        "validation_status": validation.get("status"),
        "population_definition": "candidatos com CD_SITUACAO_CANDIDATURA = 12 (APTO) no snapshot posterior à eleição",
        "candidate_rows_selected": len(candidates_all),
        "population_included": len(candidates),
        "population_excluded_by_reason": dict(excluded),
        "expense_measure": "despesas contratadas declaradas no snapshot; TP_PRESTACAO_CONTAS = Final; não afirmar equivalência com Gastos Financeiros",
        "vote_measure": "QT_VOTOS_NOMINAIS_VALIDOS",
        "absence_rule": "ausência permanece ausente; zero observado permanece zero observado",
        "scenario_a": "preservar todas as linhas Final",
        "scenario_b": "remover somente repetições completas exatas, mantendo a primeira ocorrência",
        **expense_counters,
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }
    _write_csv(output_dir / "exploratory_candidates.csv", list(rows_a[0].keys()) if rows_a else [], rows_a)
    _write_csv(output_dir / "exploratory_scenario_a_preserve_all.csv", list(rows_a[0].keys()) if rows_a else [], rows_a)
    _write_csv(output_dir / "exploratory_scenario_b_remove_exact_repeats.csv", list(rows_b[0].keys()) if rows_b else [], rows_b)
    _write_csv(output_dir / "exploratory_scenario_comparison.csv", list(comparison[0].keys()) if comparison else [], comparison)
    _write_csv(output_dir / "exploratory_distributions.csv", list(summary[0].keys()) if summary else [], summary)
    _write_csv(output_dir / "exploratory_uf_associations.csv", list(uf_summary[0].keys()) if uf_summary else [], uf_summary)
    (output_dir / "exploratory_metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _svg_scatter(rows_a, "declared_expense_centavos", plots_dir / "exploratory_expense_vs_votes_a.svg", "Cenário A — despesas declaradas versus votos")
    _svg_scatter(rows_b, "declared_expense_centavos", plots_dir / "exploratory_expense_vs_votes_b.svg", "Cenário B — despesas declaradas versus votos")
    _svg_distributions(rows_a, rows_b, plots_dir / "exploratory_distributions.svg")
    _svg_uf_totals(uf_a, uf_b, plots_dir / "exploratory_uf_expense_totals.svg")
    _write_report(output_dir / "exploratory_report.md", metadata, summary, comparison, uf_summary)
    return metadata
