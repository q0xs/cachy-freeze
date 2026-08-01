from __future__ import annotations

import unittest
from dataclasses import replace

from cachy_freeze.models import CHECKSUM_ALGORITHM, SnapshotMetadata


def snapshot() -> SnapshotMetadata:
    return SnapshotMetadata.create(
        snapshot_id="snap-20260801T120000Z-1234abcd",
        subvolume="@cachy-snapshots/snap-20260801T120000Z-1234abcd",
        btrfs_uuid="btrfs-uuid",
        parent_uuid="parent-uuid",
        created_at="2026-08-01T12:00:00+00:00",
        kernel="6.18.0-cachyos",
        apparent_size_bytes=4096,
        exclusive_size_bytes=1024,
        description="Known good baseline",
        created_by="localadm",
        frozen=True,
        bootable=True,
        creation_duration_ms=250,
        source_subvolume="@",
    )


class SnapshotMetadataTests(unittest.TestCase):
    def test_new_metadata_has_deterministic_checksum(self) -> None:
        metadata = snapshot()
        self.assertEqual(metadata.checksum_algorithm, CHECKSUM_ALGORITHM)
        self.assertTrue(metadata.verifies())
        self.assertEqual(metadata, SnapshotMetadata.from_dict(metadata.to_dict()))

    def test_immutable_identity_change_breaks_checksum(self) -> None:
        self.assertFalse(replace(snapshot(), description="Tampered").verifies())

    def test_health_and_rollback_are_mutable_operational_fields(self) -> None:
        updated = replace(snapshot(), health="warning", rollback_count=4)
        self.assertTrue(updated.verifies())


if __name__ == "__main__":
    unittest.main()
