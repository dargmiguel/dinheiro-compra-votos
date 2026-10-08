from __future__ import annotations

import csv
import io
from itertools import islice
import json
from pathlib import Path
import zipfile


TEXT_SUFFIXES = {".csv", ".txt"}
DELIMITERS = (";", "|", "\t", ",")


def _decode(raw: bytes) -> tuple[str, str]:
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            return raw.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    raise ValueError("não foi possível decodificar a amostra como UTF-8 ou latin-1")


def _delimiter(text: str) -> str:
    first_line = next((line for line in text.splitlines() if line.strip()), "")
    counts = {delimiter: first_line.count(delimiter) for delimiter in DELIMITERS}
    return max(counts, key=counts.get) if max(counts.values(), default=0) else ";"


def inspect_text_sample(raw: bytes, *, max_rows: int = 4) -> dict:
    text, encoding = _decode(raw)
    delimiter = _delimiter(text)
    rows = list(islice(csv.reader(io.StringIO(text), delimiter=delimiter), max_rows + 1))
    if not rows:
        return {"encoding": encoding, "delimiter": delimiter, "columns": [], "sample_rows": []}
    columns = [column.strip() for column in rows[0]]
    sample_rows = [dict(zip(columns, row)) for row in rows[1:] if row]
    return {
        "encoding": encoding,
        "delimiter": delimiter,
        "columns": columns,
        "sample_rows": sample_rows,
    }


def inspect_archive(path: Path, *, sample_bytes: int = 128 * 1024) -> dict:
    members = []
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            suffix = Path(info.filename).suffix.casefold()
            layout = None
            if suffix in TEXT_SUFFIXES and not info.is_dir():
                with archive.open(info) as handle:
                    raw_layout = inspect_text_sample(handle.read(sample_bytes))
                    layout = {key: value for key, value in raw_layout.items() if key != "sample_rows"}
            members.append({
                "name": info.filename,
                "size_bytes": info.file_size,
                "compressed_size_bytes": info.compress_size,
                "is_table": layout is not None,
                "layout": layout,
            })
    return {"archive_name": path.name, "members": members}

def write_layout_report(manifest_path: Path, output_path: Path) -> Path:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    reports = []
    for resource in manifest["resources"]:
        inspected = inspect_archive(Path(resource["local_path"]))
        schemas = {}
        members = []
        for member in inspected["members"]:
            compact = {
                "name": member["name"],
                "size_bytes": member["size_bytes"],
                "compressed_size_bytes": member["compressed_size_bytes"],
                "is_table": member["is_table"],
            }
            layout = member["layout"]
            if layout is not None:
                signature = (layout["encoding"], layout["delimiter"], tuple(layout["columns"]))
                schema_id = next((key for key, value in schemas.items() if value == signature), None)
                if schema_id is None:
                    schema_id = f"layout_{len(schemas) + 1}"
                    schemas[schema_id] = signature
                compact["layout_id"] = schema_id
            members.append(compact)
        report_archive = {
            "archive_name": inspected["archive_name"],
            "member_count": len(members),
            "table_member_count": sum(1 for item in members if item["is_table"]),
            "members": members,
            "layouts": {
                schema_id: {
                    "encoding": signature[0],
                    "delimiter": signature[1],
                    "columns": list(signature[2]),
                }
                for schema_id, signature in schemas.items()
            },
        }
        reports.append({
            "resource_key": resource["resource_key"],
            "resource_id": resource["resource_id"],
            "local_path": resource["local_path"],
            "archive": report_archive,
        })
    report = {
        "schema_version": 1,
        "manifest_id": manifest["manifest_id"],
        "election": manifest["election"],
        "resources": reports,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path
