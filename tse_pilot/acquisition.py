from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
from typing import BinaryIO, Callable, Iterable, Mapping
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class ResourceSpec:
    key: str
    dataset: str
    resource_id: str
    resource_name: str
    role: str
    url: str
    filename: str
    format: str = "CSV dentro de ZIP"
    scope: str = "Brasil / todas as UFs"


CORE_RESOURCES: tuple[ResourceSpec, ...] = (
    ResourceSpec(
        key="candidates_2022",
        dataset="candidatos-2022",
        resource_id="435145fd-bc9d-446a-ac9d-273f585a0bb9",
        resource_name="Candidatos",
        role="unidade candidato-eleição",
        url="https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_2022.zip",
        filename="consulta_cand_2022.zip",
    ),
    ResourceSpec(
        key="accounts_2022",
        dataset="dadosabertos-tse-jus-br-dataset-prestacao-de-contas-eleitorais-2022",
        resource_id="e45493d5-75df-4ccf-a4b4-7b1f5213577d",
        resource_name="Prestação de contas de candidatos",
        role="gasto declarado de campanha",
        url="https://cdn.tse.jus.br/estatistica/sead/odsele/prestacao_contas/prestacao_de_contas_eleitorais_candidatos_2022.zip",
        filename="prestacao_de_contas_eleitorais_candidatos_2022.zip",
    ),
    ResourceSpec(
        key="votes_2022",
        dataset="resultados-2022",
        resource_id="40fdcf49-256a-4c81-87cf-711545bd1528",
        resource_name="Votação nominal por município e zona",
        role="votação nominal",
        url="https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_candidato_munzona/votacao_candidato_munzona_2022.zip",
        filename="votacao_candidato_munzona_2022.zip",
    ),
)

VOTE_TOTALS_RESOURCE_2022 = ResourceSpec(
    key="vote_totals_2022",
    dataset="resultados-2022",
    resource_id="ffb14f0e-85eb-4618-8031-7cb88f95e05e",
    resource_name="Votação em partido por município e zona",
    role="denominador oficial de votos válidos nominais e de legenda",
    url="https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_partido_munzona/votacao_partido_munzona_2022.zip",
    filename="votacao_partido_munzona_2022.zip",
)

ALL_RESOURCES = (*CORE_RESOURCES, VOTE_TOTALS_RESOURCE_2022)


def freeze_vote_totals_2022(
    manifest_path: Path,
    *,
    now: datetime | None = None,
    opener: Callable[..., BinaryIO] = urlopen,
) -> Path:
    manifest_path = Path(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    existing = next(
        (item for item in manifest["resources"] if item["resource_key"] == VOTE_TOTALS_RESOURCE_2022.key),
        None,
    )
    if existing is not None:
        frozen_path = Path(existing["local_path"])
        expected_hash = existing.get("file", {}).get("sha256")
        if frozen_path.is_file() and expected_hash and _sha256(frozen_path) == expected_hash:
            return manifest_path
        raise AcquisitionError("recurso de votos já está no manifesto, mas o arquivo congelado não confere")

    candidate = next(
        (item for item in manifest["resources"] if item["resource_key"] == "candidates_2022"),
        None,
    )
    if candidate is None:
        raise AcquisitionError("manifesto sem arquivo congelado de candidaturas para localizar o snapshot")
    target = Path(candidate["local_path"]).parent / VOTE_TOTALS_RESOURCE_2022.filename
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise AcquisitionError(f"arquivo de destino já existe fora do manifesto: {target}")

    timestamp = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    downloaded_at = timestamp.isoformat().replace("+00:00", "Z")
    request = Request(VOTE_TOTALS_RESOURCE_2022.url, headers={"User-Agent": "dinheiro-compra-votos/0.1"})
    partial = target.with_suffix(target.suffix + ".part")
    try:
        with opener(request) as response, partial.open("wb") as output:
            shutil.copyfileobj(response, output, length=1024 * 1024)
            headers = dict(response.headers.items())
    except Exception as exc:  # pragma: no cover - exercised by the real network run
        if partial.exists():
            partial.unlink()
        raise AcquisitionError(f"falha ao congelar total oficial de votos: {exc}") from exc
    partial.replace(target)
    manifest["resources"].append(
        build_manifest_entry(
            VOTE_TOTALS_RESOURCE_2022,
            target,
            downloaded_at=downloaded_at,
            response_headers=headers,
        )
    )
    temporary = manifest_path.with_suffix(manifest_path.suffix + ".part")
    temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(manifest_path)
    return manifest_path



class AcquisitionError(RuntimeError):
    """Raised when a source cannot be frozen without losing provenance."""


def _header(headers: Mapping[str, str], name: str) -> str | None:
    wanted = name.casefold()
    for key, value in headers.items():
        if key.casefold() == wanted:
            return value
    return None


def _sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest_entry(
    resource: ResourceSpec,
    path: Path,
    *,
    downloaded_at: str,
    response_headers: Mapping[str, str],
) -> dict:
    size_bytes = path.stat().st_size
    content_length = _header(response_headers, "Content-Length")
    sha256 = _sha256(path)
    return {
        "resource_key": resource.key,
        "dataset": resource.dataset,
        "resource_id": resource.resource_id,
        "resource_name": resource.resource_name,
        "role": resource.role,
        "url": resource.url,
        "scope": resource.scope,
        "local_path": path.as_posix(),
        "downloaded_at": downloaded_at,
        "version_id": f"resource:{resource.resource_id};sha256:{sha256}",
        "http": {
            "etag": _header(response_headers, "ETag"),
            "last_modified": _header(response_headers, "Last-Modified"),
            "content_length": int(content_length) if content_length and content_length.isdigit() else content_length,
        },
        "file": {
            "size_bytes": size_bytes,
            "sha256": sha256,
        },
    }


def refresh_manifest(manifest_path: Path) -> Path:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for resource in manifest["resources"]:
        path = Path(resource["local_path"])
        if not path.exists():
            raise AcquisitionError(f"arquivo congelado ausente: {path}")
        sha256 = _sha256(path)
        resource["file"] = {"size_bytes": path.stat().st_size, "sha256": sha256}
        resource["version_id"] = f"resource:{resource['resource_id']};sha256:{sha256}"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def inventory_document(resources: Iterable[ResourceSpec] = ALL_RESOURCES) -> dict:
    return {
        "schema_version": 1,
        "election": 2022,
        "scope": "Brasil / todas as UFs",
        "resources": [asdict(resource) for resource in resources],
    }


def write_inventory(data_root: Path, resources: Iterable[ResourceSpec] = ALL_RESOURCES) -> Path:
    path = data_root / "inventory-2022.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(inventory_document(resources), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def acquire_core(
    data_root: Path = Path("data"),
    *,
    now: datetime | None = None,
    opener: Callable[..., BinaryIO] = urlopen,
) -> Path:
    """Download the core archives into a unique snapshot and write its manifest."""
    timestamp = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    run_id = timestamp.strftime("%Y%m%dT%H%M%SZ")
    downloaded_at = timestamp.isoformat().replace("+00:00", "Z")
    raw_dir = data_root / "raw" / "2022" / run_id
    manifest_dir = data_root / "manifests"
    raw_dir.mkdir(parents=True, exist_ok=False)
    manifest_dir.mkdir(parents=True, exist_ok=True)

    entries: list[dict] = []
    for resource in ALL_RESOURCES:
        target = raw_dir / resource.filename
        request = Request(resource.url, headers={"User-Agent": "dinheiro-compra-votos/0.1"})
        try:
            with opener(request) as response, target.with_suffix(target.suffix + ".part").open("wb") as partial:
                shutil.copyfileobj(response, partial, length=1024 * 1024)
                headers = dict(response.headers.items())
        except Exception as exc:  # pragma: no cover - exercised by the real network run
            partial = target.with_suffix(target.suffix + ".part")
            if partial.exists():
                partial.unlink()
            raise AcquisitionError(f"falha ao baixar {resource.key}: {exc}") from exc
        partial = target.with_suffix(target.suffix + ".part")
        partial.replace(target)
        entries.append(build_manifest_entry(resource, target, downloaded_at=downloaded_at, response_headers=headers))

    manifest = {
        "schema_version": 1,
        "manifest_id": run_id,
        "election": 2022,
        "scope": "Brasil / todas as UFs",
        "created_at": downloaded_at,
        "resources": entries,
    }
    manifest_path = manifest_dir / f"manifest-{run_id}.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest_path
