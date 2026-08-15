# Installation

## Requirements

- CachyOS/Arch Linux with KDE Plasma
- UEFI, GRUB, Btrfs root subvolume `@`
- EFI mounted at `/boot/efi` and no separate `/boot` filesystem
- AC power, physical access, recovery media, and a restorable backup

The installer stops when preflight detects an unsupported layout.

## Complete-repository terminal install

```bash
git clone --branch main https://github.com/q0xs/cachy-freeze.git
cd cachy-freeze
sudo ./install.sh
```

The installer supports only a complete Git clone. Review the repository before
running `install.sh`; partial downloads and standalone remote-script execution
are intentionally unsupported. The installer installs the engine and GUI,
publishes the initial Golden, and leaves the next boot in THAWED mode.

## Graphical install

From the complete clone, open `cachyfreeze-setup.desktop`, run preflight, confirm
either recovery readiness or disposable-device acceptance, and select
**Install CachyFreeze**.

## Independent next steps

- Enable FROZEN immediately from Setup by choosing a strong GRUB maintenance
  password. The GRUB maintenance username is always `cachyadmin`; it is shown
  beside the password fields and is separate from Linux user accounts.
- Or create users first from Users, then enable FROZEN.
- Or enable FROZEN first and add users later during THAWED maintenance.

User creation is never a prerequisite for installation or FROZEN activation.
Before creating an application-ready user, open Updates and run **Install / repair
applications**. The Users dialog can then create a standard account, enable
automatic sign-in if requested, publish the prepared account into Golden, and
schedule the next boot as FROZEN. It never reboots automatically.
After an operation finishes, use the application's reboot confirmation. Never
interrupt package, initramfs, GRUB, or Golden writes.
