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
success or reconciled after interruption. The early-boot reset is idempotent for
one kernel boot, refuses to delete a mounted runtime, and must leave a current
boot-id proof before the graphical boot is accepted as healthy.

Deleting a Btrfs subvolume is logical non-retention, not forensic media erasure.
CachyFreeze does not claim to overwrite old CoW extents, SSD flash cells, or
controller-managed storage.

The standard CachyOS data subvolumes (`@home`, `@root`, `@srv`, `@cache`,
`@tmp`, and `@log`) are captured into Golden with same-filesystem CoW clones
where supported and a normal copy for Btrfs NOCOW files such as system journals.
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

## Download and install

> [!IMPORTANT]
> The current published build is
> [CachyFreeze v1.0.0rc6](https://github.com/q0xs/cachy-freeze/releases/tag/v1.0.0rc6),
> which is marked as a pre-release. Keep recovery media and a restorable backup
> available before installing it.

### 1. Download the official files

Download both files from the `Assets` section of the release. They must have
the same version number:

- [CachyFreeze-Installer-1.0.0rc6.run](https://github.com/q0xs/cachy-freeze/releases/download/v1.0.0rc6/CachyFreeze-Installer-1.0.0rc6.run)
- [CachyFreeze-Installer-1.0.0rc6.run.sha256](https://github.com/q0xs/cachy-freeze/releases/download/v1.0.0rc6/CachyFreeze-Installer-1.0.0rc6.run.sha256)

Do not download GitHub's **Source code (zip)** or **Source code (tar.gz)** for a
normal installation. Those archives are for development and are not the
graphical installer.

### 2. Verify the download

Open Konsole and run:

```bash
cd "$(xdg-user-dir DOWNLOAD)"
sha256sum --check CachyFreeze-Installer-1.0.0rc6.run.sha256
```

Continue only if the result is:

```text
CachyFreeze-Installer-1.0.0rc6.run: OK
```

If verification reports `FAILED`, delete both downloaded files and download
them again from the release page.

### 3. Start the graphical installer

Make the verified file executable and open it:

```bash
chmod +x CachyFreeze-Installer-1.0.0rc6.run
./CachyFreeze-Installer-1.0.0rc6.run
```

Do not run the installer with `sudo`. It requests administrator authorization
through PolicyKit only when privileged work is required. You can also open the
executable from Dolphin after enabling **Is executable** in its file
permissions.

### 4. Complete setup

1. Approve the PolicyKit request that places the verified installer in a
   temporary root-owned staging directory.
2. Enter and confirm a boot-maintenance password in the setup window. It must
   contain 12-256 characters and at least three of these classes: lowercase,
   uppercase, digits, and symbols. A colon (`:`) is not supported.
3. Select **INSTALL CACHYFREEZE** and approve any additional PolicyKit request.
4. Wait for the success message. Do not interrupt package installation,
   Golden publication, initramfs generation, or GRUB generation.
5. Save all work and select **REBOOT NOW**. The installer never reboots the
   computer without this explicit request.

The initial installation creates and verifies the Golden baseline, then
schedules FROZEN for the next boot. After reboot, open **CachyFreeze** from the
KDE Application Launcher.

The fixed GRUB maintenance username is `cachyadmin`; it is separate from Linux
desktop accounts. FROZEN starts without this password. Starting THAWED from
GRUB requires `cachyadmin` and the boot-maintenance password chosen during
installation.

The installer performs compatibility checks before changing the boot stack,
installs required Arch packages, installs the unprivileged GUI and its
PolicyKit helper, builds the initramfs integration, generates the managed GRUB
entry, publishes the initial Golden baseline, and schedules FROZEN. A network
connection may be required to install missing packages. No Git checkout,
`pip install`, manual Btrfs setup, or manual GRUB configuration is required.

### Update an existing installation

Run a newer installer only while the computer is actually booted in THAWED
mode from persistent `@`:

1. In CachyFreeze, select **THAW COMPUTER**, then **REBOOT NOW**.
2. Confirm that the application reports **THAWED** after reboot.
3. Download and verify the newer installer and checksum from
   [GitHub Releases](https://github.com/q0xs/cachy-freeze/releases).
4. Run the newer installer normally, without `sudo`, and reboot when setup
   succeeds.

Never reinstall or update CachyFreeze from a FROZEN session.

The stable CachyFreeze entry is the direct GRUB default. A visible five-second
menu shows exactly one normal entry, named FROZEN or THAWED according to the mode
scheduled by the application. FROZEN boots without a GRUB password; THAWED asks
for the fixed `cachyadmin` boot-maintenance user and its password. Vendor,
firmware, snapshot, and custom entries remain generated behind an explicit
administrator recovery gate instead of appearing in the normal appliance menu.

## Build from source

Developers can build the single-file installer from an unprivileged checkout:

```bash
bash packaging/build-installer.sh
```

See [installation details](docs/installation.md),
[architecture](docs/architecture.md), [recovery](docs/boot-recovery.md), and
[development verification](docs/development.md).

## Separate portable workstation provisioning

The repository also contains an administrator-only, independently packaged
CachyOS workstation provisioner. It is not part of the normal CachyFreeze GUI,
installer payload, or Btrfs/GRUB lifecycle. It installs the approved employee
applications and the 60-minute lock / 120-minute shutdown policy before the
administrator creates the final Golden baseline.

Build its single-file payload with:

```bash
bash packaging/build-workstation-installer.sh
```

Then copy the `.run` file and checksum to a THAWED target machine and run it for
an already-created standard account:

```bash
sudo ./CachyWorkstation-Setup-1.0.0.run wrw1166
sudo ./CachyWorkstation-Setup-1.0.0.run --check wrw1166
```

The small payload is an online provisioner, not an offline application bundle.
Each target needs internet access to its configured CachyOS repositories and
the pinned official application URLs; downloaded proprietary files are checked
against the reviewed hashes embedded in the `.run` file.

See the complete [portable provisioning and deployment
guide](docs/workstation-provisioning.md). Freeze is always the last manual
deployment step, after all health checks and application tests pass.

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
bash packaging/build-workstation-installer.sh
bash workstation/tests/static.sh
bash deepfreeze/tests/boot-acceptance-vm.sh
```

Never run the Btrfs, GRUB, initramfs, reboot, or lifecycle acceptance tests on a
normal workstation. Use the repository’s loopback fixtures and disposable
QEMU/OVMF guests.

## License

Copyright 2026 Atilla Mert Akkaya. Licensed under the Apache License 2.0.
