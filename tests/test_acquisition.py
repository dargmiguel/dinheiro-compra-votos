import tempfile
import unittest
from pathlib import Path

from tse_pilot.acquisition import CORE_RESOURCES, build_manifest_entry


class AcquisitionManifestTests(unittest.TestCase):
    def test_core_inventory_covers_only_the_three_pilot_inputs(self):
        self.assertEqual(
            {resource.key for resource in CORE_RESOURCES},
            {"candidates_2022", "accounts_2022", "votes_2022"},
        )
        self.assertTrue(all(resource.url.startswith("https://cdn.tse.jus.br/") for resource in CORE_RESOURCES))
        self.assertTrue(all(resource.resource_id for resource in CORE_RESOURCES))

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
