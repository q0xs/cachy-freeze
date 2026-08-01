# CachyOS Corporate Laptop Provisioning

This repository provisions CachyOS laptops for shared call-center and sales
workstations. It installs the required applications, creates a restricted
employee account, and restores the machine to a clean **Frozen** state after
every reboot.

> [!IMPORTANT]
> For the complete installation procedure in Turkish, read
> **[KURULUM-TR.md](KURULUM-TR.md)**.

> [!CAUTION]
> These scripts modify the boot chain, initramfs, GRUB configuration, and Btrfs
> subvolumes. Perform the first installation on a backed-up pilot device while
> you have physical access to it.

## Overview

The project validates the required UEFI, Btrfs, and GRUB layout before making
changes. It then:

- installs the workstation applications;
- creates the managed employee account;
- enables microphone, speaker, headset, video, input, and realtime access;
- requests the `localadm` administrator password for privileged desktop
  actions instead of immediately denying them;
- gives the employee a normal Windows-standard-user-like desktop experience:
  user settings remain available, while system changes require Polkit
  authentication with the `localadm` password;
- starts the employee's Plasma session with the Breeze Dark theme;
- hides `localadm` from the graphical login screen in Frozen mode;
- restores both the employee and `localadm` home directories from clean
  templates during every Frozen boot;
- maintains a Golden Btrfs snapshot from which the active Frozen system is
  recreated;
- records snapshot metadata, checksums, history, health, exports, imports,
  comparisons, cleanup, and rollback counters;
- recovers interrupted Golden/Active transactions and automatically restores
  the previous known-good Golden after repeated failed boots;
- provides GUI pages for dashboards, snapshots, standard users, updates,
  audit logs, boot policy, automatic snapshots, network policy, and settings;
- performs privileged work only through a PolicyKit-authenticated allow-list
  helper; passwords use stdin and never appear in process lists;
- displays one GRUB entry whose title reflects the selected mode: **FROZEN**
  or **THAWED**.

## Application preview

![Cachy Freeze Management Center dashboard](docs/images/cachy-freeze-management-center-preview.png)

The preview is rendered from the real PyQt6 application with representative,
non-production status data. The installed application reads the actual Btrfs,
boot-health, snapshot, update, and audit state from the workstation.

## Codex quick handoff — live CachyOS laptop test

When this repository is reopened for the physical laptop test, start here
instead of redesigning the project:

1. Read `MIMARI-TR.md`, `KURULUM-TR.md`, and `PILOT-NOTLARI.md`; then inspect
   `git status --short` and the latest three commits.
2. Keep the Windows host and CachyOS target strictly separate. Btrfs, GRUB,
   initramfs, snapshot, freeze, and rollback commands may run only on the
   dedicated CachyOS laptop or a disposable CachyOS VM.
3. Before installation, make a recoverable backup and confirm **UEFI + Btrfs +
   GRUB**, `/boot/efi`, and no separate `/boot`. Stop if preflight rejects the
   layout; do not bypass it.
4. Use only the numbered top-level installers for normal deployment. Daily
   operation after bootstrap must use **Cachy Freeze Management Center**.
5. Test all six GUI pages, both `localadm` and a standard user, FROZEN/THAWED
   and one-time THAWED boots, snapshot create/full verify/rollback, updates,
   autologin, home reset, audio devices, and a real MicroSIP call.
6. Exercise unexpected shutdown and boot rollback only after a healthy Golden
   exists. Never cut power during Golden publication or package installation.
7. On failure, preserve evidence before changing anything: application audit
   logs, `journalctl -b`, `findmnt`, `btrfs subvolume list /`, boot mode, and the
   exact failed step. Do not run `btrfs check --repair`.

Previous acceptance covered real Btrfs loop-device transactions, power-loss
recovery, 25-snapshot stress, Linux user lifecycle, PyQt6 smoke testing,
MicroSIP 3.22.12 under Wine, and initramfs builds for two CachyOS kernels. The
remaining production acceptance is the physical **UEFI/GRUB reboot chain** on
the backed-up pilot laptop.

## Boot modes

| Mode | Purpose | Persistence |
| --- | --- | --- |
| **FROZEN** | Normal employee operation | Local changes are removed on reboot |
| **THAWED** | Persistent maintenance and updates | Changes are retained |
| **Golden** | Published source snapshot for Frozen mode | Not booted directly |

FROZEN boots without a GRUB password. THAWED requires the `cachyadmin` GRUB
user and the password configured during installation.

Changes made in THAWED mode do not automatically become the new Frozen
baseline. Publish them with `11-BAKIM-YAYINLA-VE-DONDUR.sh`.

## Requirements

- CachyOS with KDE Plasma
- UEFI boot
- Btrfs root filesystem
- GRUB
- EFI system partition mounted at `/boot/efi`
- no separate `/boot` filesystem
- internet access
- local `localadm` account with `sudo` privileges and an active password

The installer stops when it detects an unsupported disk or boot layout.

## Clone the repository

Run this from a clean CachyOS installation or while the system is in THAWED
mode:

```bash
sudo pacman -S --needed git github-cli
gh auth login
mkdir -p ~/Projeler
cd ~/Projeler
gh repo clone q0xs/CachyOS-USB-Kurulum
cd CachyOS-USB-Kurulum
```

The repository is private, so the authenticated GitHub account must have
access.

## Installation file order

Use the top-level entry scripts. Do not run scripts under `installer/` or
`deepfreeze/` individually during a normal installation. The filenames are
numbered in their intended order:

| File | When to use it |
| --- | --- |
| `01-TAM-KURULUMU-BASLAT.sh` | Starts the complete corporate workstation installation |
| `02-TAM-KURULUMU-TAMAMLA.sh` | Run after testing the employee applications |
| `03-ALTERNATIF-SADECE-FREEZE-UYGULAMASI.sh` | Alternative to 01–02; installs only the graphical Freeze Manager |
| `10-BAKIM-ERIT.sh` | Schedules the next boot in persistent maintenance mode |
| `11-BAKIM-YAYINLA-VE-DONDUR.sh` | Publishes maintenance changes and returns to Frozen mode |

Do not run `03` after a complete `01`–`02` installation. It is a standalone
alternative for computers that need only the Freeze Manager.

## Complete workstation installation

1. Start provisioning:

   ```bash
   bash ./01-TAM-KURULUMU-BASLAT.sh
   ```

2. Sign in to the employee account and verify:

   - Chrome, Slack, AnyDesk, LibreOffice, MicroSIP, and Zoiper;
   - microphone, speaker, and headset input/output;
   - an administrative desktop action asks for the `localadm` password;
   - the employee account is not a direct member of `wheel` or `sudo`.

3. Return to `localadm`, complete the installation, and publish the Golden
   snapshot:

   ```bash
   bash ./02-TAM-KURULUMU-TAMAMLA.sh
   sudo reboot
   ```

4. During the first FROZEN test, create a temporary file in both managed
   accounts when practical, reboot, and confirm that it is removed.

See **[KURULUM-TR.md](KURULUM-TR.md)** for the full Turkish procedure and
expected prompts.

## Standalone freeze manager

To install only the reusable graphical freeze/thaw manager on a compatible
CachyOS computer:

```bash
bash ./03-ALTERNATIF-SADECE-FREEZE-UYGULAMASI.sh
```

The installer detects that computer's Btrfs UUID and installs a
Polkit-authenticated **Cachy Freeze Manager** PyQt6 desktop application. The
management center includes six wired pages:

- **Dashboard:** running/scheduled mode, disk, snapshot and boot health.
- **Snapshots:** create, verify, compare, export, import, delete and rollback.
- **Users:** standard account lifecycle, password, lock and autologin policy.
- **Updates:** read-only checks, corporate application verification/repair,
  and snapshot-protected THAWED updates.
- **Audit logs:** structured INFO/WARNING/ERROR operation history.
- **Settings:** freeze, snapshot, update, theme, language, boot, log, network,
  and automatic snapshot policy.

Both actions show confirmation and progress feedback and offer to reboot when
finished. The repository does not embed machine-specific identifiers. The
supported layout is UEFI + Btrfs + GRUB, with the EFI partition mounted at
`/boot/efi` and no separate `/boot` filesystem.

## Maintenance

Daily maintenance does not require a terminal. In **Cachy Freeze Management
Center**, schedule persistent or one-time THAWED boot, accept its reboot
prompt, then use the Updates page. A protected update creates a rollback
snapshot before pacman and publishes a new Golden after verification. Return
to FROZEN from Dashboard or Settings and accept the reboot prompt.

The numbered shell entry points remain deployment/bootstrap tools for the
technician performing the first installation.

## Repository layout

```text
.
├── 01-TAM-KURULUMU-BASLAT.sh
├── 02-TAM-KURULUMU-TAMAMLA.sh
├── 03-ALTERNATIF-SADECE-FREEZE-UYGULAMASI.sh
├── 10-BAKIM-ERIT.sh
├── 11-BAKIM-YAYINLA-VE-DONDUR.sh
├── app/           # Graphical freeze/thaw manager and Polkit policy
├── KURULUM-TR.md  # Complete Turkish installation guide
├── deepfreeze/    # Btrfs, initramfs, and GRUB infrastructure
├── installer/     # Provisioning and publishing steps
├── policies/      # Managed application policies
├── user/          # Employee account services and desktop entries
└── vendor/        # Offline or reviewed packaging helpers
```

## Validation

Run the repository's static checks:

```bash
bash ./deepfreeze/tests/static.sh
bash ./deepfreeze/tests/grub-generation.sh
sudo bash ./deepfreeze/tests/integration-btrfs.sh
sudo bash ./deepfreeze/tests/integration-engine.sh
sudo bash ./deepfreeze/tests/integration-users.sh
bash ./deepfreeze/tests/ui-smoke.sh
```

The static suite checks Bash syntax, core configuration, desktop entries, JSON,
and—when available—ShellCheck and systemd units. Run boot-chain and Btrfs
integration tests only on a dedicated test device.

## Additional documentation

- [Turkish installation guide](KURULUM-TR.md)
- [Pilot-device checklist](PILOT-NOTLARI.md)
- [GitHub workflow on Linux](GITHUB-ILE-CALISMA.md)
- [Boot recovery notes](KURTARMA-EKRAN-GELMEZSE.txt)
- [Platform architecture and recovery model](MIMARI-TR.md)
- [Optional legacy USB workflow](USB-KURULUM.txt)

## Safety and backups

- GitHub protects the project files; it is not a disk image or a replacement
  for bootable recovery media.
- Never commit passwords, access tokens, device UUIDs, or real user data.
- Unpushed changes made in FROZEN mode disappear after reboot.
- Do not manually delete the `@`, `@golden`, or `@active` Btrfs subvolumes.
- Do not run `btrfs check --repair` without expert guidance.
- Do not cut power while freezing or publishing snapshots.
