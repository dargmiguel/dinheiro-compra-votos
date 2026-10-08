from __future__ import annotations

import csv
import json
from decimal import Decimal
from pathlib import Path


def _money(centavos: int) -> str:
    value = Decimal(centavos) / Decimal(100)
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _int(value: str) -> int | None:
    return int(value) if value != "" else None

def _ratio(centavos: int, votes: int) -> str:
    return f"{Decimal(centavos) / Decimal(votes):.2f}".replace(".", ",")


def write_exploratory_report(derived_dir: Path, output_path: Path) -> Path:
    derived_dir = Path(derived_dir)
    validation = json.loads((derived_dir / "validation.json").read_text(encoding="utf-8"))
    if validation.get("status") != "approved":
        raise ValueError("relatório exploratório bloqueado: validation.json não está aprovado")

    rows = []
    with (derived_dir / "analytical_base.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            row["expense"] = _int(row["declared_expense_centavos"])
            row["votes"] = _int(row["valid_nominal_votes"])
            rows.append(row)

    expense_observations = {value: sum(row["expense_observation"] == value for row in rows) for value in ("observed", "observed_zero", "absent")}
    vote_observations = {value: sum(row["vote_observation"] == value for row in rows) for value in ("observed", "observed_zero", "absent")}
    observed_expense = [row for row in rows if row["expense"] is not None]
    observed_votes = [row for row in rows if row["votes"] is not None]
    comparable = [row for row in rows if row["expense"] is not None and row["votes"] is not None and row["votes"] > 0]
    top_votes = sorted(observed_votes, key=lambda row: (row["votes"], row["sq_candidate"]), reverse=True)[:10]
    top_expense = sorted(observed_expense, key=lambda row: (row["expense"], row["sq_candidate"]), reverse=True)[:10]
    top_cost = sorted(comparable, key=lambda row: (row["expense"] / row["votes"], row["sq_candidate"]), reverse=True)[:10]

    lines = [
        "# Relatório exploratório: TSE 2022",
        "",
        "Este relatório descreve a base aprovada do piloto; não estima causalidade, não atribui probabilidade de vitória e não substitui controles estatísticos. O escopo é Brasil / todas as UFs, apenas deputado federal no primeiro turno de 2022.",
        "",
        "## Proveniência e aprovação",
        "",
        f"- Manifesto: `{validation.get('manifest_id')}`.",
        f"- Status das validações: **{validation['status']}**.",
        f"- Candidatos na base analítica: **{len(rows):,}**.".replace(",", "."),
        "- Despesas: soma de `VR_DESPESA_CONTRATADA`, em centavos de real.",
        "- Votos: soma de `QT_VOTOS_NOMINAIS_VALIDOS` por candidato, município, zona e trânsito.",
        "- Arquivos `BR`/`BRASIL` não foram misturados aos arquivos por UF; a decisão e a lista estão em `validation.json`.",
        "",
        "## Cobertura das medidas",
        "",
        "| Medida | Observada | Observada com zero | Ausente |",
        "|---|---:|---:|---:|",
        f"| Despesa contratada | {expense_observations['observed']:,} | {expense_observations['observed_zero']:,} | {expense_observations['absent']:,} |".replace(",", "."),
        f"| Voto nominal válido | {vote_observations['observed']:,} | {vote_observations['observed_zero']:,} | {vote_observations['absent']:,} |".replace(",", "."),
        "",
        "## Totais descritivos",
        "",
        f"- Despesa contratada declarada observada: **{_money(sum(row['expense'] for row in observed_expense))}**.",
        f"- Votos nominais válidos observados: **{sum(row['votes'] for row in observed_votes):,}**.".replace(",", "."),
        f"- Candidatos com despesa e votos positivos: **{len(comparable):,}**.".replace(",", "."),
        "",
        "## Dez maiores votações nominais válidas",
        "",
        "| SQ_CANDIDATO | Candidato | UF | Votos | Despesa observada |",
        "|---|---|---|---:|---:|",
    ]
    lines.extend(f"| {row['sq_candidate']} | {row['candidate_name']} | {row['uf']} | {row['votes']:,} | {_money(row['expense']) if row['expense'] is not None else 'ausente'} |".replace(",", ".") for row in top_votes)
    lines.extend([
        "",
        "## Dez maiores despesas contratadas",
        "",
        "| SQ_CANDIDATO | Candidato | UF | Despesa | Votos observados |",
        "|---|---|---|---:|---:|",
    ])
    lines.extend(f"| {row['sq_candidate']} | {row['candidate_name']} | {row['uf']} | {_money(row['expense'])} | {row['votes']:,} |".replace(",", ".") for row in top_expense)
    lines.extend([
        "",
        "## Dez maiores despesas por voto positivo",
        "",
        "A razão abaixo é apenas descritiva e usa candidatos com ambas as medidas observadas e mais de zero voto; não é evidência de que gasto cause voto.",
        "",
        "| SQ_CANDIDATO | Candidato | UF | Despesa | Votos | Centavos por voto |",
        "|---|---|---|---:|---:|---:|",
    ])
    lines.extend(f"| {row['sq_candidate']} | {row['candidate_name']} | {row['uf']} | {_money(row['expense'])} | {row['votes']} | {_ratio(row['expense'], row['votes'])} |" for row in top_cost)
    lines.extend([
        "",
        "## Limitações",
        "",
        "- A prestação usada mede despesas contratadas declaradas; pagamentos, receitas, transferências e despesas partidárias não foram transformados em gasto individual do candidato.",
        "- Ausência foi preservada e não equivale a zero. A cobertura desigual precisa ser tratada antes de qualquer regressão.",
        "- As tabelas são exploratórias. Comparações entre candidatos ainda exigem controles por UF, partido, situação, competitividade e outras variáveis definidas no estudo.",
    ])
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path
