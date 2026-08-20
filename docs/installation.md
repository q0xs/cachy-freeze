# Installation

## Requirements

- CachyOS/Arch Linux with KDE Plasma
- UEFI, GRUB, Btrfs root subvolume `@`
- EFI mounted at `/boot/efi` and no separate `/boot` filesystem
- AC power, physical access, recovery media, and a restorable backup

The installer stops when preflight detects an unsupported layout.
The idle power policy additionally requires an RTC wake alarm exposed at
`/sys/class/rtc/rtc0/wakealarm`; missing RTC support does not make the Btrfs
freeze engine unsafe, so it is reported separately instead of aborting setup.

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
The Users page presents the intended order directly: first run **1. Install /
repair applications**, then **2. Create ready user**. Account creation can enable
automatic sign-in, but it never publishes Golden, schedules FROZEN, or reboots.
Sign in to the prepared account, finish its desktop checks, and only then publish
Golden / enable FROZEN from that session.
After an operation finishes, use the application's reboot confirmation. Never
interrupt package, initramfs, GRUB, or Golden writes.

## Automatic idle power policy

Installation enables `cachy-freeze-idle-power.service` automatically. With no
keyboard or pointer activity for one hour, the workstation enters a timed sleep.
If it remains asleep for the following hour, the RTC wakes it and CachyFreeze
powers it off, for two hours total unattended time. Waking it manually before
the deadline cancels shutdown; another complete one-hour idle period is required
before sleep can be scheduled again.

If RTC wake support is unavailable or unwritable, CachyFreeze reports the policy
as unsupported and does not suspend the workstation, because sleep without a
reliable shutdown deadline would violate the requested policy. Support status is
visible in Management Center and in the redacted diagnostic bundle.
