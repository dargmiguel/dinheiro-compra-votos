from __future__ import annotations

import csv
import io
import json
import zipfile
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
REFERENCE = REPORTS / "tse-2022-funding-source-candidates.csv"
BASE = ROOT / "data/derived/2022/analytical_base.csv"
RECUT = REPORTS / "tse-2022-funding-source-recut.json"
SUMMARY = REPORTS / "tse-2022-funding-source-summary.csv"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def cents(row: dict[str, str], field: str) -> int:
    value = row.get(field, "")
    return int(value) if value else 0


def write_csv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def median(values: list[int]) -> Decimal:
    if not values:
        return Decimal(0)
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return Decimal(ordered[middle])
    return Decimal(ordered[middle - 1] + ordered[middle]) / 2


def pct(numerator: int, denominator: int) -> float:
    return round(100 * numerator / denominator, 4) if denominator else 0.0


def currency(centavos: int) -> str:
    whole, fractional = divmod(centavos, 100)
    value = f"{whole:,}.{fractional:02d}"
    return "R$ " + value.replace(",", "X").replace(".", ",").replace("X", ".")


def count_fmt(value: int) -> str:
    return f"{value:,}".replace(",", ".")


def main() -> None:
    candidate_rows = read_csv(REFERENCE)
    base_rows = read_csv(BASE)
    candidate_by_id = {row["sq_candidate"]: row for row in candidate_rows}
    base_by_id = {row["sq_candidate"]: row for row in base_rows}
    assert len(candidate_by_id) == len(candidate_rows) == 9204
    assert set(candidate_by_id) <= set(base_by_id)
    ids = set(candidate_by_id)
    recut = json.loads(RECUT.read_text(encoding="utf-8"))
    summary_rows = read_csv(SUMMARY)
    source_counts: dict[str, set[str]] = {key: set() for key in ("public", "private", "unclassified")}
    financial_row_counts: dict[str, set[str]] = {key: set() for key in source_counts}
    financial_record_counts = {key: 0 for key in source_counts}
    receipt_row_count = 0
    financial_receipt_row_count = 0
    archive = ROOT / Path(recut["source_archive"])
    class_codes = {code: "public" for code in recut["classification"]["public_source_codes"]}
    class_codes.update({code: "private" for code in recut["classification"]["private_source_codes"]})
    selected_members = recut["source_members"]["receipts_selected"]
    with zipfile.ZipFile(archive) as source_zip:
        for member in selected_members:
            with source_zip.open(member) as raw:
                reader = csv.DictReader(io.TextIOWrapper(raw, encoding="latin-1", newline=""), delimiter=";")
                for source_row in reader:
                    if source_row.get("AA_ELEICAO") != "2022" or source_row.get("ST_TURNO") != "1":
                        continue
                    if (source_row.get("TP_PRESTACAO_CONTAS") or "").strip().casefold() != "final":
                        continue
                    if source_row.get("CD_CARGO") != "6":
                        continue
                    candidate_id = (source_row.get("SQ_CANDIDATO") or "").strip()
                    if candidate_id not in ids:
                        continue
                    source_class = class_codes.get((source_row.get("CD_FONTE_RECEITA") or "").strip(), "unclassified")
                    source_counts[source_class].add(candidate_id)
                    receipt_row_count += 1
                    if (source_row.get("CD_NATUREZA_RECEITA") or "").strip() == "1":
                        financial_row_counts[source_class].add(candidate_id)
                        financial_record_counts[source_class] += 1
                        financial_receipt_row_count += 1
    assert receipt_row_count == recut["source_members"]["receipt_rows_linked_to_reference_candidates"] == 99242
    assert {key: len(value) for key, value in source_counts.items()} == {"public": 8106, "private": 5460, "unclassified": 421}
    assert {key: len(value) for key, value in financial_row_counts.items()} == {"public": 7713, "private": 3955, "unclassified": 421}
    financial_covered_ids = set().union(*financial_row_counts.values())
    assert len(financial_covered_ids) == 8858
    assert all(row.get("receipt_has_rows", "").lower() == "true" for row in candidate_rows)

    groups: dict[tuple[str, str], list[str]] = defaultdict(list)
    for candidate_id in ids:
        base = base_by_id[candidate_id]
        sex = base.get("gender") or "NÃO INFORMADO"
        race = base.get("race") or "NÃO INFORMADO"
        groups[("sexo", sex)].append(candidate_id)
        groups[("raça/cor", race)].append(candidate_id)
    groups[("sexo", "TODOS")].extend(ids)
    groups[("raça/cor", "TODOS")].extend(ids)
    groups[("raça/cor", "PRETAS + PARDAS")].extend(
        candidate_id for candidate_id in ids if base_by_id[candidate_id].get("race") in {"PRETA", "PARDA"}
    )

    group_fields = [
        "group_type", "group_value", "candidate_count", "reference_population_n", "reference_population_coverage_pct",
        "receipt_rows_candidates", "receipt_row_coverage_pct", "financial_receipt_candidates",
        "financial_receipt_coverage_pct", "no_financial_receipt_candidates",
        "expense_observed_candidates", "expense_coverage_pct", "election_result_candidates",
        "election_result_coverage_pct", "receipt_all_flow_zero_candidates",
        "public_source_row_candidates", "public_source_coverage_pct", "public_source_absent_candidates",
        "private_source_row_candidates", "private_source_coverage_pct", "private_source_absent_candidates",
        "unclassified_source_row_candidates", "financial_public_row_candidates", "financial_public_coverage_pct",
        "financial_public_absent_candidates", "financial_public_absent_in_covered_candidates",
        "financial_private_row_candidates", "financial_private_coverage_pct", "financial_private_absent_candidates",
        "financial_private_absent_in_covered_candidates", "financial_unclassified_row_candidates",
        "financial_receipts_total_centavos", "financial_receipts_median_centavos",
        "public_financial_total_centavos", "public_financial_median_centavos",
        "public_financial_zero_amount_with_financial_row_candidates",
        "other_resources_financial_total_centavos", "other_resources_financial_median_centavos",
        "other_resources_financial_zero_amount_with_financial_row_candidates",
        "unclassified_financial_total_centavos", "contracted_expenses_total_centavos",
        "contracted_expenses_median_centavos", "contracted_expense_zero_candidates",
        "elected_candidates", "elected_denominator", "elected_pct", "small_group_n_lt_30",
    ]
    group_output: list[dict[str, object]] = []
    for (kind, label), members in sorted(groups.items()):
        member_ids = sorted(members)
        member_set = set(member_ids)
        member_ref = [candidate_by_id[cid] for cid in member_ids]
        member_base = [base_by_id[cid] for cid in member_ids]
        public_amount = {cid: cents(candidate_by_id[cid], "receipt_public_financial_centavos") for cid in member_ids}
        private_amount = {cid: cents(candidate_by_id[cid], "receipt_private_financial_centavos") for cid in member_ids}
        unclassified_amount = {cid: cents(candidate_by_id[cid], "receipt_unclassified_financial_centavos") for cid in member_ids}
        expenses = [cents(row, "contracted_expense_centavos") for row in member_ref]
        elected = sum(row.get("candidate_total_status_code") in {"2", "3"} for row in member_base)
        public_ids = source_counts["public"] & member_set
        private_ids = source_counts["private"] & member_set
        unclassified_ids = source_counts["unclassified"] & member_set
        financial_ids = set().union(*financial_row_counts.values()) & member_set
        public_financial_ids = financial_row_counts["public"] & member_set
        private_financial_ids = financial_row_counts["private"] & member_set
        unclassified_financial_ids = financial_row_counts["unclassified"] & member_set
        public_median_population = sorted(financial_ids)
        total_financial_values = [
            public_amount[cid] + private_amount[cid] + unclassified_amount[cid]
            for cid in public_median_population
        ]
        public_financial_values = [public_amount[cid] for cid in public_median_population]
        private_financial_values = [private_amount[cid] for cid in public_median_population]
        public_zero = sum(public_amount[cid] == 0 for cid in public_financial_ids)
        private_zero = sum(private_amount[cid] == 0 for cid in private_financial_ids)
        group_output.append({
            "group_type": kind, "group_value": label, "candidate_count": len(member_ids),
            "reference_population_n": len(ids), "reference_population_coverage_pct": pct(len(member_ids), len(ids)),
            "receipt_rows_candidates": sum(candidate_by_id[cid].get("receipt_has_rows", "").lower() == "true" for cid in member_ids),
            "receipt_row_coverage_pct": pct(len(member_ids), len(member_ids)),
            "financial_receipt_candidates": len(financial_ids),
            "financial_receipt_coverage_pct": pct(len(financial_ids), len(member_ids)),
            "no_financial_receipt_candidates": len(member_ids) - len(financial_ids),
            "expense_observed_candidates": sum(candidate_by_id[cid].get("contracted_expense_centavos", "") != "" for cid in member_ids),
            "expense_coverage_pct": pct(len(member_ids), len(member_ids)),
            "election_result_candidates": sum(row.get("candidate_total_status_code") in {"2", "3", "4", "5"} for row in member_base),
            "election_result_coverage_pct": pct(len(member_ids), len(member_ids)),
            "receipt_all_flow_zero_candidates": sum(cents(candidate_by_id[cid], "receipt_total_centavos") == 0 for cid in member_ids),
            "public_source_row_candidates": len(public_ids), "public_source_coverage_pct": pct(len(public_ids), len(member_ids)),
            "public_source_absent_candidates": len(member_ids) - len(public_ids),
            "private_source_row_candidates": len(private_ids), "private_source_coverage_pct": pct(len(private_ids), len(member_ids)),
            "private_source_absent_candidates": len(member_ids) - len(private_ids),
            "unclassified_source_row_candidates": len(unclassified_ids),
            "financial_public_row_candidates": len(public_financial_ids),
            "financial_public_coverage_pct": pct(len(public_financial_ids), len(member_ids)),
            "financial_public_absent_candidates": len(member_ids) - len(public_financial_ids),
            "financial_public_absent_in_covered_candidates": len(financial_ids - public_financial_ids),
            "financial_private_row_candidates": len(private_financial_ids),
            "financial_private_coverage_pct": pct(len(private_financial_ids), len(member_ids)),
            "financial_private_absent_candidates": len(member_ids) - len(private_financial_ids),
            "financial_private_absent_in_covered_candidates": len(financial_ids - private_financial_ids),
            "financial_unclassified_row_candidates": len(unclassified_financial_ids),
            "financial_receipts_total_centavos": sum(public_amount.values()) + sum(private_amount.values()) + sum(unclassified_amount.values()),
            "financial_receipts_median_centavos": median(total_financial_values) if total_financial_values else "",
            "public_financial_total_centavos": sum(public_amount.values()),
            "public_financial_median_centavos": median(public_financial_values) if public_financial_values else "",
            "public_financial_zero_amount_with_financial_row_candidates": public_zero,
            "other_resources_financial_total_centavos": sum(private_amount.values()),
            "other_resources_financial_median_centavos": median(private_financial_values) if private_financial_values else "",
            "other_resources_financial_zero_amount_with_financial_row_candidates": private_zero,
            "unclassified_financial_total_centavos": sum(unclassified_amount.values()),
            "contracted_expenses_total_centavos": sum(expenses), "contracted_expenses_median_centavos": median(expenses),
            "contracted_expense_zero_candidates": sum(value == 0 for value in expenses),
            "elected_candidates": elected, "elected_denominator": len(member_ids), "elected_pct": pct(elected, len(member_ids)),
            "small_group_n_lt_30": len(member_ids) < 30,
        })
    race_categories = {row["group_value"] for row in group_output if row["group_type"] == "raça/cor"}
    assert {"BRANCA", "PRETA", "PARDA", "AMARELA", "INDÍGENA", "NÃO INFORMADO", "NÃO DIVULGÁVEL", "PRETAS + PARDAS", "TODOS"} <= race_categories
    assert sum(row["elected_candidates"] for row in group_output if row["group_type"] == "sexo" and row["group_value"] != "TODOS") == 510
    write_csv(REPORTS / "tse-2022-financial-distribution-by-group.csv", group_fields, group_output)

    party_members: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in candidate_rows:
        party_members[row.get("party_abbrev") or "NÃO INFORMADO"].append(row)
    party_fields = ["party_abbrev", "candidate_count", "reference_population_n", "candidate_coverage_pct", "contracted_expenses_total_centavos", "contracted_expenses_median_centavos", "contracted_expense_zero_candidates", "small_group_n_lt_30", "expense_subject"]
    party_output = []
    for party, members in sorted(party_members.items()):
        amounts = [cents(row, "contracted_expense_centavos") for row in members]
        party_output.append({"party_abbrev": party, "candidate_count": len(members), "reference_population_n": len(ids), "candidate_coverage_pct": pct(len(members), len(ids)), "contracted_expenses_total_centavos": sum(amounts), "contracted_expenses_median_centavos": median(amounts), "contracted_expense_zero_candidates": sum(value == 0 for value in amounts), "small_group_n_lt_30": len(members) < 30, "expense_subject": "Candidatos; não é orçamento/despesa de diretório partidário"})
    assert sum(int(row["candidate_count"]) for row in party_output) == len(ids)
    assert sum(int(row["contracted_expenses_total_centavos"]) for row in party_output) == sum(cents(row, "contracted_expense_centavos") for row in candidate_rows)
    write_csv(REPORTS / "tse-2022-financial-distribution-by-party.csv", party_fields, party_output)

    summary_by_key = {(row["flow"], row["source_class"]): row for row in summary_rows}
    total_receipts = sum(cents(row, "receipt_total_centavos") for row in candidate_rows)
    financial_public = sum(cents(row, "receipt_public_financial_centavos") for row in candidate_rows)
    financial_private = sum(cents(row, "receipt_private_financial_centavos") for row in candidate_rows)
    financial_unclassified = sum(cents(row, "receipt_unclassified_financial_centavos") for row in candidate_rows)
    expense_total = sum(cents(row, "contracted_expense_centavos") for row in candidate_rows)
    payment_total = sum(cents(row, "payment_total_centavos") for row in candidate_rows)
    assert total_receipts == 319043392188
    assert financial_public == 269689145934 and financial_private == 35625612785 and financial_unclassified == 0
    assert expense_total == 307614262875 and payment_total == 303323646443
    total_fields = ["flow", "measure", "source_class", "amount_centavos", "coverage_candidates", "coverage_denominator", "coverage_pct", "amount_denominator_centavos", "share_pct", "record_count", "amount_missing_rows", "deduplication", "note"]
    total_output: list[dict[str, object]] = []
    def add_total(flow: str, measure: str, source_class: str, amount: int, covered: int, denominator: int, amount_denom: int, records: int, missing: int, dedup: str, note: str) -> None:
        total_output.append({"flow": flow, "measure": measure, "source_class": source_class, "amount_centavos": amount, "coverage_candidates": covered, "coverage_denominator": denominator, "coverage_pct": pct(covered, denominator), "amount_denominator_centavos": amount_denom, "share_pct": pct(amount, amount_denom), "record_count": records, "amount_missing_rows": missing, "deduplication": dedup, "note": note})
    all_receipt_records = sum(int(row["record_count"]) for (flow, _), row in summary_by_key.items() if flow == "receipts")
    for source_class in ("public", "private", "unclassified"):
        row = summary_by_key[("receipts", source_class)]
        add_total("receitas", "receitas declaradas - todas as naturezas", source_class, int(row["amount_centavos"]), int(row["candidate_count"]), len(ids), total_receipts, int(row["record_count"]), int(row["amount_missing_rows"]), "soma das linhas do recorte existente", "Inclui receitas financeiras e estimáveis; coberturas por classe podem se sobrepor entre candidatos.")
    for source_class in ("public", "private", "unclassified"):
        row = summary_by_key[("receipts", source_class)]
        add_total("receitas", "financeiras", source_class, int(row["financial_amount_centavos"]), len(financial_row_counts[source_class]), len(ids), financial_public + financial_private + financial_unclassified, financial_record_counts[source_class], int(row["amount_missing_rows"]), "soma das linhas do recorte existente", "Cobertura = candidatos com ao menos uma linha CD_NATUREZA=1 desta fonte; não confundir com cobertura financeira total.")
    financial_covered = len(financial_covered_ids)
    add_total("receitas", "financeiras - total", "todas as fontes", financial_public + financial_private + financial_unclassified, financial_covered, len(ids), financial_public + financial_private + financial_unclassified, financial_receipt_row_count, 0, "soma das linhas do recorte existente", "Financeiras apenas; não inclui receitas estimáveis.")
    add_total("receitas", "receitas declaradas - financeiras + estimáveis", "todas as fontes", total_receipts, len(ids), len(ids), total_receipts, all_receipt_records, 0, "soma das linhas do recorte existente", "Inclui recursos estimáveis; não é total apenas financeiro.")
    for source_class in ("public", "private", "unclassified"):
        row = summary_by_key[("payments", source_class)]
        add_total("pagamentos", "pagamentos declarados", source_class, int(row["amount_centavos"]), int(row["candidate_count"]), len(ids), payment_total, int(row["record_count"]), int(row["amount_missing_rows"]), "sem deduplicação adicional", "Fonte declarada da despesa; não rastreia fungibilidade nem pareia pagamento a receita.")
    add_total("pagamentos", "pagamentos declarados - total", "todas as fontes", payment_total, int(recut["population"]["payments_candidates_with_rows"]), len(ids), payment_total, sum(int(row["record_count"]) for (flow, _), row in summary_by_key.items() if flow == "payments"), 0, "sem deduplicação adicional", "841 candidatos não têm linha de pagamento no recorte; ausência não é zero pago.")
    add_total("despesas", "despesas contratadas deduplicadas", "não aplicável", expense_total, len(ids), int(recut["population"]["all_apto_candidates"]), expense_total, 1095391, 0, "deduplicação da análise existente", "9.204 APTO/Final com despesa observada; 272 de 9.476 APTO sem Final observado.")
    write_csv(REPORTS / "tse-2022-financial-distribution-totals.csv", total_fields, total_output)

    dictionary = [
        ("group_type", "Dimensão da linha: sexo ou raça/cor; linhas combinadas identificadas no rótulo."),
        ("group_value", "Categoria oficial da base eleitoral; PRETAS + PARDAS é um agregado sobreposto e não soma de categorias exclusivas."),
        ("candidate_count", "Número de candidatos do grupo dentro da população APTO/Final com despesa observada."),
        ("financial_receipt_candidates", "Candidatos com ao menos uma linha de receita financeira (CD_NATUREZA=1); valores registrados iguais a zero continuam cobertos."),
        ("financial_receipt_coverage_pct", "financial_receipt_candidates dividido pelo número de candidatos do grupo."),
        ("no_financial_receipt_candidates", "Candidatos sem qualquer linha CD_NATUREZA=1; excluídos das medianas de receitas e não imputados como zero observado."),
        ("financial_receipts_median_centavos", "Mediana do total financeiro individual entre candidatos com ao menos uma linha financeira. Fontes não presentes contribuem sem valor da fonte no cálculo comum; ausência fica separadamente sinalizada."),
        ("public_financial_median_centavos", "Mediana da receita financeira pública na mesma população com ao menos uma linha financeira total; não é mediana só entre recebedores públicos. Sem linha pública não significa zero observado."),
        ("other_resources_financial_median_centavos", "Mediana de Outros Recursos na mesma população financeira comum; não é mediana só entre recebedores de Outros Recursos. Sem linha da fonte não significa zero observado."),
        ("financial_public_absent_in_covered_candidates", "Candidatos com receita financeira observada em alguma fonte, mas sem linha pública financeira."),
        ("financial_private_absent_in_covered_candidates", "Candidatos com receita financeira observada em alguma fonte, mas sem linha financeira de Outros Recursos."),
        ("*_zero_amount_with_financial_row_candidates", "Candidatos com linha financeira da fonte cujo total da fonte é zero; separa zero observado da ausência de linha."),
        ("contracted_expenses_median_centavos", "Mediana da despesa contratada deduplicada entre todos os candidatos do grupo; despesa observada igual a zero permanece incluída."),
        ("elected_pct", "Eleitos com status total 2 ou 3 divididos por todos os candidatos do grupo, não apenas pela cobertura financeira."),
        ("small_group_n_lt_30", "Sinaliza apenas grupo com menos de 30 candidatos; não é teste de significância."),
        ("*_coverage_pct", "Candidatos com linha/cobertura observada divididos pelo denominador nomeado; ausências não são valores observados iguais a zero."),
        ("*_median_centavos", "Mediana em centavos; pode conter 0,5 centavo quando o número de observações é par. Dividir por 100 para obter reais."),
        ("amount_centavos", "Valor em centavos inteiros; dividir por 100 para exibir R$."),
        ("coverage_pct", "Candidatos com linha no recorte divididos pelo denominador indicado; não representa completude além do recorte."),
        ("share_pct", "Participação do valor na base indicada em amount_denominator_centavos."),
    ]
    write_csv(REPORTS / "tse-2022-financial-distribution-dictionary.csv", ["field", "definition"], [{"field": a, "definition": b} for a, b in dictionary])
    public_share = pct(financial_public, financial_public + financial_private + financial_unclassified)
    private_share = pct(financial_private, financial_public + financial_private + financial_unclassified)
    report = f'''# Distribuição financeira e eleitoral — deputados federais, 2022

## Resumo

Na população APTO/Final com despesa observada há 9.204 candidatos. As receitas financeiras declaradas somam **{currency(financial_public + financial_private + financial_unclassified)}**: recursos públicos **{currency(financial_public)} ({public_share:.4f}%)**, Outros Recursos **{currency(financial_private)} ({private_share:.4f}%)** e não classificados **{currency(financial_unclassified)}** (421 candidatos registrados na classe). Separadamente, 421 candidatos têm total de receitas observado igual a zero; não há candidatos sem qualquer linha de receita. O denominador dos percentuais é o total de receitas financeiras desta população.

As despesas contratadas deduplicadas dos candidatos somam **{currency(expense_total)}**. Os pagamentos declarados somam **{currency(payment_total)}**, com linhas para 8.363/9.204 candidatos; não houve deduplicação adicional de pagamentos. São três medidas distintas: receita declarada, contratação declarada e pagamento declarado.

## Recortes e denominadores

- População-base: 2022, 1º turno, deputado federal, candidaturas APTO com ao menos uma linha Final de despesa contratada; N=9.204 de 9.476 APTO. 272 APTO não têm despesa Final observada.
- Resultado eleitoral disponível para 9.204/9.204; a proporção eleita divide eleitos pelo total de candidatos do grupo, sem condicionar à cobertura de receitas financeiras. É diferente do recorte de 9.202 do modelo eleitoral ajustado.
- Receitas financeiras: 8.858/9.204 candidatos (96,2408%) têm ao menos uma linha CD_NATUREZA=1. Os 346 sem qualquer linha financeira são excluídos das medianas de receita, não imputados como R$ 0.
- As medianas total, pública e Outros Recursos usam a mesma população dentro de cada grupo: candidatos com ao menos uma linha financeira. Para a mediana de fonte, componente sem linha é zero apenas na operação matemática da mediana comum; não é recebido observado de R$ 0. Os campos de ausência de linha e os zeros com linha financeira observada ficam separados.
- Medianas de despesa contratada usam todos os candidatos do grupo com despesa Final observada; valores observados iguais a zero continuam incluídos.
- Todos os 9.204 têm alguma linha de receita, embora 346 não tenham linha financeira. Há linha financeira pública para {count_fmt(len(financial_row_counts["public"]))} candidatos e de Outros Recursos para {count_fmt(len(financial_row_counts["private"]))}; na coorte com qualquer receita financeira, {count_fmt(len(financial_covered_ids - financial_row_counts["public"]))} não têm linha pública e {count_fmt(len(financial_covered_ids - financial_row_counts["private"]))} não têm linha de Outros Recursos.
- Fonte: CD_FONTE 0/2 = público; CD_FONTE 1 = Outros Recursos; códigos restantes não classificados. CD_NATUREZA_RECEITA=1 = financeiro; 0 = estimável. Receitas estimáveis não entram nas medianas financeiras.

## Sexo, raça/cor e partidos

As tabelas por grupo apresentam candidatos, cobertura financeira, medianas de receitas na coorte com receita financeira observada, mediana de despesas contratadas e eleitos/total. Categorias de raça/cor ficam separadas; PRETAS + PARDAS é um agregado complementar sobreposto a PRETA e PARDA. “NÃO INFORMADO” e “NÃO DIVULGÁVEL” permanecem explícitas.

A tabela por partido descreve despesas contratadas dos candidatos, não contas de diretórios. `small_group_n_lt_30` sinaliza grupos com menos de 30 candidatos; não é teste de significância.

Despesas menores não significam menor orçamento recebido. Diferenças entre grupos são descritivas; não demonstram efeito causal. A fonte declarada de um pagamento não prova rastreamento de fungibilidade entre receita e despesa.

## Arquivos

- `tse-2022-financial-distribution-totals.csv`: totais, recortes, denominadores e cobertura.
- `tse-2022-financial-distribution-by-party.csv`: despesas contratadas por partido dos candidatos.
- `tse-2022-financial-distribution-by-group.csv`: sexo, categorias de raça/cor e agregado pretas+pardas.
- `tse-2022-financial-distribution-dictionary.csv`: definições e interpretação dos campos.
- `summarize-tse-2022-financial-distribution.py`: reprodução destes artefatos a partir dos arquivos existentes.
'''
    (REPORTS / "tse-2022-financial-distribution.md").write_text(report, encoding="utf-8")
    print(f"Wrote four CSVs and report; N={len(ids)}, receipts={currency(total_receipts)}, financial={currency(financial_public + financial_private + financial_unclassified)}, expenses={currency(expense_total)}, payments={currency(payment_total)}")


if __name__ == "__main__":
    main()
