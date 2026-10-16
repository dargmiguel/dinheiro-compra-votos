from __future__ import annotations

import argparse
import json
from pathlib import Path
from .acquisition import acquire_core, freeze_vote_totals_2022, refresh_manifest, write_inventory
from .analysis import run_financial_analysis, write_expense_temporal_analysis
from .funding import write_funding_source_analysis
from .exploratory import run_exploratory_scenarios
from .layout import write_layout_report
from .pipeline import run_pipeline
from .report import write_exploratory_report
from .duplicates import write_duplicate_diagnostics


def main() -> int:
    parser = argparse.ArgumentParser(description="Piloto TSE 2022: inventário, congelamento, leiautes e base analítica")
    parser.add_argument("command", choices=("inventory", "acquire", "freeze-votes", "refresh", "inspect", "run", "report", "duplicates", "explore", "analyze", "expense-temporal", "funding-source"))
    parser.add_argument("--data-root", type=Path, default=Path("data"))
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--database", type=Path)
    parser.add_argument("--validation", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--archive", type=Path)
    args = parser.parse_args()

    if args.command == "inventory":
        print(write_inventory(args.data_root))
    elif args.command == "acquire":
        print(acquire_core(args.data_root))
    elif args.command == "refresh":
        if not args.manifest:
            parser.error("refresh exige --manifest")
        print(refresh_manifest(args.manifest))
    elif args.command == "inspect":
        if not args.manifest:
            parser.error("inspect exige --manifest")
        output = args.output or args.data_root / "layout-2022.json"
        print(write_layout_report(args.manifest, output))
    elif args.command == "freeze-votes":
        if not args.manifest:
            parser.error("freeze-votes exige --manifest")
        print(freeze_vote_totals_2022(args.manifest))
    elif args.command == "run":
        if not args.manifest:
            parser.error("run exige --manifest")
        output = args.output or args.data_root / "derived" / "2022"
        result = run_pipeline(args.manifest, output)
        print(json.dumps(result, ensure_ascii=False))
    elif args.command == "report":
        if not args.output:
            parser.error("report exige --output")
        print(write_exploratory_report(args.data_root / "derived" / "2022", args.output))
    elif args.command == "duplicates":
        if not args.output:
            parser.error("duplicates exige --output")
        database = args.database or args.data_root / "derived" / "2022" / "pilot.sqlite"
        write_duplicate_diagnostics(database, args.output)
        print(args.output)
        print(args.output.with_name("tse-2022-dedup-exclusions.csv"))
    elif args.command == "explore":
        if not args.manifest:
            parser.error("explore exige --manifest")
        validation = args.validation or args.data_root / "derived" / "2022" / "validation.json"
        output = args.output or args.data_root / "exploratory" / "2022"
        result = run_exploratory_scenarios(args.manifest, validation, output)
        print(json.dumps(result, ensure_ascii=False))
    elif args.command == "analyze":
        database = args.database or args.data_root / "derived" / "2022" / "pilot.sqlite"
        validation = args.validation or args.data_root / "derived" / "2022" / "validation.json"
        output = args.output or Path("reports")
        result = run_financial_analysis(database, validation, output)
        print(json.dumps(result, ensure_ascii=False))
    elif args.command == "expense-temporal":
        database = args.database or args.data_root / "derived" / "2022" / "pilot.sqlite"
        output = args.output or Path("reports")
        result = write_expense_temporal_analysis(database, output)
        print(json.dumps(result, ensure_ascii=False))
    elif args.command == "funding-source":
        if not args.archive:
            parser.error("funding-source exige --archive com o ZIP de contas congelado")
        database = args.database or args.data_root / "derived" / "2022" / "pilot.sqlite"
        output = args.output or Path("reports")
        result = write_funding_source_analysis(database, args.archive, output)
        print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    raise SystemExit(main())
