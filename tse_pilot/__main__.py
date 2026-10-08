from __future__ import annotations

import argparse
import json
from pathlib import Path
from .acquisition import acquire_core, refresh_manifest, write_inventory
from .layout import write_layout_report
from .pipeline import run_pipeline
from .exploratory import run_exploratory_scenarios


def main() -> int:
    parser = argparse.ArgumentParser(description="Piloto TSE 2022: inventário, congelamento, leiautes e base analítica")
    parser.add_argument("command", choices=("inventory", "acquire", "refresh", "inspect", "run", "report", "duplicates", "explore"))
    parser.add_argument("--data-root", type=Path, default=Path("data"))
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--database", type=Path)
    parser.add_argument("--validation", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if args.command == "inventory":
        print(write_inventory(args.data_root))
    elif args.command == "refresh":
        if not args.manifest:
            parser.error("refresh exige --manifest")
        print(refresh_manifest(args.manifest))
    elif args.command == "inspect":
        if not args.manifest:
            parser.error("inspect exige --manifest")
        output = args.output or args.data_root / "layout-2022.json"
        print(write_layout_report(args.manifest, output))
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
        print(write_duplicate_diagnostics(database, args.output))
    elif args.command == "explore":
        if not args.manifest:
            parser.error("explore exige --manifest")
        validation = args.validation or args.data_root / "derived" / "2022" / "validation.json"
        output = args.output or args.data_root / "exploratory" / "2022"
        result = run_exploratory_scenarios(args.manifest, validation, output)
        print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    raise SystemExit(main())
