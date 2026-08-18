# Installation

## Requirements

- CachyOS/Arch Linux with KDE Plasma
- UEFI, GRUB, Btrfs root subvolume `@`
- EFI mounted at `/boot/efi` and no separate `/boot` filesystem
- AC power, physical access, recovery media, and a restorable backup

The installer stops when preflight detects an unsupported layout.

## ZIP-based graphical install

1. Open <https://github.com/q0xs/cachy-freeze> in a browser.
2. Select **Code → Download ZIP**, or use the direct
   [CachyFreeze main ZIP](https://github.com/q0xs/cachy-freeze/archive/refs/heads/main.zip).
3. Extract the entire archive and open the resulting `cachy-freeze-main` folder.
   Do not launch from the compressed-file preview and do not copy only selected
   files out of the archive.
4. Open `cachyfreeze-setup.desktop` and choose **Execute** if KDE prompts.
5. Run preflight, confirm either recovery readiness or disposable-device
   acceptance, and select **Install CachyFreeze**.

The launcher restores any helper execute permission lost during extraction,
installs the graphical dependency through PolicyKit when necessary, and opens
the unprivileged Setup page. Root operations still pass through the restricted
PolicyKit helper. Installation publishes the initial Golden and leaves the next
boot in THAWED mode.

Only a complete project archive is supported. Individual scripts, GitHub raw
file links, and launching directly from inside the ZIP are intentionally
unsupported. `install.sh` remains a complete-repository fallback, but the ZIP
and graphical Setup launcher are the documented end-user path.

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
