# CachyFreeze

[![Quality checks](https://github.com/q0xs/cachy-freeze/actions/workflows/static-tests.yml/badge.svg?branch=main)](https://github.com/q0xs/cachy-freeze/actions/workflows/static-tests.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-CachyOS-5865F2.svg)](https://cachyos.org/)

CachyFreeze is a graphical Btrfs freeze and recovery manager for managed
CachyOS workstations. Administrators maintain a persistent system in THAWED
mode, publish a verified Golden baseline, and return each FROZEN boot to that
known-good state.

![CachyFreeze Management Center](docs/images/cachy-freeze-management-center-preview.png)

> [!CAUTION]
> CachyFreeze changes Btrfs subvolumes, initramfs, GRUB, and the boot process.
> Use a backed-up pilot device with physical access and recovery media. The
> installer intentionally stops on unsupported disk or boot layouts.

## What it provides

- FROZEN mode recreates writable `@active` from read-only `@golden` on boot.
- THAWED mode boots the persistent `@` maintenance system.
- Interrupted Golden and Active rotations use durable transaction recovery.
- Repeated boot failures can restore the previous healthy Golden baseline.
- Snapshots can be created, verified, compared, exported, imported, retained,
  rolled back, and published from one desktop application.
- Application-ready standard users receive verified desktop shortcuts, KDE
  defaults, Chrome policy, and an isolated MicroSIP Wine profile.
- The administrator remains fully privileged but is hidden from the graphical
  login screen during FROZEN operation.
- PolicyKit keeps the graphical application unprivileged and restricts root
  operations to an explicit helper allow-list.
- Passwords and reusable password hashes travel through stdin, never through
  command arguments, environment variables, or logs.

## Supported system

CachyFreeze currently requires all of the following:

- CachyOS with KDE Plasma
- UEFI firmware
- Btrfs root using the `@` subvolume
- GRUB with the EFI system partition mounted at `/boot/efi`
- no separate `/boot` filesystem
- an existing `localadm` administrator account
- AC power, recovery media, and a restorable backup

It is not a generic installer for arbitrary Arch, ext4, BIOS, systemd-boot, or
custom Btrfs layouts.

## Download the complete installer

The recommended method clones the complete repository, preserving executable
permissions and downloading every installer, application, policy, user asset,
test, and recovery component required by CachyFreeze:

```bash
git clone --depth 1 --branch main https://github.com/q0xs/cachy-freeze.git
cd cachy-freeze
sudo ./install.sh
```

You can also download the complete source bundle directly:

**[Download the complete CachyFreeze installer (ZIP)](https://github.com/q0xs/cachy-freeze/archive/refs/heads/main.zip)**

After extracting the ZIP, run this inside the extracted directory:

```bash
chmod +x install.sh app/cachy-freeze-setup app/cachy-freeze-manager-helper
sudo ./install.sh
```

The root-level [`install.sh`](install.sh) is the public terminal installer. It
runs the supported-layout preflight, installs the complete engine and graphical
management application, publishes the initial Golden baseline, and leaves the
next boot safely scheduled as THAWED.

### Bootstrap installation

For a disposable pilot or after reviewing the remote script, the short bootstrap
command remains available:

```bash
curl -fsSL https://raw.githubusercontent.com/q0xs/cachy-freeze/main/install.sh | sudo bash
```

The downloaded bootstrap is not a partial installation: it installs Git, clones
the complete `main` repository into a temporary directory, runs the same
`installer/install-cachyfreeze.sh`, and removes only that temporary clone after
completion.

### Graphical setup

To start from the desktop, clone or extract the complete installer and launch
[`cachyfreeze-setup.desktop`](cachyfreeze-setup.desktop). The graphical Setup
page uses the same preflight and privileged installer as the terminal entrypoint.

## First workstation setup

Installation, application installation, user creation, and FROZEN activation
are deliberately independent:

1. Install CachyFreeze. The machine remains in THAWED maintenance mode.
2. Open **Updates** and select **Install / repair applications**.
3. Open **Users** and select **Create ready user**.
4. Use a lowercase login such as `wrw21166`; the account is created with native
   CachyOS standard-user defaults and is rejected if it unexpectedly has
   administrator membership.
5. Keep **Publish Golden and schedule FROZEN mode after creation** enabled if the
   next manually initiated reboot should present the prepared employee account.

User provisioning verifies Chrome, Slack, LibreOffice, Zoiper, AnyDesk, Wine,
and MicroSIP before capturing the clean home template. Failure removes the
partial account and candidate template. CachyFreeze does not rewrite the
account's native group membership.

No operation in the creation dialog reboots the computer automatically.

## Boot model

| Subvolume | Role |
| --- | --- |
| `@` | Persistent THAWED maintenance root |
| `@golden` | Read-only known-good baseline |
| `@active` | Disposable writable FROZEN runtime |
| `@cachy-state` | Persistent settings, audit, health, and transaction state |
| `@cachy-snapshots` | Managed recovery snapshots |

FROZEN is the passwordless daily boot path. THAWED maintenance is protected by
the GRUB `cachyadmin` credential configured during activation.

## Repository layout

| Path | Responsibility |
| --- | --- |
| `install.sh` | Public complete-repository terminal installer |
| `app/` | PyQt6 Management Center, launcher, PolicyKit helper, desktop files |
| `src/cachy_freeze/` | Snapshot, boot, settings, update, audit, and user logic |
| `deepfreeze/` | Btrfs early-boot reset, GRUB, initramfs, systemd, safe tests |
| `installer/` | Internal verified installation and maintenance operations |
| `user/` | Managed-user desktop assets and FROZEN home reset integration |
| `policies/` | Managed application policies |
| `vendor/aur/` | Reviewed AUR build inputs used by application installation |
| `tests/` | Python and graphical contract tests |
| `docs/` | Architecture, installation, recovery, development, and test evidence |

## Validation

The normal local quality gate is:

```bash
ruff check src app/cachy_freeze_gui tests
ruff format --check src app/cachy_freeze_gui tests
PYTHONPATH=src:app python -m unittest discover -s tests -v
SHELLCHECK_OPTS=--severity=error bash deepfreeze/tests/static.sh
QT_QPA_PLATFORM=offscreen bash deepfreeze/tests/ui-smoke.sh
bash deepfreeze/tests/grub-generation.sh
```

Loop-backed Btrfs, initramfs, reboot, recovery, and power-loss tests must run only
on a disposable VM or an explicitly approved pilot device. Executed evidence is
recorded in [`docs/testing/TEST-LOG.md`](docs/testing/TEST-LOG.md).

## Documentation

- [Installation guide](docs/installation.md)
- [Architecture](docs/architecture.md)
- [Boot recovery](docs/boot-recovery.md)
- [Development workflow](docs/development.md)
- [Test evidence](docs/testing/TEST-LOG.md)

## License

Copyright 2026 Atilla Mert Akkaya.

Licensed under the Apache License 2.0. See [LICENSE](LICENSE) and
[NOTICE](NOTICE).
