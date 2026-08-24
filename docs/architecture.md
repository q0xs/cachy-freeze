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
| `@cachy-capture` | Transaction-only parent for read-only CachyOS data captures |

`@golden.next`, `@golden.pending`, `@active.next`, `@active.pending`, and
`@cachy-capture` are transaction-scoped names. They are not recovery history
and must not remain after a successful operation.

## State transitions

### FREEZE

```text
verified running @ (THAWED)
→ lock and validate filesystem/boot state
→ discover and verify standard CachyOS data mounts and supported nested state
→ sync, snapshot @ to @golden.next, and capture auxiliary sources read-only
→ reflink captured content where supported and copy NOCOW files normally
→ exclude third-party Snapper history and make the candidate read-only
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
`@active`. The FROZEN kernel receives `fstab=no`, so persistent THAWED data
subvolumes are not mounted; their approved content already exists inside the
flattened Golden/Active root. The initramfs hook then verifies the Btrfs device and
Golden, rolls back an interrupted pre-boot transaction when pending names prove
the old roots, recursively deletes all disposable runtime objects, creates a
fresh writable runtime from Golden, validates its boot files and usable init,
and exposes it as `@active`.

The reset oneshot remains active for the rest of the initramfs transaction and
also records the current boot ID. A duplicate start in the same boot is a
verified no-op. A reset with a new boot ID refuses to delete `@active` while any
mount references it. The next candidate is created, synced, and fully validated
before the prior runtime is recursively deleted. No previous runtime is renamed
into history.

A failed reset schedules the next boot as password-protected THAWED when the
canonical GRUB environment is still writable; it never continues into an
unverified FROZEN root. The real-root boot-health check accepts FROZEN only when
the reset proof matches that same kernel boot.

### THAW

While verified FROZEN, the engine verifies persistent `@`, writes and verifies
the managed GRUB environment, and schedules THAWED. It never snapshots or copies
`@active`. Once a THAWED graphical boot is verified, the boot-verification
service recursively deletes stale CachyFreeze runtime objects and removes the
old reset proof.

## GRUB boundary

The normal five-second GRUB menu contains one dynamic managed entry. Its title
is FROZEN or THAWED, never both. FROZEN is unrestricted for passwordless boot;
THAWED gates every kernel and initramfs load behind successful `cachyadmin`
authentication. Vendor, firmware, snapshot, and custom generators are preserved
inside a `cachy_recovery=1` conditional and therefore remain absent from the
normal menu.

## Existing installations

Migration removes `@cachy-snapshots` only when every child exactly matches the
owned, valid `snapshots.json` catalog. Missing, malformed, or mismatched
ownership evidence aborts migration without deletion. Unrelated Snapper,
Timeshift, Btrfs, and GRUB resources are never migration targets.

The installer disables and removes only known CachyFreeze legacy services and
binaries. It preserves unrelated GRUB generators and entries.

Existing Snapper `.snapshots` data remains attached only to persistent `@` and
is neither copied into Golden nor deleted. Unknown nested subvolumes and custom
Btrfs submounts are rejected rather than silently left persistent.

## Data guarantee

CachyFreeze keeps no logically accessible historical FROZEN runtime or Golden
archive. This is not physical secure erase; Btrfs CoW, TRIM, SSD wear leveling,
and storage-controller behavior remain outside this guarantee. External drives,
network storage, manually mounted filesystems, and unsupported layouts are also
outside the reset boundary.
