# Architecture

CachyFreeze is a local two-mode appliance. The unprivileged PyQt6 GUI sends an
exact allow-listed action through PolicyKit. The privileged helper invokes the
Python engine with structured arguments. Only the engine may mutate Btrfs or
GRUB state.

| Subvolume | Purpose |
| --- | --- |
| `@` | Persistent writable THAWED maintenance root |
| `@golden` | Read-only approved FROZEN baseline |
| `@active` | Writable disposable FROZEN root, recreated at every FROZEN boot |
| `@cachy-state` | Minimal version, transaction, boot proof, and status metadata |

`@golden.next`, `@golden.pending`, `@active.next`, and `@active.pending` are
transaction-scoped names. They are not recovery history and must not remain
after a successful operation.

## State transitions

### FREEZE

```text
verified running @ (THAWED)
→ lock and validate filesystem/boot state
→ sync and snapshot @ read-only to @golden.next
→ validate candidate boot files and read-only state
→ create and validate @active.next
→ move current roots to transaction-scoped pending names
→ activate candidates
→ verify and schedule FROZEN in GRUB environment
→ delete pending objects and close the journal
```

Before the final commit, interruption recovery restores pending predecessors.
After the boot-mode commit, recovery validates the new pair and removes pending
objects. An invalid candidate is never activated deliberately.

### FROZEN boot

GRUB loads the FROZEN kernel, microcode, and initramfs from read-only `@golden`,
never from the previous writable `@active`; the selected root remains
`@active`. The initramfs hook then verifies the configured Btrfs device and
Golden, rolls back an interrupted pre-boot transaction when pending names prove
the old roots, deletes all disposable runtime objects, creates a fresh writable
runtime from Golden, validates it, and exposes it as `@active`.

No previous runtime is renamed into history. Failure enters initramfs emergency
handling rather than booting an unverified root.

### THAW

While verified FROZEN, the engine verifies persistent `@`, writes and verifies
the managed GRUB environment, and schedules THAWED. It never snapshots or copies
`@active`. Once a THAWED graphical boot is verified, the boot-verification
service deletes stale CachyFreeze runtime objects.

## Existing installations

Migration removes `@cachy-snapshots` only when every child exactly matches the
owned, valid `snapshots.json` catalog. Missing, malformed, or mismatched
ownership evidence aborts migration without deletion. Unrelated Snapper,
Timeshift, Btrfs, and GRUB resources are never migration targets.

The installer disables and removes only known CachyFreeze legacy services and
binaries. It preserves unrelated GRUB generators and entries.

## Data guarantee

CachyFreeze keeps no logically accessible historical FROZEN runtime or Golden
archive. This is not physical secure erase; Btrfs CoW, TRIM, SSD wear leveling,
and storage-controller behavior remain outside this guarantee.
