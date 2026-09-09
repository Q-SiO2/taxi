from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest


SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from generate_source_contract_inventory import (
    InventoryError,
    MigrationRecord,
    api_inventory,
    migration_inventory,
    permission_inventory,
    read_migration_records,
    validate_migration_graph,
)


class SourceContractInventoryTests(unittest.TestCase):
    def test_migration_inventory_is_ordered_and_has_one_root_and_head(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            versions = root / "versions"
            versions.mkdir()
            (versions / "0002_second.py").write_text(
                "revision: str = '0002'\ndown_revision = '0001'\n",
                encoding="utf-8",
            )
            (versions / "0001_first.py").write_text(
                "revision = '0001'\ndown_revision = None\n",
                encoding="utf-8",
            )

            inventory = migration_inventory(
                read_migration_records(versions, workspace_root=root)
            )

            self.assertEqual(2, inventory["count"])
            self.assertEqual(["0001"], inventory["roots"])
            self.assertEqual(["0002"], inventory["heads"])
            self.assertEqual(
                ["0001", "0002"],
                [record["revision"] for record in inventory["revisions"]],
            )

    def test_migration_inventory_rejects_dangling_and_duplicate_revisions(self) -> None:
        with self.assertRaisesRegex(InventoryError, "Unknown migration parent"):
            validate_migration_graph(
                [MigrationRecord("0002", ("missing",), "0002.py")]
            )
        with self.assertRaisesRegex(InventoryError, "Duplicate migration revision"):
            validate_migration_graph(
                [
                    MigrationRecord("0001", (), "first.py"),
                    MigrationRecord("0001", (), "duplicate.py"),
                ]
            )

    def test_api_inventory_is_sorted_and_rejects_duplicate_operation_ids(self) -> None:
        inventory = api_inventory(
            {
                "paths": {
                    "/z": {
                        "post": {"operationId": "z_post", "tags": ["z"]},
                    },
                    "/a": {
                        "get": {"operationId": "a_get", "tags": ["b", "a"]},
                    },
                }
            },
            ["/api/v1/events"],
        )
        self.assertEqual(2, inventory["http_operation_count"])
        self.assertEqual("/a", inventory["http_operations"][0]["path"])
        self.assertEqual(["a", "b"], inventory["http_operations"][0]["tags"])

        with self.assertRaisesRegex(InventoryError, "Duplicate API operationId"):
            api_inventory(
                {
                    "paths": {
                        "/a": {"get": {"operationId": "duplicate"}},
                        "/b": {"post": {"operationId": "duplicate"}},
                    }
                },
                [],
            )

    def test_permission_inventory_requires_every_role_and_known_permission(self) -> None:
        inventory = permission_inventory(
            ["read", "write"],
            ["ADMIN", "READER"],
            {"ADMIN": ["write", "read"], "READER": ["read"]},
        )
        self.assertEqual(2, inventory["permission_count"])
        self.assertEqual("ADMIN", inventory["roles"][0]["role"])
        self.assertEqual(["read", "write"], inventory["roles"][0]["permissions"])

        with self.assertRaisesRegex(InventoryError, "mapping mismatch"):
            permission_inventory(["read"], ["ADMIN", "READER"], {"ADMIN": ["read"]})
        with self.assertRaisesRegex(InventoryError, "Unknown mapped permission"):
            permission_inventory(["read"], ["ADMIN"], {"ADMIN": ["delete"]})


if __name__ == "__main__":
    unittest.main()
