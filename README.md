<p align="center">
  <img src="app/cachy_freeze_gui/assets/cachy-freeze.png" width="168" alt="CachyFreeze logo">
</p>

<h1 align="center">CachyFreeze</h1>

CachyFreeze freezes a CachyOS workstation so every reboot returns it to the
approved baseline.

> Turkish setup guide: [KURULUM-TR.md](KURULUM-TR.md)

## What It Does

- **FROZEN:** each reboot starts from the saved Golden baseline.
- **THAWED:** changes persist, so the administrator can update or repair the
  workstation.
- **Workstation buttons:** the installer can prepare employee apps before the
  first freeze.

The current single-file installer includes CachyWorkstation. Target computers
do not need a Git checkout.

## Requirements

- CachyOS or Arch Linux with KDE Plasma
- UEFI + GRUB
- Btrfs root subvolume `@`
- EFI mounted at `/boot/efi`
- `/boot` inside the Btrfs root, not a separate filesystem
- internet access during setup
- recovery media and a restorable backup

Unsupported layouts stop before CachyFreeze changes Btrfs or GRUB.

## Download

Download both files from the latest release:

- `CachyFreeze-Installer-1.0.0rc7.run`
- `CachyFreeze-Installer-1.0.0rc7.run.sha256`

Verify them:

```bash
cd "$(xdg-user-dir DOWNLOAD)"
sha256sum --check CachyFreeze-Installer-1.0.0rc7.run.sha256
chmod 0755 CachyFreeze-Installer-1.0.0rc7.run
```

Continue only if the checksum prints:

```text
CachyFreeze-Installer-1.0.0rc7.run: OK
```

## Fresh Employee Workstation

1. Install CachyOS with the supported Btrfs `@` layout.
2. Create the administrator account.
3. Create the employee account as a standard user. Do not add it to `wheel`,
   `sudo`, `docker`, `lxd`, or any administrator-equivalent group.
4. Log in once as the employee, let KDE create the desktop folders, then log
   back in as the administrator.
5. Run the installer without `sudo`:

```bash
./CachyFreeze-Installer-1.0.0rc7.run
```

6. Approve the PolicyKit prompt.
7. Enter the employee username.
8. Click **INSTALL / REPAIR WORKSTATION**.
9. Log in as the employee and open these apps once:
   Google Chrome, LibreOffice, AnyDesk, Zoiper, MicroSIP.
10. Return to the administrator account.
11. Enter the employee username again and click **CHECK WORKSTATION**.
12. Continue only if the check reports `OVERALL: PASS` and
    `Ready for freeze: YES`.
13. Enter the GRUB maintenance password twice.
14. Click **INSTALL CACHYFREEZE**.
15. When setup succeeds, click **REBOOT NOW**.

After reboot, CachyFreeze should show **FROZEN**.

## Existing CachyFreeze Machine

1. Open CachyFreeze.
2. Click **THAW COMPUTER**.
3. Click **REBOOT NOW**.
4. Confirm the app shows **THAWED** after reboot.
5. Install or repair Workstation from the app.
6. Run **CHECK WORKSTATION**.
7. Test the five employee apps manually.
8. Click **FREEZE COMPUTER**.
9. Click **REBOOT NOW**.

Never install, repair, or update Workstation while booted from FROZEN
`@active`.

## Installed App

The normal CachyFreeze app keeps the workflow small:

- **FREEZE COMPUTER:** save the current THAWED system as the new Golden and
  schedule FROZEN.
- **THAW COMPUTER:** schedule the persistent THAWED system for the next boot.
- **REBOOT NOW:** shown only after a mode change.

CachyFreeze never reboots automatically.

## Developer Build

```bash
bash packaging/build-installer.sh
```

The output is written to `dist/` with a matching SHA-256 file.

Useful checks:

```bash
ruff check .
PYTHONPATH=src:app QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests -v
bash deepfreeze/tests/static.sh
bash deepfreeze/tests/ui-smoke.sh
bash deepfreeze/tests/grub-generation.sh
bash workstation/tests/static.sh
```

More detail is in [docs/installation.md](docs/installation.md),
[docs/workstation-provisioning.md](docs/workstation-provisioning.md), and
[docs/architecture.md](docs/architecture.md).
