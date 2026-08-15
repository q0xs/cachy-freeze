# CachyFreeze

CachyFreeze is an open-source, Btrfs-based system freeze and recovery manager
for CachyOS workstations. It restores managed machines to a known-good state
after reboot while providing a persistent maintenance mode for administrators.

Copyright 2026 Atilla Mert Akkaya. Licensed under the Apache License 2.0.

> [!CAUTION]
> CachyFreeze changes Btrfs subvolumes, initramfs, GRUB, and the boot process.
> Use a backed-up pilot device with physical access and recovery media.

## Core capabilities

- FROZEN mode recreates a writable `@active` root from read-only `@golden`.
- THAWED mode boots the persistent `@` maintenance root.
- Interrupted Golden/Active transactions are recovered during early boot.
- Repeated boot failures can restore the previous known-good Golden snapshot.
- Snapshot creation, verification, comparison, export, import, retention, and
  rollback are available from one desktop application.
- Standard-user lifecycle, protected updates, audit logs, and boot policy are
  managed from the same application.
- Privileged operations use a strict PolicyKit helper allow-list.
- Passwords and reusable password hashes travel through stdin, never command
  arguments or logs.

## Install

Install from a terminal with one command:

```bash
curl -fsSL https://raw.githubusercontent.com/q0xs/cachy-freeze/main/install.sh | sudo bash
```

Alternatively, launch `cachyfreeze-setup.desktop` and use the Setup page. Both
paths run the same preflight and privileged installer. Review `install.sh`
before piping it to a root shell in security-sensitive environments.

Installation leaves the system in THAWED maintenance mode. Engine installation,
user creation, and FROZEN activation are independent:

1. Install CachyFreeze.
2. Optionally create or manage users from the Users page at any time.
3. Enable FROZEN from Setup, or publish later changes from Overview.

No user account is required to enable FROZEN mode.

Application-ready standard users are created from the Users page while the
machine is in THAWED maintenance mode. Install or repair the managed application
set from Updates first. User creation then verifies the application commands,
prepares the KDE desktop and isolated MicroSIP Wine profile, confirms that the
account has no administrator membership, and captures its clean home template.
The creation dialog can publish Golden and schedule FROZEN immediately afterward;
reboot remains a separate, explicit action.

## Requirements

- CachyOS with KDE Plasma
- UEFI boot
- Btrfs root using the `@` subvolume
- GRUB
- EFI system partition mounted at `/boot/efi`
- no separate `/boot` filesystem
- a working `localadm` administrator account
- AC power, recovery media, and a recoverable backup

## Architecture

| Component | Responsibility |
| --- | --- |
| `app/` | PyQt6 desktop application, launcher, and PolicyKit boundary |
| `src/cachy_freeze/` | Snapshot, boot, settings, update, audit, and user domain logic |
| `deepfreeze/` | Btrfs early-boot reset, GRUB, initramfs, and systemd integration |
| `installer/` | Internal GUI-driven provisioning actions; not user entry points |
| `user/` | Managed-user desktop and home-reset integration |
| `policies/` | Managed application policies |
| `tests/` | Unit and setup-contract tests |

The persistent Btrfs model is documented in
[docs/architecture.md](docs/architecture.md).

## Development checks

```bash
ruff check src app/cachy_freeze_gui tests
ruff format --check src app/cachy_freeze_gui tests
python -m unittest discover -s tests -v
SHELLCHECK_OPTS=--severity=error bash deepfreeze/tests/static.sh
QT_QPA_PLATFORM=offscreen bash deepfreeze/tests/ui-smoke.sh
```

Btrfs loop, initramfs, GRUB, reboot, and power-loss tests must run only on a
disposable VM or an explicitly approved pilot device.

## Documentation

- [Installation guide](docs/installation.md)
- [Architecture](docs/architecture.md)
- [Boot recovery](docs/boot-recovery.md)
- [Development workflow](docs/development.md)
- [Test log](docs/testing/TEST-LOG.md)

## License

Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
