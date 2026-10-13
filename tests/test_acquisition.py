import io
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from tse_pilot.acquisition import CORE_RESOURCES, VOTE_TOTALS_RESOURCE_2022, build_manifest_entry, freeze_vote_totals_2022


class AcquisitionManifestTests(unittest.TestCase):
    def test_core_inventory_covers_only_the_three_pilot_inputs(self):
        self.assertEqual(
            {resource.key for resource in CORE_RESOURCES},
            {"candidates_2022", "accounts_2022", "votes_2022"},
        )
        self.assertTrue(all(resource.url.startswith("https://cdn.tse.jus.br/") for resource in CORE_RESOURCES))
        self.assertTrue(all(resource.resource_id for resource in CORE_RESOURCES))

    def test_vote_totals_source_is_frozen_in_existing_snapshot_and_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw_dir = root / "raw" / "2022" / "snapshot"
            raw_dir.mkdir(parents=True)
            existing_source = raw_dir / "candidates.zip"
            existing_source.write_bytes(b"existing frozen source")
            manifest_path = root / "manifests" / "manifest-snapshot.json"
            manifest_path.parent.mkdir()
            manifest_path.write_text(
                json.dumps({
                    "manifest_id": "snapshot",
                    "resources": [{"resource_key": "candidates_2022", "local_path": str(existing_source)}],
                }),
                encoding="utf-8",
            )

            class Response(io.BytesIO):
                headers = {
                    "ETag": '"official-votes"',
                    "Last-Modified": "Wed, 14 Oct 2026 00:00:00 GMT",
                    "Content-Length": "15",
                }

            opened = []

            def opener(request):
                opened.append(request.full_url)
                return Response(b"frozen vote data")

            result = freeze_vote_totals_2022(
                manifest_path,
                now=datetime(2026, 10, 14, tzinfo=timezone.utc),
                opener=opener,
            )
            manifest = json.loads(result.read_text(encoding="utf-8"))
            source = next(item for item in manifest["resources"] if item["resource_key"] == "vote_totals_2022")

            self.assertEqual(source["url"], VOTE_TOTALS_RESOURCE_2022.url)
            self.assertEqual(source["file"]["size_bytes"], 16)
            self.assertEqual(source["file"]["sha256"], "385b5d23583cc13a21d5085986ba58310bb76c262640559e589e1bd563b893b6")
            self.assertEqual(Path(source["local_path"]), raw_dir / VOTE_TOTALS_RESOURCE_2022.filename)
            self.assertEqual(len(opened), 1)

            freeze_vote_totals_2022(manifest_path, opener=lambda request: self.fail("source must not be downloaded twice"))
            self.assertEqual(len(opened), 1)

    def test_manifest_entry_records_file_identity_and_http_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.zip"
            path.write_bytes(b"pilot bytes")

            entry = build_manifest_entry(
                CORE_RESOURCES[0],
                path,
                downloaded_at="2026-10-08T16:00:00Z",
                response_headers={
                    "ETag": '"example"',
                    "Last-Modified": "Thu, 08 Oct 2026 06:20:11 GMT",
                    "Content-Length": "11",
                },
            )

        self.assertEqual(entry["resource_key"], "candidates_2022")
        self.assertEqual(entry["file"]["size_bytes"], 11)
        self.assertEqual(
            entry["file"]["sha256"],
            "ea17ab386a27c143fa4acd72658179f52ceec851515e8af96017bad196a82af5",
        )
        self.assertEqual(entry["version_id"], "resource:435145fd-bc9d-446a-ac9d-273f585a0bb9;sha256:ea17ab386a27c143fa4acd72658179f52ceec851515e8af96017bad196a82af5")
        self.assertEqual(entry["http"]["last_modified"], "Thu, 08 Oct 2026 06:20:11 GMT")
        self.assertEqual(entry["downloaded_at"], "2026-10-08T16:00:00Z")


if __name__ == "__main__":
    unittest.main()
