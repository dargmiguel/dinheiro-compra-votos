from __future__ import annotations

import argparse
import csv
import html
import math
import sqlite3
import xml.etree.ElementTree as ET
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
SOURCE = REPORTS / "linkedin-carousel-2022"
DATA = SOURCE / "data"
OUT = SOURCE / "v4"
W, H = 1080, 1350
TOTAL_SLIDES = 8
FINAL_SLIDE_IDS = ("01", "03", "04", "05", "scatter-rj", "06", "07", "09")
REPRO_URL = "https://github.com/dargmiguel/dinheiro-compra-votos"

C = {
    "paper": "#F7F6F1", "white": "#FFFFFF", "ink": "#172A3A",
    "teal": "#14766F", "teal_dark": "#0B514D", "teal_pale": "#DDECE8",
    "gold": "#C58D2A", "gold_pale": "#F2E8D0", "rust": "#B34F3D",
    "rust_pale": "#F3E2DC", "muted": "#5D6D74", "line": "#D8D9D2",
    "grid": "#E8E8E1", "slate": "#39566A",
}
FONT_DISPLAY = "Georgia, 'Times New Roman', serif"
FONT_BODY = "Arial, Helvetica, sans-serif"
FONT_DATA = "Consolas, 'Courier New', monospace"

IBGE_UF = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP", "17": "TO",
    "21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB", "26": "PE", "27": "AL", "28": "SE", "29": "BA",
    "31": "MG", "32": "ES", "33": "RJ", "35": "SP", "41": "PR", "42": "SC", "43": "RS",
    "50": "MS", "51": "MT", "52": "GO", "53": "DF",
}

# Label positions are state-capital coordinates, used only to place UF abbreviations.
CAPITALS = {
    "AC": (-67.81, -9.97), "AL": (-35.74, -9.65), "AP": (-51.07, 0.03),
    "AM": (-60.02, -3.10), "BA": (-38.50, -12.97), "CE": (-38.54, -3.73),
    "DF": (-47.88, -15.79), "ES": (-40.34, -20.32), "GO": (-49.25, -16.68),
    "MA": (-44.30, -2.53), "MT": (-56.10, -15.60), "MS": (-54.62, -20.45),
    "MG": (-43.94, -19.92), "PA": (-48.50, -1.45), "PB": (-34.88, -7.12),
    "PR": (-49.27, -25.43), "PE": (-34.88, -8.05), "PI": (-42.80, -5.09),
    "RJ": (-43.20, -22.91), "RN": (-35.21, -5.80), "RS": (-51.23, -30.03),
    "RO": (-63.90, -8.76), "RR": (-60.67, 2.82), "SC": (-48.55, -27.59),
    "SP": (-46.63, -23.55), "SE": (-37.07, -10.91), "TO": (-48.33, -10.18),
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def br(value: float | Decimal, places: int = 1) -> str:
    quant = Decimal("1").scaleb(-places)
    rounded = Decimal(str(value)).quantize(quant, rounding=ROUND_HALF_UP)
    return f"{rounded:,.{places}f}".replace(",", "\0").replace(".", ",").replace("\0", ".")


def brl_short(value: Decimal | float) -> str:
    amount = Decimal(str(value))
    if amount >= Decimal("1000000"):
        return f"R$ {br(amount / Decimal('1000000'), 2)} mi"
    return f"R$ {br(amount / Decimal('1000'), 1)} mil"


def text(x: float, y: float, content: str, size: int = 28, fill: str | None = None,
         family: str = FONT_BODY, weight: int | str = 400, anchor: str = "start",
         letter: float | None = None) -> str:
    attrs = (f'x="{x:.1f}" y="{y:.1f}" font-family="{family}" font-size="{size}" '
             f'font-weight="{weight}" text-anchor="{anchor}" fill="{fill or C["ink"]}"')
    if letter is not None:
        attrs += f' letter-spacing="{letter}"'
    return f"<text {attrs}>{html.escape(str(content))}</text>"


def rect(x: float, y: float, width: float, height: float, fill: str, radius: int = 0,
         stroke: str | None = None, stroke_width: int = 1) -> str:
    result = f'<rect x="{x}" y="{y}" width="{width}" height="{height}" fill="{fill}" rx="{radius}"'
    if stroke:
        result += f' stroke="{stroke}" stroke-width="{stroke_width}"'
    return result + '/>'


def line(x1: float, y1: float, x2: float, y2: float, stroke: str, width: float = 2) -> str:
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{width}"/>'


def frame(slide: int, title: str, subtitle: str, body: list[str],
          notes: list[str], source: str, title_lines: list[str] | None = None,
          page_label: str | None = None, note_size: int = 17,
          title_size: int = 43, body_separator_y: int | None = 1060) -> str:
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    parts += [f'<title>{html.escape(title)}</title>', rect(0, 0, W, H, C["paper"])]
    parts += [text(64, 48, "CADERNO DE DADOS  /  ELEIÇÕES 2022", 19, C["teal_dark"], FONT_DATA, 700, letter=0.7)]
    page = page_label or f"{slide:02d} / {TOTAL_SLIDES:02d}"
    parts += [text(1016, 48, page, 19, C["muted"], FONT_DATA, 600, "end")]
    parts += [line(64, 69, 1016, 69, C["ink"], 2)]
    if title_lines:
        for i, row in enumerate(title_lines):
            parts += [text(64, 135 + i * 48, row, title_size, C["ink"], FONT_DISPLAY, 700)]
        parts += [text(64, 218, subtitle, 22, C["muted"], FONT_BODY, 400)]
    else:
        size = 49 if len(title) > 32 else 56
        parts += [text(64, 148, title, size, C["ink"], FONT_DISPLAY, 700)]
        parts += [text(64, 204, subtitle, 22, C["muted"], FONT_BODY, 400)]
    parts += body
    if body_separator_y is not None:
        parts += [line(64, body_separator_y, 1016, body_separator_y, C["line"], 2)]
    note_y = 1090
    for note in notes[:2]:
        parts += [text(64, note_y, note, note_size, C["muted"], FONT_BODY, 400)]
        note_y += 26
    if source.startswith("Reprodução:"):
        parts += [f'<a href="{REPRO_URL}">{text(64, 1170, source, 16, C["muted"], FONT_BODY, 400)}</a>']
    else:
        parts += [text(64, 1170, source, 16, C["muted"], FONT_BODY, 400)]
    parts += [line(64, 1235, 1016, 1235, C["line"], 2)]
    parts += [text(64, 1270, "ELEIÇÕES FEDERAIS 2022  ·  TSE", 17, C["teal_dark"], FONT_DATA, 600, letter=0.2)]
    parts += [text(1016, 1270, "2022", 17, C["muted"], FONT_DATA, 600, "end")]
    parts += ["</svg>"]
    if note_y > 1150:
        raise ValueError(f"Notas da lâmina {slide} ultrapassaram a área reservada.")
    return "\n".join(parts)


def load_existing() -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    map_rows = read_csv(DATA / "despesas-eleitos-por-uf.csv")
    band_rows = read_csv(DATA / "proporcao-eleita-por-faixa.csv")
    counterpoint = read_csv(DATA / "contraponto-acima-1m.csv")
    funding = read_csv(REPORTS / "tse-2022-financial-distribution-totals.csv")
    groups = read_csv(REPORTS / "tse-2022-financial-distribution-by-group.csv")
    if len(map_rows) != 27 or sum(int(r["elected_result_classified_count"]) for r in map_rows) != 512:
        raise ValueError("A tabela de mapa salva não contém 27 UFs e 512 eleitos.")
    if sum(int(r["expense_observed_count"]) for r in map_rows) != 510:
        raise ValueError("A cobertura do mapa salvo não reconcilia com 510 observados.")
    if sum(int(r["candidate_count"]) for r in band_rows) != 9202:
        raise ValueError("A tabela de faixas salva não corresponde ao recorte aprovado.")
    return map_rows, band_rows, counterpoint, funding, groups








def cover_svg(funding: list[dict[str, str]]) -> str:
    expense = next(r for r in funding if r["flow"] == "despesas" and r["measure"] == "despesas contratadas deduplicadas")
    receipts = next(r for r in funding if r["flow"] == "receitas" and r["measure"] == "financeiras - total")
    public = next(r for r in funding if r["flow"] == "receitas" and r["measure"] == "financeiras" and r["source_class"] == "public")
    other = next(r for r in funding if r["flow"] == "receitas" and r["measure"] == "financeiras" and r["source_class"] == "private")
    total_expense = Decimal(expense["amount_centavos"]) / 100
    receipt_total = Decimal(receipts["amount_centavos"]) / 100
    public_brl = Decimal(public["amount_centavos"]) / 100
    other_brl = Decimal(other["amount_centavos"]) / 100
    public_pct = Decimal(public["share_pct"])
    body = [
        rect(64, 246, 952, 384, C["teal_dark"], 5),
        text(104, 296, "DESPESAS CONTRATADAS DECLARADAS", 22, C["teal_pale"], FONT_DATA, 700, letter=0.5),
        text(104, 412, f"R$ {br(total_expense / Decimal('1000000000'), 2)} bilhões", 74, C["white"], FONT_DISPLAY, 700),
        text(104, 470, "por 9.204 candidaturas a deputado federal", 25, C["white"], FONT_BODY, 500),
        text(104, 516, "Brasil · 1º turno · 2022", 21, C["teal_pale"], FONT_DATA, 500),
        rect(752, 290, 216, 292, C["paper"], 4, C["line"], 2),
        text(774, 330, "PRESTAÇÃO", 18, C["teal_dark"], FONT_DATA, 700),
        text(774, 358, "2022 · TSE", 17, C["muted"], FONT_DATA, 600),
        line(774, 378, 944, 378, C["line"], 2),
        text(774, 416, "DESPESAS", 15, C["muted"], FONT_DATA, 700),
        rect(774, 431, 154, 10, C["teal_pale"], 2),
        rect(774, 456, 132, 10, C["teal_pale"], 2),
        rect(774, 481, 161, 10, C["teal_pale"], 2),
        line(774, 507, 944, 507, C["line"], 2),
        text(774, 548, "FINAL", 18, C["rust"], FONT_DATA, 700),
        rect(64, 660, 952, 350, C["white"], 5, C["line"], 2),
        text(104, 706, "RECEITAS FINANCEIRAS · OUTRA MEDIDA", 21, C["muted"], FONT_DATA, 700),
        text(104, 812, f"{br(public_pct, 1)}%", 78, C["rust"], FONT_DISPLAY, 700),
        text(396, 778, "das receitas financeiras", 26, C["ink"], FONT_BODY, 600),
        text(396, 815, "declaradas eram públicas", 26, C["ink"], FONT_BODY, 600),
        rect(104, 850, 872, 36, C["rust_pale"], 3),
        rect(104, 850, float(public_pct / 100) * 872, 36, C["teal"], 3),
        text(104, 930, f"Públicas · R$ {br(public_brl / Decimal('1000000000'), 2)} bilhões", 22, C["teal_dark"], FONT_BODY, 700),
        text(976, 930, f"Outros Recursos · R$ {br(other_brl / Decimal('1000000'), 1)} mi", 21, C["rust"], FONT_BODY, 700, "end"),
        text(104, 977, f"Receitas financeiras declaradas: R$ {br(receipt_total / Decimal('1000000000'), 2)} bilhões", 20, C["muted"], FONT_BODY, 500),
    ]
    return frame(1, "Bilhões em campanhas. Quem chegou à Câmara?",
                 "Deputados federais · Brasil · 1º turno de 2022", body,
                 ["R$ 3,08 bi = despesas contratadas; 88,3% = participação pública nas receitas financeiras."],
                 "Fonte: TSE 2022 · prestações de contas e receitas financeiras declaradas.",
                 title_lines=["Bilhões em campanhas.", "Quem chegou à Câmara?"])




def party_svg(rows: list[dict[str, str]]) -> str:
    top = sorted(rows, key=lambda row: (-int(row["expense_centavos"]), row["party_abbrev"]))[:7]
    lowest_elected = sorted(
        (row for row in rows if int(row["elected_count"]) > 0),
        key=lambda row: (int(row["expense_centavos"]), row["party_abbrev"]),
    )[:3]
    no_elected = [row for row in rows if int(row["elected_count"]) == 0]
    no_elected_expense = sum(
        (Decimal(row["expense_centavos"]) for row in no_elected), Decimal(0)
    ) / Decimal("100000000")
    axis_x, axis_w, max_centavos = 365, 430, Decimal("50000000000")
    body = [
        text(64, 264, "Despesas contratadas somadas por partido", 30, C["ink"], FONT_BODY, 700),
        text(64, 298, "Escala linear · R$ milhões · 0 a 500", 22, C["muted"], FONT_BODY, 500),
        text(1016, 337, "ELEITOS", 15, C["muted"], FONT_DATA, 700, "end"),
    ]
    for tick in (0, 125, 250, 375, 500):
        x = axis_x + axis_w * tick / 500
        body += [
            text(x, 337, str(tick), 22, C["muted"], FONT_DATA, 500, "middle"),
            line(x, 350, x, 740, C["line"], 1),
        ]
    colors = [C["teal_dark"], C["teal"], C["slate"], C["gold"], C["rust"], C["muted"], C["ink"]]
    for i, row in enumerate(top):
        y = 370 + i * 52
        total = Decimal(row["expense_centavos"])
        width = float(total / max_centavos) * axis_w
        body += [
            text(64, y + 30, row["party_abbrev"], 32, C["ink"], FONT_BODY, 700),
            rect(axis_x, y, axis_w, 36, C["grid"], 3),
            rect(axis_x, y, width, 36, colors[i], 3),
            text(954, y + 29, f"R$ {br(total / Decimal('100000000'), 1)} mi",
                 22, colors[i], FONT_DATA, 700, "end"),
            text(975, y + 29, "•", 14, colors[i], FONT_DATA, 700, "middle"),
            text(1016, y + 29, str(int(row["elected_count"])),
                 22, colors[i], FONT_DATA, 700, "end"),
        ]
    body += [
        rect(64, 775, 952, 232, C["white"], 4, C["line"], 2),
        text(88, 812, "E quem elegeu deputados com os menores totais declarados?",
             24, C["ink"], FONT_BODY, 700),
        text(96, 850, "PARTIDO", 15, C["muted"], FONT_DATA, 700),
        text(610, 850, "DESPESA TOTAL", 15, C["muted"], FONT_DATA, 700, "end"),
        text(984, 850, "ELEITOS", 15, C["muted"], FONT_DATA, 700, "end"),
        line(88, 862, 992, 862, C["line"], 1),
    ]
    for i, row in enumerate(lowest_elected):
        y = 899 + i * 39
        total_mi = Decimal(row["expense_centavos"]) / Decimal("100000000")
        body += [
            text(96, y, row["party_abbrev"], 22, C["ink"], FONT_BODY, 700),
            text(610, y, f"R$ {br(total_mi, 2)} milhões", 21, C["ink"], FONT_DATA, 600, "end"),
            text(984, y, f"{int(row['elected_count'])}", 22, C["teal_dark"], FONT_DATA, 700, "end"),
        ]
        if i < len(lowest_elected) - 1:
            body.append(line(88, y + 15, 992, y + 15, C["line"], 1))
    body.append(text(
        64, 1042,
        f"{len(no_elected)} partidos somaram R$ {br(no_elected_expense, 2)} milhões em despesas declaradas e não elegeram nenhum deputado.",
        19, C["ink"], FONT_BODY, 600,
    ))
    return frame(
        2, "Quais partidos declararam mais despesas?",
        "Despesas contratadas dos candidatos filiados · recorte eleitoral N=9.202",
        body,
        ["Despesas de todas as candidaturas do partido no recorte, inclusive as não eleitas."],
        "Fonte: TSE 2022 · despesas contratadas deduplicadas por candidatura.",
        title_lines=["Quais partidos declararam", "mais despesas?"],
        page_label="02 / 08", title_size=42)








def teal(value: float, lo: float, hi: float) -> str:
    t = 0 if hi == lo else (value - lo) / (hi - lo)
    start, end = (221, 236, 232), (11, 81, 77)
    rgb = tuple(round(a + t * (b - a)) for a, b in zip(start, end))
    return "#" + "".join(f"{channel:02X}" for channel in rgb)


def load_ibge_geometry() -> tuple[str, str, dict[str, str]]:
    svg_path = SOURCE / "v4" / "apoio" / "map-geometry.svg"
    root = ET.parse(svg_path).getroot()
    inner = root.find(".//{http://www.w3.org/2000/svg}svg")
    if inner is None:
        raise ValueError("O SVG preservado não contém o painel cartográfico esperado.")
    group = inner.find("{http://www.w3.org/2000/svg}g")
    if group is None:
        raise ValueError("O SVG preservado não contém as geometrias das UFs.")
    paths = {element.attrib["id"].removeprefix("uf-"): element.attrib["d"]
             for element in group if element.tag.endswith("path")}
    if set(paths) != set(IBGE_UF.values()):
        raise ValueError(f"A geometria preservada contém {len(paths)} UFs, esperado 27.")
    return inner.attrib["viewBox"], group.attrib["transform"], paths


def map_svg(map_rows: list[dict[str, str]]) -> str:
    view_box, transform, paths = load_ibge_geometry()
    values = {row["uf"]: Decimal(row["median_contracted_expense_brl"]) for row in map_rows}
    lo, hi = min(values.values()), max(values.values())
    map_paths = []
    for uf in IBGE_UF.values():
        fill = teal(float(values[uf]), float(lo), float(hi))
        map_paths.append(
            f'<path id="uf-{uf}" d="{paths[uf]}" fill="{fill}" '
            'stroke="#FFFFFF" stroke-width="850" stroke-linejoin="round"/>'
        )
    map_labels = [
        f'<text x="{lon}" y="{-lat}" text-anchor="middle" font-family="{FONT_DATA}" '
        f'font-size="0.95" font-weight="700" fill="{C["ink"]}" stroke="{C["paper"]}" '
        f'stroke-width="0.12" paint-order="stroke">{uf}</text>'
        for uf, (lon, lat) in CAPITALS.items()
    ]
    panel_x, panel_y, panel_w, panel_h = 90, 242, 900, 500
    vb_x, vb_y, vb_w, vb_h = (float(part) for part in view_box.split())
    scale = min(panel_w / vb_w, panel_h / vb_h)
    pad_x, pad_y = (panel_w - vb_w * scale) / 2, (panel_h - vb_h * scale) / 2
    map_panel = (
        f'<svg x="{panel_x}" y="{panel_y}" width="{panel_w}" height="{panel_h}" '
        f'viewBox="{html.escape(view_box)}" preserveAspectRatio="xMidYMid meet">'
        f'<g transform="{html.escape(transform)}">{"".join(map_paths)}</g>{"".join(map_labels)}</svg>'
    )
    ordered = sorted(map_rows, key=lambda row: Decimal(row["median_contracted_expense_brl"]))
    selected = [next(row for row in ordered if row["uf"] == uf) for uf in ("RR", "SP", "PE")]
    callouts = {
        "RR": (64, 330, 250, 345, "start"),
        "PE": (1016, 387, 830, 412, "end"),
        "SP": (1016, 602, 830, 610, "end"),
    }
    body = [
        map_panel,
        '<defs><linearGradient id="expense-scale" x1="0" x2="1"><stop offset="0%" stop-color="#DDECE8"/><stop offset="50%" stop-color="#749E9A"/><stop offset="100%" stop-color="#0B514D"/></linearGradient></defs>',
    ]
    for row in selected:
        uf = row["uf"]
        lon, lat = CAPITALS[uf]
        point_x = panel_x + pad_x + (lon - vb_x) * scale
        point_y = panel_y + pad_y + (-lat - vb_y) * scale
        label_x, label_y, end_x, end_y, anchor = callouts[uf]
        median = Decimal(row["median_contracted_expense_brl"])
        if uf in ("RR", "PE"):
            body.append(text(
                label_x, label_y, "Menor valor" if uf == "RR" else "Maior valor",
                18, C["teal_dark"], FONT_DATA, 700, anchor,
            ))
        body += [
            line(point_x, point_y, end_x, end_y, C["ink"], 1.8),
            f'<circle cx="{point_x:.1f}" cy="{point_y:.1f}" r="6.5" fill="{C["gold"]}" stroke="{C["paper"]}" stroke-width="2.5"/>',
            text(label_x, label_y + 27,
                 f"{uf} · R$ {br(median / Decimal('1000000'), 2)} mi",
                 18, C["teal_dark"], FONT_DATA, 700, anchor),
        ]
    body += [
        rect(110, 758, 860, 16, "url(#expense-scale)", 2),
        text(110, 798, "R$ 1,00 mi", 18, C["ink"], FONT_DATA, 600),
        text(540, 798, "R$ 1,77 mi", 18, C["ink"], FONT_DATA, 600, "middle"),
        text(970, 798, "R$ 2,55 mi", 18, C["ink"], FONT_DATA, 600, "end"),
    ]
    listing = sorted(map_rows, key=lambda row: row["uf"])
    columns = [64, 384, 704]
    for column, x in enumerate(columns):
        for i, row in enumerate(listing[column * 9:(column + 1) * 9]):
            y = 832 + i * 26
            median = Decimal(row["median_contracted_expense_brl"])
            body += [
                text(x, y, row["uf"], 19, C["muted"], FONT_DATA, 500),
                text(x + 270, y, f"R$ {br(median / Decimal('1000000'), 2)} mi",
                     20, C["ink"], FONT_DATA, 700, "end"),
                line(x, y + 8, x + 270, y + 8, C["grid"], 0.8),
            ]
    return frame(3, "Quanto declararam gastar os eleitos em cada estado?",
                 "Despesa contratada mediana dos deputados eleitos em cada estado",
                 body,
                 ["Metade dos eleitos declarou menos que esse valor; metade, mais.",
                  "Dois eleitos sem despesa final observada: um na BA e um em SP; eles não entram nas medianas."],
                 "Fonte: TSE 2022 · resultados oficiais e despesas finais; malha IBGE 2022.",
                 title_lines=["Quanto declararam gastar", "os eleitos em cada estado?"],
                 page_label="03 / 08")


def map_support_svg(map_rows: list[dict[str, str]]) -> str:
    called_out = {"RR", "DF", "PE", "SP", "RJ", "MG"}
    rows = sorted((row for row in map_rows if row["uf"] not in called_out), key=lambda row: row["uf"])
    if len(rows) != 21:
        raise ValueError(f"A tabela deve conter 21 UFs além das seis chamadas, recebeu {len(rows)}.")
    body: list[str] = []
    columns = [64, 387, 710]
    for column, x in enumerate(columns):
        body.append(text(x, 300, "UF · mediana · cobertura Final", 18, C["muted"], FONT_DATA, 700))
        for i, row in enumerate(rows[column * 7:(column + 1) * 7]):
            y = 350 + i * 90
            median = Decimal(row["median_contracted_expense_brl"])
            observed_n = int(row["expense_observed_count"])
            elected_n = int(row["elected_result_classified_count"])
            body += [
                text(x, y, f"{row['uf']} · R$ {br(median, 0)}", 22, C["ink"], FONT_DATA, 600),
                text(x, y + 30, f"{observed_n}/{elected_n} eleitos APTO observados",
                     16, C["muted"], FONT_BODY, 500),
                line(x, y + 44, x + 290, y + 44, C["line"], 1),
            ]
    return frame(4, "E os demais estados?",
                 "Mediana das despesas declaradas dos eleitos APTO · reais; cobertura Final observada / eleitos.",
                 body,
                 ["O mapa e seus cartões mostram RR, DF, PE, SP, RJ e MG; esta lâmina lista as outras 21 UFs.",
                  "Ausência de despesa Final permanece ausente, nunca convertida em zero."],
                 "Fonte: TSE 2022 · resultados oficiais e despesas Final; mediana por UF.",
                 title_lines=["E os demais estados?", "Medianas e cobertura por UF"],
                 page_label="APOIO", title_size=42)






def bands_svg(bands: list[dict[str, str]], counterpoint: list[dict[str, str]]) -> str:
    elected_total = sum(int(row["elected_count"]) for row in bands)
    expected_bands = {
        "ate_50_mil", "50_a_200_mil", "200_mil_a_1_milhao", "acima_1_milhao",
    }
    if elected_total != 510 or len(bands) != 4 or {r["expense_band_code"] for r in bands} != expected_bands:
        raise ValueError("A distribuição deve conter quatro faixas e cobrir 510 eleitos.")
    by_band = {row["expense_band_code"]: row for row in bands}
    high_band = by_band["acima_1_milhao"]
    elected_high = int(high_band["elected_count"])
    candidate_high = int(high_band["candidate_count"])

    by_metric = {row["metric"]: row for row in counterpoint}
    non_elected_high = by_metric["Não eleitos entre candidatos acima de R$ 1 milhão"]
    non_elected_count = int(non_elected_high["numerator"])
    if (candidate_high != 987 or elected_high != 420
            or int(non_elected_high["denominator"]) != candidate_high
            or non_elected_count != 567
            or elected_high + non_elected_count != candidate_high):
        raise ValueError("As contagens acima de R$ 1 milhão divergiram do resumo validado.")

    elected_candidate_pct = Decimal(elected_high) * 100 / Decimal(candidate_high)
    not_elected_pct = Decimal(non_elected_count) * 100 / Decimal(candidate_high)
    if (elected_candidate_pct.quantize(Decimal("0.1")) != Decimal("42.6")
            or not_elected_pct.quantize(Decimal("0.1")) != Decimal("57.4")):
        raise ValueError("As proporções por resultado acima de R$ 1 milhão divergiram.")

    axis_x, axis_w = 64, 952
    block_shift = 20
    elected_share = Decimal(elected_high) * 100 / Decimal(elected_total)
    body = [
        text(540, 276, f"{br(elected_share, 1)}%", 88, C["rust"], FONT_DISPLAY, 700, "middle"),
        text(540, 314, "dos eleitos declararam mais de R$ 1 milhão",
             25, C["ink"], FONT_BODY, 600, "middle"),
        text(64, 356 + block_shift, "Distribuição dos 510 eleitos por faixa de despesa",
             24, C["ink"], FONT_BODY, 700),
    ]
    for tick in (0, 25, 50, 75, 100):
        x = axis_x + axis_w * tick / 100
        body += [
            text(x, 397 + block_shift, f"{tick}%", 20, C["muted"], FONT_DATA, 500, "middle"),
            line(x, 408 + block_shift, x, 724 + block_shift, C["line"], 1),
        ]
    for index, row in enumerate(bands):
        y = 427 + index * 81 + block_shift
        elected_n = int(row["elected_count"])
        share = Decimal(elected_n) * 100 / Decimal(elected_total)
        width = float(share / 100) * axis_w
        is_high_band = row["expense_band_code"] == "acima_1_milhao"
        color = C["rust"] if is_high_band else C["teal_pale"]
        value_x = min(axis_x + width + 12, axis_x + axis_w - 70)
        body.append(text(64, y, row["expense_band_label"], 24, C["ink"], FONT_BODY, 600))
        if width > 0:
            body.append(rect(axis_x, y + 14, width, 38, color, 2))
        body.append(text(value_x, y + 43, f"{br(share, 1)}%",
                         20, C["rust"] if is_high_band else C["muted"],
                         FONT_DATA, 700))

    body.append(text(540, 779 + block_shift, "Mas a maioria dos candidatos dessa faixa não se elegeu.",
                     22, C["rust"], FONT_BODY, 700, "middle"))
    body.append(text(540, 808 + block_shift, "Entre os 987 candidatos acima de R$ 1 milhão",
                     22, C["muted"], FONT_BODY, 500, "middle"))
    cards = [
        (128, elected_high, f"eleitos · {br(elected_candidate_pct, 1)}%", C["teal_dark"]),
        (552, non_elected_count, f"não eleitos · {br(not_elected_pct, 1)}%", "#7A263A"),
    ]
    for x, count, label, color in cards:
        card_y = 828 + block_shift
        body += [
            rect(x, card_y, 400, 136, C["white"], 4, C["line"], 2),
            text(x + 200, card_y + 68, str(count), 54, color, FONT_DISPLAY, 700, "middle"),
            text(x + 200, card_y + 112, label, 21, color, FONT_BODY, 600, "middle"),
        ]
    return frame(5, "Quanto declararam gastar os candidatos que se elegeram?",
                 "",
                 body,
                 [],
                 "Fonte: TSE 2022 · recorte APTO/Final com controles completos.",
                 title_lines=["Quanto declararam gastar", "os candidatos que se elegeram?"],
                 page_label="04 / 08", title_size=40)


def gender_svg(groups: list[dict[str, str]]) -> str:
    data = {row["group_value"]: row for row in groups if row["group_type"] == "sexo"}
    women, men = data["FEMININO"], data["MASCULINO"]
    total = data["TODOS"]
    expected = {
        "FEMININO": ("2.76", "65.6", "3266", "7067000", "35,5", "90"),
        "MASCULINO": ("7.08", "65.0", "5936", "7566000", "64,5", "420"),
    }
    for key, row in (("FEMININO", women), ("MASCULINO", men)):
        median_thousands = (
            Decimal(row["contracted_expenses_median_centavos"]) / Decimal("100000")
        ).quantize(Decimal("0.1"))
        candidate_share = br(Decimal(row["reference_population_coverage_pct"]), 1)
        observed = (
            str(Decimal(row["elected_pct"]).quantize(Decimal("0.01"))),
            str(median_thousands),
            row["elected_denominator"],
            row["financial_receipts_median_centavos"],
            candidate_share,
            row["elected_candidates"],
        )
        if observed != expected[key]:
            raise ValueError(f"Os resultados existentes por grupo mudaram para {key}.")
    if total["candidate_count"] != "9204" or total["elected_candidates"] != "510":
        raise ValueError("O recorte existente de sexo mudou.")

    median_x, median_w, median_max = 240, 640, Decimal("120000")
    body = [text(64, 287, "Receita e despesa medianas",
                 30, C["ink"], FONT_BODY, 700)]
    body += [
        rect(240, 318, 14, 14, "#B9BFC2"),
        text(262, 332, "receita financeira", 22, C["muted"], FONT_BODY, 400),
        rect(472, 318, 14, 14, C["muted"]),
        text(494, 332, "despesa contratada", 22, C["muted"], FONT_BODY, 400),
    ]
    for tick in (0, 60, 120):
        x = median_x + median_w * tick / 120
        body += [
            text(x, 367, "R$ 0" if tick == 0 else f"R$ {tick} mil",
                 22, C["muted"], FONT_DATA, 500, "middle"),
            line(x, 378, x, 564, C["grid"], 1),
        ]
    for label, color, y in [
        ("Mulheres", C["rust"], 437),
        ("Homens", C["teal_dark"], 538),
    ]:
        body.append(text(64, y, label, 30, color, FONT_BODY, 700))
    for row, group_color, bar_color, y, field in [
        (women, C["rust"], "#D8ABA0", 390, "financial_receipts_median_centavos"),
        (women, C["rust"], C["rust"], 429, "contracted_expenses_median_centavos"),
        (men, C["teal_dark"], "#8DACA7", 491, "financial_receipts_median_centavos"),
        (men, C["teal_dark"], C["teal_dark"], 530, "contracted_expenses_median_centavos"),
    ]:
        median = Decimal(row[field]) / 100
        bar_end = median_x + float(median / median_max) * median_w
        value_label = f"R$ {br(median / Decimal('1000'), 1)} mil"
        body += [
            rect(median_x, y, bar_end - median_x, 34, bar_color, 4),
            text(bar_end + 14, y + 26, value_label, 28, group_color, FONT_BODY, 700),
        ]

    body.append(text(64, 633, "Participação no total", 30, C["ink"], FONT_BODY, 700))
    body += [
        rect(240, 661, 14, 14, "#B9BFC2"),
        text(262, 675, "das candidaturas", 22, C["muted"], FONT_BODY, 400),
        rect(472, 661, 14, 14, C["muted"]),
        text(494, 675, "dos eleitos", 22, C["muted"], FONT_BODY, 400),
    ]
    rate_x, rate_w = 240, 640
    for tick in (0, 50, 100):
        x = rate_x + rate_w * tick / 100
        body += [
            text(x, 712, f"{tick}%", 22, C["muted"], FONT_DATA, 500, "middle"),
            line(x, 723, x, 885, C["grid"], 1),
        ]
    election_shares = {"FEMININO": "17.6", "MASCULINO": "82.4"}
    for row, label, color, pale, candidate_pct, elected_count_word, y, label_y in [
        (women, "Mulheres", C["rust"], "#D8ABA0", Decimal("35.5"), "eleitas", 727, 774),
        (men, "Homens", C["teal_dark"], "#8DACA7", Decimal("64.5"), "eleitos", 812, 859),
    ]:
        body.append(text(64, label_y, label, 30, color, FONT_BODY, 700))
        for pct, fill, bar_y, count_text in [
            (candidate_pct, pale, y, None),
            (Decimal(election_shares[row["group_value"]]), color, y + 39, f'{row["elected_candidates"]} {elected_count_word}'),
        ]:
            bar_end = rate_x + float(pct / Decimal("100")) * rate_w
            label_x = bar_end + 14
            if count_text is None:
                candidate_count = f'{br(Decimal(row["candidate_count"]), 0)} candidaturas'
                body += [
                    rect(rate_x, bar_y, bar_end - rate_x, 34, fill, 4),
                    rect(label_x - 6, bar_y + 1, 330, 32, C["paper"]),
                    (
                        f'<text x="{label_x:.1f}" y="{bar_y + 26}" font-family="{FONT_BODY}" '
                        f'font-size="28" font-weight="700" fill="{color}">'
                        f'<tspan>{br(pct, 1)}%</tspan>'
                        f'<tspan font-size="22" font-weight="400"> {html.escape(candidate_count)}</tspan>'
                        f'</text>'
                    ),
                ]
            else:
                body += [
                    rect(rate_x, bar_y, bar_end - rate_x, 34, fill, 4),
                    rect(label_x - 6, bar_y + 1, 236, 32, C["paper"]),
                    (
                        f'<text x="{label_x:.1f}" y="{bar_y + 26}" font-family="{FONT_BODY}" '
                        f'font-size="28" font-weight="700" fill="{color}">'
                        f'<tspan>{br(pct, 1)}%</tspan>'
                        f'<tspan font-size="22" font-weight="400"> {html.escape(count_text)}</tspan>'
                        f'</text>'
                    ),
                ]
    body += [
        f'<text x="64" y="949" font-family="{FONT_BODY}" font-size="24" font-weight="400" fill="{C["ink"]}">'
        '<tspan>Receitas e despesas medianas parecidas, mas participação diferente:</tspan></text>',
        f'<text x="64" y="987" font-family="{FONT_BODY}" font-size="24" font-weight="400" fill="{C["ink"]}">'
        '<tspan>mulheres eram </tspan>'
        '<tspan font-weight="700" fill="#B34F3D">35,5%</tspan>'
        '<tspan> das candidaturas e </tspan>'
        '<tspan font-weight="700" fill="#B34F3D">17,6%</tspan>'
        '<tspan> dos eleitos.</tspan></text>',
    ]

    body.append(line(64, 1050, 1016, 1050, C["line"], 2))
    notes = [
        (1085, "Mediana: valor central do grupo; proximidade não significa valores iguais para cada candidatura."),
        (1109, "Participação no total: parcela de cada grupo entre todas as candidaturas e entre todos os eleitos."),
        (1133, "Comparação descritiva; não demonstra que gênero ou despesa causou o resultado."),
        (1157, "Gênero conforme o registro de candidatura no TSE (feminino ou masculino);"),
        (1181, "a base não identifica pessoas trans ou não binárias."),
        (1205, "Fonte: TSE 2022 · candidaturas APTO; receitas financeiras e despesas contratadas finais observadas."),
    ]
    body += [text(64, y, note, 20, C["muted"], FONT_BODY, 400) for y, note in notes]
    return frame(
        6, "Receitas e despesas medianas parecidas, quem se candidata é quem se elege?",
        "Candidaturas a deputado federal, 2022 · comparação descritiva",
        body,
        [],
        "",
        title_lines=["Receitas e despesas medianas parecidas,", "quem se candidata é quem se elege?"],
        page_label="06 / 08",
        title_size=40,
        body_separator_y=None,
    )
def sex_support_rows(groups: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[str]]:
    fields = [
        "group_value", "candidate_count", "financial_receipt_candidates",
        "financial_receipt_coverage_pct", "no_financial_receipt_candidates",
        "financial_receipts_median_centavos", "expense_observed_candidates",
        "expense_coverage_pct", "contracted_expenses_median_centavos",
        "elected_candidates", "elected_denominator", "elected_pct",
    ]
    rows = [
        {field: row[field] for field in fields}
        for row in groups if row["group_type"] == "sexo"
    ]
    return rows, fields






def race_rows(groups: list[dict[str, str]]) -> tuple[list[dict[str, str]], dict[str, str]]:
    wanted = ["BRANCA", "PRETA", "PARDA", "AMARELA", "INDÍGENA", "NÃO INFORMADO", "NÃO DIVULGÁVEL", "PRETAS + PARDAS"]
    lookup = {row["group_value"]: row for row in groups if row["group_type"] == "raça/cor"}
    rows = [lookup[key] for key in wanted]
    return rows, lookup["TODOS"]



def race_svg(groups: list[dict[str, str]]) -> str:
    rows, total = race_rows(groups)
    lookup = {row["group_value"]: row for row in rows}
    white, black = lookup["BRANCA"], lookup["PRETAS + PARDAS"]
    expected = {
        "BRANCA": ("10000000", "9235853", "7.75", "50,9", "363"),
        "PRETAS + PARDAS": ("5300000", "4999685", "3.17", "47,6", "139"),
    }
    for group in (white, black):
        observed = (
            group["financial_receipts_median_centavos"],
            group["contracted_expenses_median_centavos"],
            str(Decimal(group["elected_pct"]).quantize(Decimal("0.01"))),
            br(Decimal(group["reference_population_coverage_pct"]), 1),
            group["elected_candidates"],
        )
        if observed != expected[group["group_value"]]:
            raise ValueError(f"Os resultados raciais existentes mudaram para {group['group_value']}.")
    if total["candidate_count"] != "9204" or total["elected_candidates"] != "510":
        raise ValueError("O recorte existente de raça/cor mudou.")

    body = [text(64, 287, "Receita e despesa medianas",
                 30, C["ink"], FONT_BODY, 700)]
    body += [
        rect(240, 318, 14, 14, "#B9BFC2"),
        text(262, 332, "receita financeira", 22, C["muted"], FONT_BODY, 400),
        rect(472, 318, 14, 14, C["muted"]),
        text(494, 332, "despesa contratada", 22, C["muted"], FONT_BODY, 400),
    ]
    median_x, median_w, median_max = 240, 640, Decimal("120000")
    for tick in (0, 60, 120):
        x = median_x + median_w * tick / 120
        body += [
            text(x, 367, "R$ 0" if tick == 0 else f"R$ {tick} mil",
                 22, C["muted"], FONT_DATA, 500, "middle"),
            line(x, 378, x, 564, C["grid"], 1),
        ]

    for row, label, color, receipt_color, receipt_y, expense_y, label_y in [
        (white, "Brancas", "#2F5D8A", "#9DB1C3", 390, 429, 437),
        (black, "Negras", "#6B4A8F", "#B8A9C5", 491, 530, 538),
    ]:
        body.append(text(64, label_y, label, 30, color, FONT_BODY, 700))
        for y, field, bar_color in [
            (receipt_y, "financial_receipts_median_centavos", receipt_color),
            (expense_y, "contracted_expenses_median_centavos", color),
        ]:
            median = Decimal(row[field]) / 100
            bar_end = median_x + float(median / median_max) * median_w
            value_label = f"R$ {br(median / Decimal('1000'), 1)} mil"
            label_x = bar_end + 14
            body += [
                rect(median_x, y, bar_end - median_x, 34, bar_color, 4),
                rect(label_x - 7, y + 1, 176, 32, C["paper"]),
                text(label_x, y + 26, value_label, 28, color, FONT_BODY, 700),
            ]

    body.append(text(64, 633, "Participação no total", 30, C["ink"], FONT_BODY, 700))
    body += [
        rect(240, 661, 14, 14, "#B9BFC2"),
        text(262, 675, "das candidaturas", 22, C["muted"], FONT_BODY, 400),
        rect(472, 661, 14, 14, C["muted"]),
        text(494, 675, "dos eleitos", 22, C["muted"], FONT_BODY, 400),
    ]
    rate_x, rate_w = 240, 640
    for tick in (0, 50, 100):
        x = rate_x + rate_w * tick / 100
        body += [
            text(x, 712, f"{tick}%", 22, C["muted"], FONT_DATA, 500, "middle"),
            line(x, 723, x, 885, C["grid"], 1),
        ]
    election_shares = {"BRANCA": "71.2", "PRETAS + PARDAS": "27.3"}
    for row, label, color, pale, candidate_pct, elected_count, y, label_y in [
        (white, "Brancas", "#2F5D8A", "#9DB1C3", Decimal("50.9"), "363 eleitos", 727, 774),
        (black, "Negras", "#6B4A8F", "#B8A9C5", Decimal("47.6"), "139 eleitos", 812, 859),
    ]:
        body.append(text(64, label_y, label, 30, color, FONT_BODY, 700))
        for pct, fill, bar_y, count_text in [
            (candidate_pct, pale, y, None),
            (Decimal(election_shares[row["group_value"]]), color, y + 39, elected_count),
        ]:
            bar_end = rate_x + float(pct / Decimal("100")) * rate_w
            label_x = bar_end + 14
            if count_text is None:
                candidate_count = f'{br(Decimal(row["candidate_count"]), 0)} candidaturas'
                body += [
                    rect(rate_x, bar_y, bar_end - rate_x, 34, fill, 4),
                    rect(label_x - 6, bar_y + 1, 330, 32, C["paper"]),
                    (
                        f'<text x="{label_x:.1f}" y="{bar_y + 26}" font-family="{FONT_BODY}" '
                        f'font-size="28" font-weight="700" fill="{color}">'
                        f'<tspan>{br(pct, 1)}%</tspan>'
                        f'<tspan font-size="22" font-weight="400"> {html.escape(candidate_count)}</tspan>'
                        f'</text>'
                    ),
                ]
            else:
                body += [
                    rect(rate_x, bar_y, bar_end - rate_x, 34, fill, 4),
                    rect(label_x - 6, bar_y + 1, 236, 32, C["paper"]),
                    (
                        f'<text x="{label_x:.1f}" y="{bar_y + 26}" font-family="{FONT_BODY}" '
                        f'font-size="28" font-weight="700" fill="{color}">'
                        f'<tspan>{br(pct, 1)}%</tspan>'
                        f'<tspan font-size="22" font-weight="400"> {html.escape(count_text)}</tspan>'
                        f'</text>'
                    ),
                ]

    body += [
        f'<text x="64" y="949" font-family="{FONT_BODY}" font-size="24" font-weight="400" fill="{C["ink"]}">'
        '<tspan>Candidaturas negras tiveram receitas e despesas medianas menores que as brancas.</tspan></text>',
        f'<text x="64" y="987" font-family="{FONT_BODY}" font-size="24" font-weight="400" fill="{C["ink"]}">'
        '<tspan>Eram </tspan>'
        '<tspan font-weight="700" fill="#6B4A8F">47,6%</tspan>'
        '<tspan> das candidaturas, mas só </tspan>'
        '<tspan font-weight="700" fill="#6B4A8F">27,3%</tspan>'
        '<tspan> dos eleitos.</tspan></text>',
    ]

    body.append(line(64, 1050, 1016, 1050, C["line"], 2))
    notes = [
        (1109, "Mediana: valor central do grupo; não indica o que cada candidatura recebeu ou gastou."),
        (1133, "Receita: candidaturas com receita observada. Participação: parcela entre candidaturas e eleitos."),
        (1157, "Comparação descritiva; não demonstra que raça/cor ou dinheiro causou o resultado."),
        (1181, "Brancas e negras somam ~98% das candidaturas e dos eleitos; demais categorias: ver apoio."),
        (1205, "Fonte: TSE 2022 · candidaturas APTO; receitas financeiras e despesas contratadas finais observadas."),
    ]
    body += [text(64, y, note, 20, C["muted"], FONT_BODY, 400) for y, note in notes]
    return frame(
        7,
        "Receitas e despesas medianas diferentes, quem se candidata é quem se elege?",
        "Candidaturas de mulheres e homens a deputado federal, 2022 · negras = pretas ou pardas",
        body,
        [],
        "",
        title_lines=[
            "Receitas e despesas medianas diferentes,",
            "quem se candidata é quem se elege?",
        ],
        page_label="07 / 08",
        title_size=40,
        body_separator_y=None,
    )

    body = [
        text(64, 270, "Receita financeira mediana", 30, C["ink"], FONT_BODY, 700),
        text(64, 305, "Entre candidaturas com receita observada", 22, C["muted"], FONT_BODY, 500),
    ]
    receipt_x, receipt_w, receipt_max = 250, 500, Decimal("120000")
    for tick in (0, 60, 120):
        x = receipt_x + receipt_w * tick / 120
        body += [
            text(x, 342, "R$ 0" if tick == 0 else f"R$ {tick} mil",
                 22, C["muted"], FONT_DATA, 500, "middle"),
            line(x, 353, x, 520, C["line"], 1),
        ]
    for row, label, color, y in [
        (white, "Brancas", C["teal_dark"], 392),
        (black, "Negras", C["rust"], 472),
    ]:
        median = Decimal(row["financial_receipts_median_centavos"]) / 100
        body += [
            text(64, y + 22, label, 32, color, FONT_BODY, 700),
            rect(receipt_x, y, receipt_w, 26, C["white"], 3, C["line"], 1),
            rect(receipt_x, y, float(median / receipt_max) * receipt_w, 26, color, 3),
            text(1016, y + 28, f"R$ {br(median / Decimal('1000'), 0)} mil",
                 36, color, FONT_DATA, 700, "end"),
        ]

    body += [
        text(64, 635, "Proporção eleita", 30, C["ink"], FONT_BODY, 700),
        text(64, 670, "Sobre todas as candidaturas de cada grupo · eixo de 0% a 100%",
             22, C["muted"], FONT_BODY, 500),
    ]
    rate_x, rate_w = 250, 610
    for tick in (0, 25, 50, 75, 100):
        x = rate_x + rate_w * tick / 100
        body += [
            text(x, 708, f"{tick}%", 22, C["muted"], FONT_DATA, 500, "middle"),
            line(x, 720, x, 934, C["line"], 1),
        ]
    for row, label, color, y in [
        (white, "Brancas", C["teal_dark"], 780),
        (black, "Negras", C["rust"], 875),
    ]:
        pct = Decimal(row["elected_pct"])
        body += [
            text(64, y + 21, label, 32, color, FONT_BODY, 700),
            rect(rate_x, y, rate_w, 28, C["white"], 3, C["line"], 1),
            rect(rate_x, y, float(pct / 100) * rate_w, 28, color, 3),
            text(1016, y + 29, f"{br(pct, 2)}%", 36, color, FONT_DATA, 700, "end"),
        ]
    return frame(
        7, "Receitas e eleição por raça/cor",
        "Candidaturas negras = autodeclaradas pretas ou pardas.",
        body,
        ["Receitas medianas: candidaturas com receita observada; proporção eleita: total de cada grupo.",
         "Contagens, cobertura e categorias originais estão no apoio metodológico."],
        "Fonte: TSE 2022 · receitas financeiras e resultados eleitorais · APTO/Final.",
        title_lines=["Receitas e eleição", "por raça/cor"],
        page_label="07 / 08", title_size=42)




def compact_count(value: int) -> str:
    if value >= 1000000:
        return f"{br(Decimal(value) / Decimal('1000000'), 1)} mi"
    if value >= 1000:
        return f"{br(Decimal(value) / Decimal('1000'), 0)} mil"
    return str(value)


def scatter_svg(rows: list[dict[str, str]], ufs: list[str], page_label: str) -> str:
    by_uf: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_uf.setdefault(row["uf"], []).append(row)
    if set(by_uf) != {"SP", "MG", "RJ", "BA"} or len(ufs) != 2:
        raise ValueError("Os scatterplots devem conter os quatro painéis estaduais conferidos.")
    rj_min = min((row for row in by_uf["RJ"] if row["elected"] == "1"),
                 key=lambda row: int(row["expense_centavos"]))
    if (rj_min["sq_candidate"] != "190001738867"
            or rj_min["expense_centavos"] != "6438500"
            or rj_min["valid_nominal_votes"] != "94221"
            or rj_min["expense_observation"] != "observed"
            or rj_min["candidate_total_status_code"] != "2"):
        raise ValueError("O ponto eleito de menor despesa no RJ diverge do registro conferido.")
    max_expense_brl = max(int(row["expense_centavos"]) for row in rows) / 100
    x_max = max(3500000, math.ceil(max_expense_brl / 1000000) * 1000000)
    panel_w, panel_h = 462, 680
    panel_xs, panel_y = [64, 554], 255
    body: list[str] = []
    for index, uf in enumerate(ufs):
        subset = by_uf[uf]
        px = panel_xs[index]
        py = panel_y
        plot_x, plot_y = px + 102, py + 142
        plot_w, plot_h = 328, 420
        votes_max = max(int(row["valid_nominal_votes"]) for row in subset)
        y_max = max(250000, math.ceil(votes_max / 250000) * 250000)
        elected_n = sum(int(row["elected"]) for row in subset)
        body += [
            rect(px, py, panel_w, panel_h, C["white"], 4, C["line"], 2),
            text(px + 20, py + 42, uf, 30, C["ink"], FONT_BODY, 700),
            text(px + panel_w - 20, py + 40,
                 f"N={len(subset):,} · eleitos {elected_n}".replace(",", "."),
                 18, C["muted"], FONT_DATA, 500, "end"),
            f'<text x="{px + 21}" y="{plot_y + plot_h / 2}" transform="rotate(-90 {px + 21} {plot_y + plot_h / 2})" font-family="{FONT_BODY}" font-size="16" fill="{C["muted"]}" text-anchor="middle">Votos recebidos · linear</text>',
        ]
        for vote_tick in (0, y_max // 2, y_max):
            y = plot_y + plot_h - (vote_tick / y_max) * plot_h
            body += [
                line(plot_x, y, plot_x + plot_w, y, C["line"], 1),
                text(plot_x - 10, y + 6, compact_count(vote_tick),
                     16, C["muted"], FONT_DATA, 400, "end"),
            ]
        expense_ticks = list(range(0, x_max + 1, 1000000))
        if expense_ticks[-1] != x_max:
            expense_ticks.append(x_max)
        for expense_tick in expense_ticks:
            x = plot_x + (expense_tick / x_max) * plot_w
            tick_label = "0" if expense_tick == 0 else f"R$ {expense_tick // 1000000} mi"
            body += [
                line(x, plot_y, x, plot_y + plot_h, C["line"], 1),
                text(x, plot_y + plot_h + 24, tick_label,
                     16, C["muted"], FONT_DATA, 400, "middle"),
            ]
        if any(int(row["expense_centavos"]) / 100 > x_max
               or int(row["valid_nominal_votes"]) > y_max for row in subset):
            raise ValueError(f"Há pontos fora dos eixos no painel {uf}.")
        for row in sorted(subset, key=lambda item: int(item["elected"])):
            x = plot_x + (int(row["expense_centavos"]) / 100 / x_max) * plot_w
            y = plot_y + plot_h - (int(row["valid_nominal_votes"]) / y_max) * plot_h
            color = C["teal_dark"] if row["elected"] == "1" else C["rust"]
            opacity = "0.82" if row["elected"] == "1" else "0.35"
            body.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3.6" fill="{color}" fill-opacity="{opacity}"/>')
        body.append(text(px + panel_w / 2, plot_y + plot_h + 62,
                         "Despesa contratada declarada (R$) · linear",
                         16, C["ink"], FONT_BODY, 500, "middle"))
    body += [
        f'<circle cx="408" cy="1010" r="8" fill="{C["teal_dark"]}"/>',
        text(429, 1017, "Eleitos", 20, C["teal_dark"], FONT_BODY, 600),
        f'<circle cx="590" cy="1010" r="8" fill="{C["rust"]}"/>',
        text(611, 1017, "Não eleitos", 20, C["rust"], FONT_BODY, 600),
    ]
    region = " · ".join(ufs)
    return frame(6 if ufs[0] == "SP" else 7, f"Despesas contratadas e votos · {region}",
                 "Cada ponto é uma candidatura · cores: eleitos e não eleitos",
                 body,
                 [f"Eixos lineares; X comum de R$ 0 a R$ {br(Decimal(x_max) / Decimal(1000000), 0)} mi, Y próprio por UF.",
                  "Todos os pontos estão dentro da janela; valores ausentes não foram convertidos em zero."],
                 "Fonte: TSE 2022 · recorte eleitoral N=9.202; votos nominais válidos; junção 1:1.",
                 title_lines=["Despesas contratadas e votos", region],
                 page_label=page_label)
def load_national_scatter_rows() -> list[dict[str, str]]:
    candidates = read_csv(REPORTS / "tse-2022-election-powerbi-candidates.csv")
    if len(candidates) != 9202 or len({row["sq_candidate"] for row in candidates}) != 9202:
        raise ValueError("O recorte nacional deve conter 9.202 candidaturas únicas.")

    database = ROOT / "data" / "derived" / "2022" / "pilot.sqlite"
    connection = sqlite3.connect(f"{database.as_uri()}?mode=ro", uri=True)
    try:
        connection.execute("CREATE TEMP TABLE selected (sq_candidate TEXT PRIMARY KEY)")
        connection.executemany(
            "INSERT INTO selected VALUES (?)",
            ((row["sq_candidate"],) for row in candidates),
        )
        denominators = {
            row[0]: (int(row[1]), int(row[2]), int(row[3]))
            for row in connection.execute(
                "SELECT uf, valid_nominal_votes, valid_legend_votes, valid_votes_total "
                "FROM vote_denominators"
            )
        }
        if len(denominators) != 27 or any(
            nominal + legend != total for nominal, legend, total in denominators.values()
        ):
            raise ValueError("Os denominadores oficiais não reconciliam votos nominais e de legenda.")
        vote_rows = connection.execute(
            "SELECT votes.sq_candidate, SUM(votes.nominal_votes), COUNT(*) "
            "FROM selected JOIN votes USING (sq_candidate) "
            "GROUP BY votes.sq_candidate"
        ).fetchall()
    finally:
        connection.close()

    votes = {row[0]: (int(row[1] or 0), int(row[2])) for row in vote_rows}
    if len(votes) != len(candidates):
        raise ValueError("Há candidaturas sem votação nominal observada; não converter para zero.")

    result = []
    for row in candidates:
        uf = row["uf"]
        if uf not in denominators:
            raise ValueError(f"UF sem denominador oficial: {uf}.")
        status = row["candidate_total_status_code"]
        elected = int(row["elected"])
        if status not in {"2", "3", "4", "5"} or elected != int(status in {"2", "3"}):
            raise ValueError(f"Resultado eleitoral inconsistente para {row['sq_candidate']}.")
        nominal_votes, vote_rows_count = votes[row["sq_candidate"]]
        if vote_rows_count == 0 or int(denominators[uf][2]) <= 0:
            raise ValueError(f"Votação ou denominador ausente para {row['sq_candidate']}.")
        result.append({
            "sq_candidate": row["sq_candidate"],
            "uf": uf,
            "expense_centavos": row["expense_deduplicated_centavos"],
            "valid_nominal_votes": str(nominal_votes),
            "valid_votes_denominator": str(denominators[uf][2]),
            "elected": str(elected),
        })
    return result


def scatter_national_svg(rows: list[dict[str, str]], page_label: str) -> str:
    if len(rows) != 9202 or len({row["sq_candidate"] for row in rows}) != 9202:
        raise ValueError("O scatter nacional deve representar as 9.202 candidaturas do recorte.")
    elected_count = sum(int(row["elected"]) for row in rows)
    if elected_count != 510 or len({row["uf"] for row in rows}) != 27:
        raise ValueError("O scatter nacional deve cobrir 27 UFs e os 510 eleitos do recorte.")

    x_max, y_max = 3_500_000, 15.0
    points = [
        (
            int(row["expense_centavos"]) / 100,
            100 * int(row["valid_nominal_votes"]) / int(row["valid_votes_denominator"]),
            row["elected"] == "1",
        )
        for row in rows
    ]
    max_expense = max(x for x, _, _ in points)
    max_share = max(y for _, y, _ in points)
    if max_expense > x_max or max_share > y_max:
        raise ValueError("Há candidaturas fora dos eixos lineares; não as omitir.")

    plot_x, plot_y, plot_w, plot_h = 166, 270, 838, 590
    body = []
    for tick in range(0, 16, 3):
        y = plot_y + plot_h - (tick / y_max) * plot_h
        body += [
            line(plot_x, y, plot_x + plot_w, y, C["grid"], 1),
            text(plot_x - 14, y + 7, f"{tick}%", 20, C["muted"], FONT_DATA, 500, "end"),
        ]
    for tick in (0, 1_000_000, 2_000_000, 3_000_000, 3_500_000):
        x = plot_x + (tick / x_max) * plot_w
        label = "R$ 0" if tick == 0 else (
            f"R$ {br(Decimal(tick) / Decimal(1_000_000), 1 if tick % 1_000_000 else 0)} mi"
        )
        body += [
            line(x, plot_y, x, plot_y + plot_h, C["grid"], 1),
            text(x, plot_y + plot_h + 34, label, 20, C["muted"], FONT_DATA, 500, "middle"),
        ]

    for expense, share, elected in sorted(points, key=lambda point: point[2]):
        x = plot_x + (expense / x_max) * plot_w
        y = plot_y + plot_h - (share / y_max) * plot_h
        color = C["teal_dark"] if elected else C["rust"]
        radius = "2.8" if elected else "2.2"
        opacity = "0.76" if elected else "0.24"
        body.append(
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{radius}" fill="{color}" fill-opacity="{opacity}"/>'
        )

    body += [
        f'<text x="73" y="{plot_y + plot_h / 2}" transform="rotate(-90 73 {plot_y + plot_h / 2})" font-family="{FONT_BODY}" font-size="22" fill="{C["ink"]}" text-anchor="middle">Parcela dos votos válidos do estado (%)</text>',
        text(plot_x + plot_w / 2, 939, "Despesa contratada declarada (R$)",
             22, C["ink"], FONT_BODY, 600, "middle"),
        f'<circle cx="330" cy="998" r="8" fill="{C["teal_dark"]}"/>',
        text(350, 1006, "Eleitos · 510", 21, C["teal_dark"], FONT_BODY, 600),
        f'<circle cx="540" cy="998" r="8" fill="{C["rust"]}"/>',
        text(560, 1006, "Não eleitos · 8.692", 21, C["rust"], FONT_BODY, 600),
    ]
    return frame(
        5, "Mais despesas, mais votos?",
        "Cada ponto é uma candidatura a deputado federal em 2022.",
        body,
        [
            "3% = 3 em cada 100 votos válidos para deputado federal naquele estado.",
            "Candidaturas com despesas parecidas tiveram votações muito diferentes.",
        ],
        "Fonte: TSE 2022 · recorte eleitoral de 9.202 candidaturas · votação nominal e denominadores oficiais por UF.",
        title_lines=["Mais despesas,", "mais votos?"],
        page_label=page_label,
        title_size=42,
    )





def conclusion_svg(counterpoint: list[dict[str, str]], groups: list[dict[str, str]],
                  party_rows: list[dict[str, str]]) -> str:
    by_metric = {row["metric"]: row for row in counterpoint}
    by_group = {row["group_value"]: row for row in groups}
    elected_high = by_metric["Eleitos acima de R$ 1 milhão"]
    non_elected_high = by_metric["Não eleitos entre candidatos acima de R$ 1 milhão"]
    women, men = by_group["FEMININO"], by_group["MASCULINO"]
    white, black = by_group["BRANCA"], by_group["PRETAS + PARDAS"]
    party_by_abbrev = {row["party_abbrev"]: row for row in party_rows}
    union, pl = party_by_abbrev["UNIÃO"], party_by_abbrev["PL"]

    if (int(elected_high["numerator"]) != 420 or int(elected_high["denominator"]) != 510
            or int(non_elected_high["numerator"]) != 567
            or int(non_elected_high["denominator"]) != 987):
        raise ValueError("Os denominadores das conclusões eleitorais mudaram.")

    expected_groups = {
        "FEMININO": (3266, 90),
        "MASCULINO": (5936, 420),
        "BRANCA": (4681, 363),
        "PRETAS + PARDAS": (4381, 139),
    }
    for name, (candidate_count, elected_count) in expected_groups.items():
        row = by_group[name]
        if (int(row["candidate_count"]) != candidate_count
                or int(row["elected_candidates"]) != elected_count):
            raise ValueError("As contagens de gênero ou raça/cor da conclusão mudaram.")

    party_ranking = sorted(
        party_rows,
        key=lambda row: (-int(row["expense_centavos"]), row["party_abbrev"]),
    )
    if (party_ranking[6]["party_abbrev"] != "PL"
            or int(union["expense_centavos"]) != 49288695116
            or int(union["elected_count"]) != 57
            or int(pl["expense_centavos"]) != 21393156350
            or int(pl["elected_count"]) != 98):
        raise ValueError("Os valores de despesa ou eleitos dos partidos mudaram.")

    statements = [
        ("1", [
            "Os líderes em despesas e em número de eleitos",
            "foram diferentes.",
        ], [
            f"As candidaturas da UNIÃO somaram R$ {br(Decimal(union['expense_centavos']) / Decimal('100000000'), 1)} milhões e 57 eleitos;",
            f"as do PL, R$ {br(Decimal(pl['expense_centavos']) / Decimal('100000000'), 1)} milhões e 98 eleitos.",
        ]),
        ("2", [
            "Declarar mais de R$ 1 milhão em despesas",
            "não garantiu a eleição.",
        ], [
            f"Embora {br(Decimal(elected_high['share_pct']), 1)}% dos eleitos analisados tenham declarado",
            f"despesas acima desse valor, {br(Decimal(non_elected_high['share_pct']), 1)}% dos candidatos que",
            "também ultrapassaram R$ 1 milhão não se elegeram.",
        ]),
        ("3", [
            "Entre quem concorreu e quem se elegeu,",
            "a representação ficou mais masculina e branca.",
        ], [
            "Mulheres e candidaturas negras tiveram participação menor",
            "entre os eleitos do que entre as candidaturas analisadas.",
        ]),
    ]
    body = []
    for index, (number, headline, support) in enumerate(statements):
        y = 260 + index * 220
        body += [
            rect(64, y, 952, 205, C["white"] if index != 1 else C["teal_pale"], 4, C["line"], 2),
            text(95, y + 116, number, 58, C["teal_dark"], FONT_DISPLAY, 700),
        ]
        for line_index, statement in enumerate(headline):
            body.append(text(170, y + 52 + line_index * 34, statement,
                             30, C["ink"], FONT_BODY, 700))
        for line_index, statement in enumerate(support):
            body.append(text(170, y + 132 + line_index * 29, statement,
                             23, C["muted"], FONT_BODY, 500))
    return frame(
        8, "O que os dados mostram",
        "Três padrões nas candidaturas a deputado federal em 2022",
        body,
        ["Comparações descritivas do recorte analisado; não demonstram causalidade nem eficiência dos gastos."],
        "Fonte: TSE 2022 · despesas contratadas declaradas e resultados eleitorais.")


def cost_per_vote_svg() -> str:
    rows = read_csv(REPORTS / "tse-2022-election-expense-comparison.csv")
    selected = {row["outcome"]: row for row in rows if row["scenario"] == "deduplicado"}
    elected, not_elected = selected["eleitos"], selected["nao_eleitos"]
    if (Decimal(elected["cost_per_vote_median_brl"]).quantize(Decimal("0.01")) != Decimal("17.79")
            or Decimal(not_elected["cost_per_vote_median_brl"]).quantize(Decimal("0.01")) != Decimal("46.75")):
        raise ValueError("As medianas do resumo existente mudaram.")
    elected_n = int(elected["cost_per_vote_n_positive_votes"])
    not_elected_n = int(not_elected["cost_per_vote_n_positive_votes"])
    not_elected_zero = int(not_elected["cost_per_vote_excluded_zero_votes"])
    if (elected_n != 510 or int(elected["candidate_count"]) != 510
            or not_elected_n != 8588 or not_elected_zero != 104
            or not_elected_n + not_elected_zero != int(not_elected["candidate_count"])):
        raise ValueError("A cobertura do custo mediano por voto não reconcilia.")

    body = [text(64, 287, "Despesa contratada por voto recebido",
                 30, C["ink"], FONT_BODY, 700)]
    axis_x, axis_w = 240, 640
    for tick, label in [(0, "R$ 0"), (25, "R$ 25"), (50, "R$ 50")]:
        x = axis_x + axis_w * tick / 50
        body += [
            text(x, 367, label, 22, C["muted"], FONT_DATA, 500, "middle"),
            line(x, 376, x, 386, C["grid"], 1),
        ]
    body.append(line(axis_x, 381, axis_x + axis_w, 381, C["line"], 1))

    for row, label, color, y in [
        (elected, "Eleitos", C["teal_dark"], 432),
        (not_elected, "Não eleitos", C["rust"], 508),
    ]:
        median = Decimal(row["cost_per_vote_median_brl"])
        bar_end = axis_x + float(median / Decimal("50")) * axis_w
        value_x = bar_end + 14
        body += [
            text(64, y + 33, label, 30, color, FONT_BODY, 700),
            rect(axis_x, y, bar_end - axis_x, 44, color, 4),
            text(value_x, y + 35, f"R$ {br(median, 2)}", 36, color, FONT_BODY, 700),
            text(value_x, y + 63, "por voto", 24, color, FONT_BODY, 400),
        ]

    body += [
        text(64, 780, "Entre os não eleitos, a despesa mediana por voto foi mais que o dobro da dos eleitos.",
             24, C["ink"], FONT_BODY, 400),
        text(64, 816, "Não é preço do voto nem custo só público: eleitos tiveram, em geral, muito mais votos.",
             22, C["ink"], FONT_BODY, 400),
        line(64, 1050, 1016, 1050, C["line"], 2),
        text(64, 1109, "Mediana individual: cada candidatura divide a própria despesa pelos próprios votos;",
             20, C["muted"], FONT_BODY, 400),
        text(64, 1133, "não é soma de despesas ÷ soma de votos.",
             20, C["muted"], FONT_BODY, 400),
        text(64, 1157, "Eleitos: 510 candidaturas; não eleitos: 8.588. Candidaturas sem voto positivo ficam fora do cálculo.",
             20, C["muted"], FONT_BODY, 400),
        text(64, 1181, "Comparação descritiva; não demonstra que a despesa causou o resultado.",
             20, C["muted"], FONT_BODY, 400),
        text(64, 1205, "Fonte: TSE 2022 · despesa contratada (cenário principal) e votos nominais positivos.",
             20, C["muted"], FONT_BODY, 400),
    ]
    return frame(
        8,
        "Quem se elege declara menos por voto?",
        "Despesa contratada dividida pelos votos positivos · mediana entre candidaturas",
        body,
        [],
        "",
        title_lines=["Quem se elege declara", "menos por voto?"],
        page_label="DADO DE APOIO",
        title_size=40,
        body_separator_y=None,
    )




def methodology() -> str:
    return f'''# Carrossel TSE 2022 — versão 4

**Estado:** 8 lâminas, 1080 × 1350 px (4:5), em `reports/linkedin-carousel-2022/v4/`. Esta é a única versão mantida do carrossel.

## Ordem do carrossel

1. `slide-01-capa.svg/png` — Bilhões em campanhas. Quem chegou à Câmara?
2. `slide-02-partidos.svg/png` — Quais partidos declararam mais despesas?
3. `slide-03-mapa-uf.svg/png` — Quanto declararam gastar os eleitos em cada estado?
4. `slide-04-faixas-eleicao.svg/png` — Quanto declararam gastar os candidatos que se elegeram?
5. `slide-05-scatter-rj.svg/png` — Despesas e participação nos votos válidos por UF.
6. `slide-06-sexo.svg/png` — Despesas medianas próximas; proporções diferentes.
7. `slide-07-raca-cor.svg/png` — Receitas e eleição por raça/cor.
8. `slide-08-conclusoes.svg/png` — O que os dados mostram.

## Medidas, recortes e denominadores

- Nenhuma ingestão ou modelo foi executado. Foram reutilizados os artefatos existentes; a mudança é de apresentação.
- Capa: totais existentes para 9.204 candidaturas; partidos e scatter: recorte eleitoral N=9.202; mapa, faixas e grupos usam os recortes APTO/Final e coberturas indicados abaixo. Esses denominadores não são intercambiáveis.
- Receitas financeiras são valores recebidos; despesas contratadas são gastos declarados; pagamentos realizados são uma medida distinta e não entram nos totais deste carrossel.
- Partidos: barras com os sete maiores totais de despesas contratadas dos candidatos filiados, não dos diretórios. Todos os partidos, candidatos, votos e eleitos estão no CSV de apoio; total maior ou menor não mede eficiência.
- Mapa: mediana de despesas declaradas Final entre eleitos APTO; 510/512 têm despesa observada. As duas ausências permanecem ausentes, nunca zero. Demais UFs: `apoio/medianas-demais-estados.svg`, `png/apoio/medianas-demais-estados.png` e `../data/despesas-eleitos-por-uf.csv`.
- Faixas: distribuição entre 510 eleitos; 82,4% estavam acima de R$ 1 milhão. Entre 987 candidaturas acima de R$ 1 milhão, 42,55% se elegeram e 57,45% não. Os denominadores são distintos.
- Scatter principal: Brasil, uma candidatura por ponto (N=9.202). X = despesa contratada declarada, de R$ 0 a R$ 3,5 milhões; Y = votos nominais válidos da candidatura ÷ votos válidos oficiais da UF, incluindo votos de legenda. Eixos lineares; extremos observados (R$ 3,42 milhões e 14,60%) dentro da visão geral, sem pontos omitidos.
- Sexo: proporção eleita = eleitos/candidaturas do grupo (homens 420/5.936; mulheres 90/3.266). Medianas de despesas contratadas: R$ 65,0 mil e R$ 65,6 mil. Mediana divide o grupo ao meio; não significa valores iguais para cada candidatura.
- Raça/cor: “negras” = autodeclaradas pretas ou pardas. Medianas de receitas financeiras (R$ 100 mil brancas; R$ 53 mil pretas+pardas) usam apenas candidaturas com receita observada: 4.557/4.681 e 4.170/4.381. Proporções eleitas (7,75%; 3,17%) usam todas as candidaturas de cada grupo: 363/4.681 e 139/4.381. Categorias originais, contagens e cobertura permanecem no CSV; o agregado pretas+pardas não deve ser somado de novo às categorias.
- Dado de apoio, fora do carrossel: mediana das razões individuais (despesa contratada deduplicada ÷ votos nominais positivos): R$ 17,79 entre eleitos e R$ 46,75 entre não eleitos. A mediana menor entre eleitos ocorre em boa parte porque eles têm muito mais votos. Não é preço do voto, custo público ou razão agregada; 104 candidaturas sem voto positivo não entram no cálculo.
- As comparações são descritivas; não identificam as causas dos resultados.

## Dados e gráficos de apoio

- `../data/despesas-eleitos-por-uf.csv` — medianas e cobertura das 27 UFs.
- `../data/distribuicao-eleitos-faixa.csv`, `../data/proporcao-eleita-por-faixa.csv` e `../data/contraponto-acima-1m.csv` — contagens, taxas e denominadores por faixa.
- `../data/partidos-recorte-eleitoral.csv` — candidatos, despesas contratadas, votos válidos e eleitos por partido.
- `sexo-resultados.csv` — contagens, denominadores, percentuais e medianas por sexo.
- `../data/raca-receitas-financeiras.csv` — categorias originais, pretas+pardas e coberturas.
- `../data/scatter-candidatos-quatro-ufs.csv` — observações por candidatura em SP, MG, RJ e BA.
- `apoio/scatter-sp-mg.svg`, `apoio/scatter-rj-ba.svg` e `png/apoio/*.png` — scatterplots complementares, fora da sequência principal.
- `../../tse-2022-election-expense-comparison.csv`, `apoio/custo-por-voto.svg` e `png/apoio/custo-por-voto.png` — fonte tabular e visualização mantidas como apoio, fora do carrossel.
- `../data/origem-receitas-financeiras.csv` — totais existentes de receitas financeiras.
- `carrossel-final.pdf` — oito lâminas em ordem narrativa.

## Fontes e reprodução

- [TSE — prestações de contas de candidatos 2022](https://cdn.tse.jus.br/estatistica/sead/odsele/prestacao_contas/prestacao_de_contas_eleitorais_candidatos_2022.zip)
- [TSE — votação nominal 2022](https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_candidato_munzona/votacao_candidato_munzona_2022.zip)
- [IBGE — malhas 2022](https://servicodados.ibge.gov.br/api/docs/malhas?versao=3)
- [Repositório e reprodução]({REPRO_URL})

Renderizar todas as lâminas: `python reports/render-linkedin-carousel-2022-final.py`; selecionar por número ou nome: `--slides 1,party,map,bands,scatter-rj,sex,race,conclusions`. O script atualiza os SVGs e as notas em `v4/`; o PDF e as prévias existentes também estão versionados nessa pasta.
'''


def parse_slide_selection(value: str | None) -> set[str]:
    aliases = {
        "1": "01", "2": "03", "3": "04", "4": "05", "5": "scatter-rj",
        "6": "06", "7": "07", "8": "09",
        "party": "03", "map": "04", "bands": "05", "scatter-rj": "scatter-rj",
        "sex": "06", "race": "07", "conclusions": "09",
    }
    if value is None:
        return set(FINAL_SLIDE_IDS)
    selected = set()
    for item in value.split(","):
        key = item.strip().lower()
        slide_id = aliases.get(key, key)
        if slide_id not in FINAL_SLIDE_IDS:
            raise ValueError(
                f"Lâmina inválida: {item}. Use o número final ou um ID, como party,map,bands,scatter-rj,race,conclusions."
            )
        selected.add(slide_id)
    if not selected:
        raise ValueError("Informe ao menos um ID de lâmina.")
    return selected


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Renderiza lâminas selecionadas do carrossel TSE 2022 v4 (1080×1350)."
    )
    parser.add_argument("--slides", help="IDs ou números físicos separados por vírgula; omita para renderizar todas.")
    args = parser.parse_args()
    try:
        selected = parse_slide_selection(args.slides)
    except ValueError as exc:
        parser.error(str(exc))

    if selected == {"scatter-rj"}:
        OUT.mkdir(parents=True, exist_ok=True)
        contents = scatter_national_svg(load_national_scatter_rows(), "05 / 08")
        (OUT / "slide-05-scatter-rj.svg").write_text(contents + "\n", encoding="utf-8")
        print("Rendered only slide: scatter-rj (national, 9,202 candidaturas)")
        return
    if selected == {"06"}:
        OUT.mkdir(parents=True, exist_ok=True)
        groups = read_csv(REPORTS / "tse-2022-financial-distribution-by-group.csv")
        sex_rows, sex_fields = sex_support_rows(groups)
        write_csv(OUT / "sexo-resultados.csv", sex_rows, sex_fields)
        contents = gender_svg(groups)
        (OUT / "slide-06-sexo.svg").write_text(contents + "\n", encoding="utf-8")
        print("Rendered only slide: 06")
        return
    OUT.mkdir(parents=True, exist_ok=True)
    support_dir = OUT / "apoio"
    support_dir.mkdir(parents=True, exist_ok=True)
    map_rows, band_rows, counterpoint, funding, groups = load_existing()
    (support_dir / "custo-por-voto.svg").write_text(
        cost_per_vote_svg() + "\n", encoding="utf-8")
    sex_rows, sex_fields = sex_support_rows(groups)
    write_csv(OUT / "sexo-resultados.csv", sex_rows, sex_fields)
    filenames = {
        "01": "slide-01-capa.svg",
        "03": "slide-02-partidos.svg",
        "04": "slide-03-mapa-uf.svg",
        "05": "slide-04-faixas-eleicao.svg",
        "scatter-rj": "slide-05-scatter-rj.svg",
        "06": "slide-06-sexo.svg",
        "07": "slide-07-raca-cor.svg",
        "09": "slide-08-conclusoes.svg",
    }
    party_rows = read_csv(DATA / "partidos-recorte-eleitoral.csv")
    scatter_rows = read_csv(DATA / "scatter-candidatos-quatro-ufs.csv")
    for slide_id in sorted(selected, key=FINAL_SLIDE_IDS.index):
        if slide_id == "01":
            contents = cover_svg(funding)
        elif slide_id == "03":
            contents = party_svg(party_rows)
        elif slide_id == "04":
            contents = map_svg(map_rows)
            (support_dir / "medianas-demais-estados.svg").write_text(
                map_support_svg(map_rows) + "\n", encoding="utf-8")
        elif slide_id == "05":
            contents = bands_svg(band_rows, counterpoint)
        elif slide_id == "scatter-rj":
            contents = scatter_national_svg(load_national_scatter_rows(), "05 / 08")
            (support_dir / "scatter-sp-mg.svg").write_text(
                scatter_svg(scatter_rows, ["SP", "MG"], "APOIO") + "\n", encoding="utf-8")
            (support_dir / "scatter-rj-ba.svg").write_text(
                scatter_svg(scatter_rows, ["RJ", "BA"], "APOIO") + "\n", encoding="utf-8")
        elif slide_id == "06":
            contents = gender_svg(groups)
        elif slide_id == "07":
            contents = race_svg(groups)
        else:
            contents = conclusion_svg(counterpoint, groups, party_rows)
        (OUT / filenames[slide_id]).write_text(contents + "\n", encoding="utf-8")

    (OUT / "POWERBI-IMPORT.md").write_text(methodology(), encoding="utf-8")
    print(f"Rendered final slide IDs: {', '.join(sorted(selected, key=FINAL_SLIDE_IDS.index))}")
    print(f"Updated only selected SVGs and reused support data in {OUT}")
    print("Inputs: saved 2022 results and preserved geometry; no ingestion or models.")


    
if __name__ == "__main__":
    main()
