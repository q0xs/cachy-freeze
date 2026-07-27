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
- hides `localadm` from the graphical login screen in Frozen mode;
- restores both the employee and `localadm` home directories from clean
  templates during every Frozen boot;
- maintains a Golden Btrfs snapshot from which the active Frozen system is
  recreated;
- displays one GRUB entry whose title reflects the selected mode: **FROZEN**
  or **THAWED**.

## Boot modes

| Mode | Purpose | Persistence |
| --- | --- | --- |
| **FROZEN** | Normal employee operation | Local changes are removed on reboot |
| **THAWED** | Persistent maintenance and updates | Changes are retained |
| **Golden** | Published source snapshot for Frozen mode | Not booted directly |

FROZEN boots without a GRUB password. THAWED requires the `cachyadmin` GRUB
user and the password configured during installation.

Changes made in THAWED mode do not automatically become the new Frozen
baseline. Publish them with `BAKIM-02-DEGISIKLIKLERI-YAYINLA.sh`.

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

## Quick installation

Use the top-level entry scripts. Do not run scripts under `installer/` or
`deepfreeze/` individually during a normal installation.

1. Start provisioning:

   ```bash
   bash ./ADIM-01-KURULUMU-BASLAT.sh
   ```

2. Sign in to the employee account and verify:

   - Chrome, Slack, AnyDesk, LibreOffice, MicroSIP, and Zoiper;
   - microphone, speaker, and headset input/output;
   - an administrative desktop action asks for the `localadm` password;
   - the employee account is not a direct member of `wheel` or `sudo`.

3. Return to `localadm`, complete the installation, and publish the Golden
   snapshot:

   ```bash
   bash ./ADIM-02-KURULUMU-TAMAMLA.sh
   sudo reboot
   ```

4. During the first FROZEN test, create a temporary file in both managed
   accounts when practical, reboot, and confirm that it is removed.

See **[KURULUM-TR.md](KURULUM-TR.md)** for the full Turkish procedure and
expected prompts.

## Maintenance

Schedule the next boot as THAWED:

```bash
bash ./BAKIM-01-COZ.sh
sudo reboot
```

After completing maintenance, publish the updated Golden snapshot and return
to FROZEN:

```bash
bash ./BAKIM-02-DEGISIKLIKLERI-YAYINLA.sh
sudo reboot
```

## Repository layout

```text
.
├── ADIM-01-KURULUMU-BASLAT.sh
├── ADIM-02-KURULUMU-TAMAMLA.sh
├── BAKIM-01-COZ.sh
├── BAKIM-02-DEGISIKLIKLERI-YAYINLA.sh
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
```

The static suite checks Bash syntax, core configuration, desktop entries, JSON,
and—when available—ShellCheck and systemd units. Run boot-chain and Btrfs
integration tests only on a dedicated test device.

## Additional documentation

- [Turkish installation guide](KURULUM-TR.md)
- [Pilot-device checklist](PILOT-NOTLARI.md)
- [GitHub workflow on Linux](GITHUB-ILE-CALISMA.md)
- [Boot recovery notes](KURTARMA-EKRAN-GELMEZSE.txt)
- [Optional legacy USB workflow](USB-KURULUM.txt)

## Safety and backups

- GitHub protects the project files; it is not a disk image or a replacement
  for bootable recovery media.
- Never commit passwords, access tokens, device UUIDs, or real user data.
- Unpushed changes made in FROZEN mode disappear after reboot.
- Do not manually delete the `@`, `@golden`, or `@active` Btrfs subvolumes.
- Do not run `btrfs check --repair` without expert guidance.
- Do not cut power while freezing or publishing snapshots.
