# CachyWorkstation portable provisioning

CachyWorkstation Setup is an administrator-operated product payload kept
separate from the normal CachyFreeze FROZEN/THAWED application. It does not
change CachyFreeze's Btrfs, initramfs, GRUB, Golden, or two-mode lifecycle.

Its job is to reconcile applications, per-user launchers, MicroSIP/Wine, and
the corporate idle policy on a CachyOS KDE Plasma 6 workstation. Provisioning
must finish while the machine is booted from persistent THAWED `@`. The
administrator manually tests the applications and runs CachyFreeze last.

## Deployment order

1. Install CachyOS with the supported Btrfs `@` layout.
2. Create the administrator account.
3. Manually create the employee account, for example `wrw1166`.
4. Confirm that the employee is not in `wheel`, `sudo`, or another
   administrator-equivalent group and has no direct sudoers rule.
5. Boot persistent THAWED `@`.
6. Run CachyWorkstation Setup for that existing employee.
7. Open and test Google Chrome, LibreOffice, AnyDesk, Zoiper, and MicroSIP as
   the employee.
8. Run `--check` and require every check to report `PASS`.
9. Freeze the computer and reboot into FROZEN. The login screen should
   preselect the employee account, not the administrator account.

Never provision or repair from disposable FROZEN `@active`. The installer
checks the root subvolume and fails before package or configuration changes.

## Build the portable file

From an unprivileged checkout:

```bash
bash packaging/build-workstation-installer.sh
```

The reproducible outputs are:

```text
dist/CachyWorkstation-Setup-1.0.1.run
dist/CachyWorkstation-Setup-1.0.1.run.sha256
```

The `.run` file contains the complete provisioner, reviewed AUR recipes,
launcher templates, the KDE idle-agent source, and integrity manifests. The
target does not need the Git repository. It still needs an internet connection
for CachyOS packages and hash-pinned upstream application files.

Copy both files to a target and verify them from their directory:

```bash
sha256sum --check CachyWorkstation-Setup-1.0.1.run.sha256
```

Published binaries and checksums for the current Workstation payload are
attached to the latest
[CachyFreeze v1.0.0rc8
release](https://github.com/q0xs/cachy-freeze/releases/tag/v1.0.0rc8).

## CLI

Initial reconcile:

```bash
sudo ./CachyWorkstation-Setup-1.0.1.run wrw1166
```

Read-only system/application health logic (apart from appending the audit log):

```bash
sudo ./CachyWorkstation-Setup-1.0.1.run --check wrw1166
```

Reconcile missing or changed managed files without deleting a valid Wine
prefix:

```bash
sudo ./CachyWorkstation-Setup-1.0.1.run --repair wrw1166
```

For development from a checkout, the equivalent entry point is:

```bash
sudo ./workstation-setup.sh wrw1166
```

The user must already exist. No command creates an employee, grants group
membership, edits sudoers, changes a password, freezes the system, or reboots
it.

## Application sources and idempotence

Official CachyOS repository packages are preferred when a configured signed
repository provides the requested package. Otherwise, the portable payload
builds its embedded reviewed AUR recipe as the isolated system account
`cachyworkbuild`; it never runs `makepkg` as root or as the employee.

The source snapshot currently pins:

| Application | Installation source |
| --- | --- |
| Google Chrome | reviewed `google-chrome` AUR recipe; official Google `.deb` |
| LibreOffice | signed `libreoffice-fresh` package |
| AnyDesk | reviewed `anydesk-bin` AUR recipe; official AnyDesk archive |
| Zoiper | reviewed `zoiper-bin` AUR recipe; official Zoiper Linux archive |
| MicroSIP | official MicroSIP 3.22.12 portable ZIP |

MicroSIP's archive SHA-256 is
`59738ca40c217a87da43a57ff891cc1d5c45c16ee62f578b2ccab05bca9b2362`.
The extracted 32-bit `MicroSIP.exe` has a second independent pinned checksum.
Download size, HTTPS transport, ZIP paths, archive type, executable type, and
both checksums are validated before use.

The employee prefix is:

```text
$HOME/.local/share/wineprefixes/microsip
```

Wine initialization and archive extraction run through `runuser` with a clean,
explicit target-user environment. A valid existing prefix is preserved on
repeated install/repair runs. Only managed distribution files are overwritten;
the prefix is never deleted. Recursive ownership is checked before the health
check can pass.

The five launchers are installed both to the user's XDG application-menu
directory and to the desktop directory reported by `xdg-user-dir DESKTOP`, so
localized desktop names are supported. They are mode `0755` (KDE's
authorization mechanism for launchers outside a standard menu path), have
validated desktop-file syntax, and are owned by the employee rather than root.
User-managed path components are rejected if they escape the home directory or
resolve through a symlink; per-user files are written with the employee's own
credentials rather than root's.

## Idle policy

The policy uses event-based KDE Frameworks 6 `KIdleTime`, which has native
Wayland and X11 backends. It does not derive inactivity from a display timeout
and does not poll mouse coordinates from shell.

```text
input stops
    |
    +-- 60 minutes total idle --> loginctl lock-session
    |
    +-- 120 minutes total idle -> systemctl poweroff
```

The policy intentionally blocks real system suspend while it is supervising the
employee session. Suspend can pause ordinary timers; guaranteed data cleanup
comes from the 120-minute poweroff and the next FROZEN boot rebuilding
`@active` from Golden.

Both timeouts are registered at the start of the same idle interval. Locking at
60 minutes therefore does not start a new two-hour timer. Real keyboard or
mouse input resets KDE's idle time; if the employee returns at 75 minutes, both
thresholds begin again from zero.

The root-owned `cachy-workstation-idle.service` supervises a target-user
KIdleTime agent in the active local KDE session. Only the root supervisor can
execute the verified session lock and system poweroff actions. It continuously
holds a systemd sleep inhibitor so PowerDevil or another automatic suspend does
not break the 60/120-minute timeline. Killing the unprivileged event agent does
not disable the policy; the root supervisor restarts it. The service starts at
boot and waits harmlessly when the configured employee has no active graphical
session.

KDE's own screen-lock configuration is also reconciled to 60 minutes with a
zero password grace period. The service remains the independent system-level
source for the 120-minute shutdown.

## Health checks and logs

The installer continues with independent application sections when one fails,
then reports each step and runs the complete health check. It exits nonzero and
prints `NOT READY FOR FREEZE` if any required step or check failed.

Checks cover:

- target account, home, UID/GID, and absence of admin-equivalent access;
- all five packages/executables and Wine's checked 32-bit runtime libraries;
- AnyDesk service enabled and active;
- MicroSIP archive/executable checksums and recursive prefix ownership;
- five application-menu entries and five executable, user-owned desktop files;
- KDE lock configuration;
- root-owned idle policy configuration and installed binaries;
- idle service enabled/active and its sleep inhibitor present;
- KDE login manager preselects the employee account without automatic login;
- secure setup log ownership/mode.

## Login screen default

Provisioning configures the active KDE display manager to preselect the
employee account on the login screen. It does not enable automatic login.

On Plasma Login Manager, `/etc/plasmalogin.conf` is reconciled with
`[Greeter] PreselectedUser` and `PreselectedSession`. On SDDM,
`/etc/sddm.conf.d/90-cachy-workstation-login.conf` keeps last-user/session
memory enabled and `/var/lib/sddm/state.conf` records the employee as the last
login user with the Plasma session.

The audit log is `/var/log/cachy-workstation-setup.log`, mode `0640`, owned by
`root:root`. It records timestamps, target user, mode, package/step results,
Wine/MicroSIP results, launchers, idle policy, and health outcomes. Scripts do
not enable command tracing and do not log passwords, tokens, or sudo policy
contents.

## Updating source pins

Rolling-distribution packages and proprietary downloads change over time. Do
not silently replace a URL or checksum in a released `.run` file. Review new
AUR commits and upstream files, update `workstation/vendor/aur`,
`AUR-REVISIONS.txt`, and `workstation/assets/microsip-source.conf`, run all
tests, bump `workstation/VERSION`, and publish a new `.run` plus checksum.
