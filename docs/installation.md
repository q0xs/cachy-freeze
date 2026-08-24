# Installation

## Supported environment

- CachyOS/Arch Linux with KDE Plasma
- UEFI, GRUB, and Btrfs root subvolume `@`
- EFI mounted at `/boot/efi`
- no separate `/boot` filesystem
- the standard CachyOS data layout using any subset of `@home`, `@root`,
  `@srv`, `@cache`, `@tmp`, and `@log`
- only the standard systemd `var/lib/machines` and `var/lib/portables`
  subvolumes nested in `@`; an existing Snapper `.snapshots` tree is preserved
  but excluded from Golden

Compatibility checks run inside the graphical installer before CachyFreeze
changes Btrfs or GRUB. A failed critical check stops installation.

During FREEZE, mounted CachyOS data subvolumes are captured read-only and copied
into the staged Golden root. Same-filesystem reflinks are used where Btrfs
supports them; NOCOW files use a normal byte copy. FROZEN boots use `fstab=no`;
persistent THAWED mounts such as `@home` remain unmounted and all session
changes land in disposable `@active`. THAWED boots use the original
`/etc/fstab` unchanged.

## Graphical single-file install

1. Download `CachyFreeze-Installer-<version>.run` and verify its SHA-256 sidecar.
2. Ensure the artifact is executable, then open it in KDE.
3. Approve the PolicyKit request that creates a verified, root-owned transient
   installer staging area.
4. Enter and confirm the GRUB boot-maintenance password.
5. Select **INSTALL CACHYFREEZE** and approve any uncached PolicyKit request.
6. Wait while the installer validates compatibility, installs required Arch
   packages, configures PolicyKit/initramfs/GRUB, migrates owned legacy state,
   creates the initial Golden, and schedules FROZEN.
7. Save work and select **REBOOT NOW**.

The password travels through process standard input and is converted to a GRUB
PBKDF2 hash. The plaintext is not written to disk, command arguments,
environment files, logs, source, or fixtures.

The installer never reboots automatically. After reboot, open **CachyFreeze**
from the KDE Application Launcher.

## Repeat installation and migration

Run the installer only while actually booted from persistent THAWED `@`.
Re-running it updates/reconciles owned application files, PolicyKit, initramfs,
and the one managed GRUB entry. Existing entries from other software remain.

Legacy CachyFreeze snapshot history is removed only when its catalog proves
ownership of every child. Ambiguous data aborts installation and requires
manual review. The installer never deletes Snapper, Timeshift, or unrelated
subvolumes.

## Build

From an unprivileged checkout:

```bash
bash packaging/build-installer.sh
```

The command writes the `.run` artifact and checksum to `dist/`. Set
`SOURCE_DATE_EPOCH` to the release timestamp for reproducible release builds.
