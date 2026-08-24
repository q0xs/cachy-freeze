<p align="center">
  <img src="app/cachy_freeze_gui/assets/cachy-freeze.png" width="168" alt="CachyFreeze logo">
</p>

<h1 align="center">CachyFreeze</h1>

CachyFreeze is a Linux system-freeze utility for CachyOS.

**FROZEN:** Every reboot restores the computer to its approved baseline.

**THAWED:** Changes persist and the administrator can update the system. Freeze
again to make the maintained system the new baseline.

> [!CAUTION]
> CachyFreeze changes Btrfs subvolumes, initramfs, and GRUB. Keep recovery media
> and a restorable backup. Unsupported layouts fail before these resources are
> changed.

## Two-mode workflow

The installed application has one page. It displays the verified current mode,
the requested next-boot mode when different, and only these normal actions:

- **FREEZE COMPUTER** — while THAWED, atomically replace Golden from persistent
  `@` and schedule FROZEN.
- **THAW COMPUTER** — while FROZEN, schedule persistent `@` without copying any
  data from disposable `@active`.
- **REBOOT NOW** — shown after a mode change. CachyFreeze never silently reboots.

Every FROZEN boot deletes the prior disposable runtime and creates a fresh
`@active` from read-only `@golden`. CachyFreeze does not keep a snapshot history,
rollback timeline, old runtime, or historical Golden archive. Transaction
staging exists only while a replacement is in progress and is removed after
success or reconciled after interruption.

Deleting a Btrfs subvolume is logical non-retention, not forensic media erasure.
CachyFreeze does not claim to overwrite old CoW extents, SSD flash cells, or
controller-managed storage.

The standard CachyOS data subvolumes (`@home`, `@root`, `@srv`, `@cache`,
`@tmp`, and `@log`) are captured into Golden with same-filesystem CoW clones.
FROZEN boots disable `/etc/fstab` mounts, so those persistent THAWED subvolumes
are not modified by a FROZEN session. Existing third-party Snapper history is
not copied into Golden and is never deleted by CachyFreeze.

Unknown Btrfs submounts or nested subvolumes fail closed. Filesystems outside
the supported CachyOS root layout are not part of the reset guarantee.

## Requirements

- CachyOS or Arch Linux with KDE Plasma
- UEFI and GRUB
- Btrfs root subvolume `@`
- standard CachyOS `@home`, `@root`, `@srv`, `@cache`, `@tmp`, and `@log`
  layout (a subset is allowed)
- EFI System Partition mounted at `/boot/efi`
- `/boot` stored inside the Btrfs root
- recovery media and a restorable backup

ext4, BIOS, systemd-boot, separate `/boot`, and custom Btrfs mount layouts are
not supported.

## Install

1. Download `CachyFreeze-Installer-<version>.run` and its checksum.
2. Mark the downloaded artifact executable if the browser removed that bit.
3. Open it from KDE.
4. Authorize the verified transient staging request, then enter a
   boot-maintenance password and approve installation.
5. When installation succeeds, save work and select **REBOOT NOW**.

After reboot, open **CachyFreeze** from the KDE Application Launcher. No Git
checkout, terminal workflow, `pip install`, manual Btrfs setup, or manual GRUB
configuration is required.

Build the single-file installer from an unprivileged checkout:

```bash
bash packaging/build-installer.sh
```

See [installation details](docs/installation.md),
[architecture](docs/architecture.md), [recovery](docs/boot-recovery.md), and
[development verification](docs/development.md).

## Development checks

Use only the commands established by this repository:

```bash
ruff check src app/cachy_freeze_gui tests
ruff format --check src app/cachy_freeze_gui tests
PYTHONPATH=src:app python -m unittest discover -s tests -v
SHELLCHECK_OPTS=--severity=error bash deepfreeze/tests/static.sh
QT_QPA_PLATFORM=offscreen bash deepfreeze/tests/ui-smoke.sh
bash deepfreeze/tests/grub-generation.sh
bash packaging/build-installer.sh
bash deepfreeze/tests/boot-acceptance-vm.sh
```

Never run the Btrfs, GRUB, initramfs, reboot, or lifecycle acceptance tests on a
normal workstation. Use the repository’s loopback fixtures and disposable
QEMU/OVMF guests.

## License

Copyright 2026 Atilla Mert Akkaya. Licensed under the Apache License 2.0.
