# Threat model

This page states what FROZEN protects, against what, and where the
boundaries honestly are. It supplements the data guarantee in
`architecture.md`.

## What FROZEN protects

Every FROZEN boot discards the entire disposable session before it can be
used: `@active` is deleted and recreated from read-only `@golden` inside the
initramfs, proven by the current kernel boot id. All session writes land
only in `@active` because FROZEN boots with `fstab=no`, so persistent data
subvolumes (`@home`, `@root`, `@srv`, `@cache`, `@tmp`, `@log`) are never
mounted. There is no swap, no hibernation image, and real suspend is
inhibited by the workstation idle policy, so no second durable surface for
session data exists.

## Scenarios

### Power loss, reset, or unplanned shutdown

Pulling the plug mid-session is equivalent to a hard shutdown. RAM state is
lost immediately. The next FROZEN boot performs the normal reset and the
session is unrecoverable through the operating system. An interrupted
FREEZE transaction is recovered fail-closed by the journal: pre-boot
interruptions restore pending predecessors; an invalid candidate is never
activated.

### Normal shutdown or reboot

Same boundary: the session lives only in `@active`, which is deleted before
the next session can mount it. No historical runtime or Golden archive is
retained.

### Machine stolen or seized while powered off

- A FROZEN machine exposes no session files to the running OS: the next
  boot resets `@active`.
- This is a logical non-retention guarantee, not physical secure erase.
  Until the storage controller reuses or discards them, blocks of the
  deleted `@active` may still be recoverable with chip-level NAND tooling.
  Btrfs copy-on-write, TRIM scheduling, and SSD wear leveling all affect
  how quickly that residual window closes and are outside this product.
- The approved baseline itself (`@golden`, persistent `@`) is intentionally
  unencrypted and readable. Full-disk encryption would require a password
  at every boot and is incompatible with the passwordless FROZEN contract.

### Boot-time physical access

The THAWED GRUB password gates normal menu selection only. The managed
menu entry is `--unrestricted`, so a person with console access can edit
kernel or root arguments at boot, or reach persistent `@` directly,
without knowing that password. The same applies to writing
`cachy_mode`/`cachy_remote_auth` in `grubenv` from any root shell on `@`.

Operational requirement: set a firmware/BIOS password and enable UEFI
Secure Boot (with a custom key or with GRUB under a signed shim) on any
machine where boot-time physical access is a real threat. Without this,
the FROZEN/THAWED boundary is an administrative workflow control, not a
hostile-physics defense.

### Compromise inside FROZEN

Malware running as the employee in FROZEN mode can corrupt the running
session and can reschedule THAWED boot, but it cannot modify `@golden`
(read-only property) and its filesystem changes are destroyed at the next
FROZEN boot. A reboot into THAWED still requires the GRUB password from
the normal menu, so persistence requires either the maintenance password,
boot-time menu editing (see above), or social engineering of an
administrator into a FREEZE of the compromise.

## Deferred hardening (backlog, post-1.0.1)

- TRIM/discard policy after each FROZEN reset (for example an `fstrim`
  pass) to shrink the residual NAND window where controllers support it.
- Health-check assertions for no active swap, no hibernation image, and
  lid/power-button behavior on laptops.
- Optional per-boot ephemeral-key encrypted session layer (random key held
  in RAM only for home/cache/tmp overlays) so a powered-off disk is
  cryptographically unreadable for session data while keeping the fast
  reflink-based `@active` creation. Requires its own design document,
  initramfs work, and disposable-VM validation before any schedule
  commitment.
