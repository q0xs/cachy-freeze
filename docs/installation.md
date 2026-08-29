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

The installer makes the stable CachyFreeze entry ID the direct GRUB default
instead of relying on GRUB's saved-entry fallback. The normal five-second menu
is visible and contains exactly one managed entry, named FROZEN or THAWED
according to the mode selected in CachyFreeze. FROZEN is passwordless. THAWED
requires the fixed `cachyadmin` boot-maintenance user and its password before
any kernel or initramfs load. Other operating-system, recovery, firmware,
snapshot, and custom entries remain generated in `grub.cfg` behind the explicit
administrator recovery gate and do not appear in the normal menu.

The initramfs prepares and validates a fresh Active before deleting the prior
one, runs at most once per kernel boot, refuses to delete a mounted Active, and
records a boot-specific reset proof. If FROZEN preparation fails after the
canonical GRUB environment becomes available, the next boot is scheduled as
password-protected THAWED rather than repeatedly selecting a broken FROZEN root.

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

Employee applications and idle security are deployed by the separate portable
provisioner before FREEZE, not by this graphical installer. See
[CachyWorkstation provisioning](workstation-provisioning.md).
