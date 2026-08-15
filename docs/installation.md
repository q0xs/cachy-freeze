# Installation

## Requirements

- CachyOS/Arch Linux with KDE Plasma
- UEFI, GRUB, Btrfs root subvolume `@`
- EFI mounted at `/boot/efi` and no separate `/boot` filesystem
- AC power, physical access, recovery media, and a restorable backup

The installer stops when preflight detects an unsupported layout.

## One-command terminal install

```bash
curl -fsSL https://raw.githubusercontent.com/q0xs/cachy-freeze/main/install.sh | sudo bash
```

For high-assurance environments, download and inspect `install.sh` before
running it. The script installs required packages, clones the repository when
run from a pipe, installs the engine and GUI, publishes the initial Golden, and
leaves the next boot in THAWED mode.

## Graphical install

Open `cachyfreeze-setup.desktop`, run preflight, confirm either recovery readiness
or disposable-device acceptance, and select **Install CachyFreeze**.

## Independent next steps

- Enable FROZEN immediately from Setup by choosing a strong GRUB maintenance password.
- Or create users first from Users, then enable FROZEN.
- Or enable FROZEN first and add users later during THAWED maintenance.

User creation is never a prerequisite for installation or FROZEN activation.
Before creating an application-ready user, open Updates and run **Install / repair
applications**. The Users dialog can then create a standard account, enable
automatic sign-in if requested, publish the prepared account into Golden, and
schedule the next boot as FROZEN. It never reboots automatically.
After an operation finishes, use the application's reboot confirmation. Never
interrupt package, initramfs, GRUB, or Golden writes.
