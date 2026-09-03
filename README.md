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
- **Status:** the app shows the current mode as **FROZEN** or **THAWED**.
- **Workstation buttons:** the installer can prepare employee apps before the
  first freeze.
- **Workstation health report:** PASS/FAIL output is visible in the app, and
  the first CachyFreeze install is blocked until the selected employee passes
  the final check.

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

Download both files from the
[v1.0.0rc9 release candidate](https://github.com/q0xs/cachy-freeze/releases/tag/v1.0.0rc9):

- `CachyFreeze-Installer-1.0.0rc9.run`
- `CachyFreeze-Installer-1.0.0rc9.run.sha256`

Verify them:

```bash
cd "$(xdg-user-dir DOWNLOAD)"
sha256sum --check CachyFreeze-Installer-1.0.0rc9.run.sha256
chmod 0755 CachyFreeze-Installer-1.0.0rc9.run
```

Continue only if the checksum prints:

```text
CachyFreeze-Installer-1.0.0rc9.run: OK
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
./CachyFreeze-Installer-1.0.0rc9.run
```

6. Approve the PolicyKit prompt.
7. Enter the employee username.
8. Click **INSTALL / REPAIR WORKSTATION**.
9. Log in as the employee and open these apps once:
   Google Chrome, LibreOffice, AnyDesk, Zoiper, MicroSIP.
10. Return to the administrator account.
11. Enter the employee username again and click **CHECK WORKSTATION**.
12. Continue only if the check reports `OVERALL: PASS` and
    `Ready for freeze: YES`. The check includes the KDE login screen
    preselecting the employee account without automatic login, plus the
    60-minute lock and 120-minute poweroff policy.
13. Enter the GRUB maintenance password twice.
14. Click **INSTALL CACHYFREEZE**.
15. When setup succeeds, click **REBOOT NOW**.

After reboot, CachyFreeze should show **FROZEN**, and the login screen should
preselect the employee account.

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

## Remote Fleet Management with Ansible

CachyFreeze includes a monorepo-managed Ansible control plane in `ansible/` for
lab and production workstation fleets. A dedicated Arch/CachyOS controller can
clone this repository and run:

```bash
cd ansible
./setup-controller.sh
```

The controller uses `LocalAdm` over SSH, reads per-host employee identities such
as `WRW21166` from `inventory/hosts.ini`, and runs playbooks with fleet tuning
from `ansible.cfg` (`forks = 50`, SSH pipelining enabled). Lab defaults to
`batch_size: "100%"`; production defaults to `batch_size: "20%"` for rolling
updates across 200+ workstations.

Common operations:

```bash
ansible-playbook playbooks/provision.yml --limit lab --ask-become-pass
ansible-playbook playbooks/maintenance.yml --limit production
ansible-playbook playbooks/status.yml --limit all
```

Remote maintenance uses `cachy-freeze thaw --authorized` to schedule one
passwordless THAWED boot by setting `cachy_remote_auth=1` in GRUB. The THAWED
boot verification service immediately consumes the flag by writing
`cachy_remote_auth=0`, so the exception is one-time only. If update or
Workstation validation fails, the maintenance playbook does not freeze the
machine; it leaves the host THAWED and writes a failure marker for admin review.

See [ansible/README.md](ansible/README.md) for inventory, role, emergency thaw,
freeze, and lab-to-production rollout details.

## Installed App

The normal CachyFreeze app keeps the workflow small:

- **Status:** displays the current verified mode as **FROZEN** or **THAWED**.
- **FREEZE COMPUTER:** save the current THAWED system as the new Golden and
  schedule FROZEN.
- **THAW COMPUTER:** schedule the persistent THAWED system for the next boot.
- **REBOOT NOW:** shown only after a mode change.

CachyFreeze never reboots automatically.

## Idle Data Cleanup

CachyWorkstation enforces the employee idle policy from a root-owned service:

```text
60 minutes idle  -> lock the KDE session
120 minutes idle -> system poweroff
```

The policy intentionally blocks real suspend while supervising the employee
session. Suspend can pause timers and leave the current FROZEN runtime in
memory. The reliable cleanup point is the 120-minute poweroff, followed by the
next FROZEN boot recreating disposable `@active` from Golden.

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
