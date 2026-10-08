from __future__ import annotations

import argparse
import json
from pathlib import Path
from .acquisition import acquire_core, refresh_manifest, write_inventory
from .layout import write_layout_report
from .pipeline import run_pipeline
from .report import write_exploratory_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Piloto TSE 2022: inventário, congelamento, leiautes e base analítica")
    parser.add_argument("command", choices=("inventory", "acquire", "refresh", "inspect", "run", "report"))
    parser.add_argument("--data-root", type=Path, default=Path("data"))
    parser.add_argument("--manifest", type=Path)
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
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
