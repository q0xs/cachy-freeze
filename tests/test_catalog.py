from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from test_models import snapshot

from cachy_freeze.catalog import AuditLogger, SnapshotCatalog
from cachy_freeze.errors import IntegrityError


class SnapshotCatalogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.catalog = SnapshotCatalog(self.root / "state")

    def test_add_list_increment_and_remove(self) -> None:
        metadata = snapshot()
        self.catalog.add(metadata)
        self.assertEqual(self.catalog.list(), [metadata])
        updated = self.catalog.increment_rollback(metadata.snapshot_id)
        self.assertEqual(updated.rollback_count, 1)
        self.assertTrue(updated.verifies())
        updated = self.catalog.set_health(metadata.snapshot_id, "warning")
        self.assertEqual(updated.health, "warning")
        self.assertTrue(updated.verifies())
        self.assertEqual(self.catalog.remove(metadata.snapshot_id), updated)
        self.assertEqual(self.catalog.list(), [])

    def test_duplicate_snapshot_is_rejected(self) -> None:
        metadata = snapshot()
        self.catalog.add(metadata)
        with self.assertRaisesRegex(IntegrityError, "Duplicate snapshot"):
            self.catalog.add(metadata)

    def test_transaction_journal_has_durable_phase(self) -> None:
        self.catalog.begin_transaction("publish", "preparing", {"id": "one"})
        self.catalog.set_transaction_phase("prepared")
        transaction = self.catalog.transaction()
        assert transaction is not None
        self.assertEqual(transaction["phase"], "prepared")
        self.catalog.finish_transaction()
        self.assertIsNone(self.catalog.transaction())

    def test_malformed_catalog_is_not_silently_replaced(self) -> None:
        self.catalog.path.parent.mkdir(parents=True)
        self.catalog.path.write_text("not-json", encoding="utf-8")
        with self.assertRaisesRegex(IntegrityError, "cannot be read"):
            self.catalog.list()

    def test_audit_log_writes_one_json_object_per_line(self) -> None:
        path = self.root / "logs" / "operations.jsonl"
        AuditLogger(path).write("warning", "test.action", "message", value=7)
        entry = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(entry["level"], "WARNING")
        self.assertEqual(entry["action"], "test.action")
        self.assertEqual(entry["context"], {"value": 7})


if __name__ == "__main__":
    unittest.main()
