# Architecture

CachyFreeze separates persistent maintenance, immutable baseline, and disposable runtime state.

| Subvolume | Purpose |
| --- | --- |
| `@` | Persistent THAWED maintenance root |
| `@golden` | Read-only known-good baseline |
| `@active` | Writable FROZEN root recreated from Golden |
| `@cachy-state` | Persistent metadata, audit, and transaction state |
| `@cachy-snapshots` | Managed snapshots |

The GRUB entry supplies `cachy.freeze=0` or `cachy.freeze=1`. In FROZEN mode,
the initramfs reset service validates the root device and transaction journal,
then recreates Active atomically from Golden before switching root.

The PyQt6 application is unprivileged. It calls a narrow PolicyKit helper with
validated action names and arguments. The helper invokes the Python engine and
internal installer scripts without `shell=True`. Passwords use stdin only.

Engine installation, user management, and FROZEN activation are deliberately
independent. Templates are refreshed for `localadm` and for any optional managed
users that exist; the absence of a managed user never blocks Golden publication.

GUI-created users follow the native `useradd` standard-account path. CachyFreeze
does not rewrite their group membership. Before the account is committed, a
verified provisioner checks the managed application set, installs desktop and KDE
defaults, creates the per-user MicroSIP Wine prefix, rejects unexpected
administrator membership, and only then captures the FROZEN home template.
Provisioning failure removes the partial account and candidate template.

Automatic-login settings target the display manager that is actually enabled:
Plasma Login Manager uses `/etc/plasmalogin.conf`, while compatible SDDM systems
use the CachyFreeze-owned SDDM drop-in. User creation itself never publishes
Golden or changes the scheduled boot mode.

Golden/Active replacement uses staged subvolumes and a durable transaction
journal. Early boot can roll forward interrupted publication. Boot-health resets
the failure counter after graphical startup; repeated failures can restore the
previous healthy Golden.
