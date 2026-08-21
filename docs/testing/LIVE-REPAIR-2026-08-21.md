# Live repair progress — 2026-08-21

This is a deliberately non-sensitive continuation record for the live repair.
It must be copied to `/var/lib/cachy-freeze/repair-progress.md`, which is the
persistent CachyFreeze state subvolume, before rebooting.

## Confirmed fault

- A FROZEN boot entered with `cachy.freeze=1`, but the mounted root was
  `@active.previous`, rather than `@active`.
- The initramfs journal shows that `cachy-freeze-reset.service` ran twice:
  once before the sysroot mount and again during switch-root.
- The second invocation renamed the live `@active` to `@active.previous`.
  Boot validation then failed closed, as intended.

## Source repair

- `deepfreeze/initcpio/cachy-freeze-reset.service` now has
  `ConditionPathExists=/etc/initrd-release`. This confines reset execution to
  the initramfs and prevents a second post-switch-root run.
- `deepfreeze/tests/static.sh` verifies that guard.
- Local validation completed: 96 Python tests, Bash/static checks, Qt
  offscreen smoke, and GRUB generation checks passed. Ruff and ShellCheck were
  unavailable and remain unrun.

## Completed live repair

- The repaired reset unit was installed into both the currently running root
  and the maintenance `@` root.
- Both maintenance initramfs images were rebuilt successfully and extracted
  for verification. Each contains the repaired reset unit and its initramfs-only
  condition.
- `mkinitcpio` reported that hardware autodetection could not identify the
  chroot root filesystem. It still completed both images successfully; this
  is expected for the maintenance-root chroot and must be rechecked after the
  normal THAWED boot.

## Remaining live sequence

1. Reboot into the already-scheduled THAWED mode.
2. Confirm the root is `@`, then inspect service and audit logs.
3. Run the complete non-destructive validation gate again; do not declare a
   physical FROZEN reset verified until one controlled FROZEN reboot has
   completed successfully.
