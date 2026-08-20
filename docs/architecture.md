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
Plasma Login Manager uses the CachyFreeze-owned
`/etc/plasmalogin.conf.d/90-cachy-freeze-autologin.conf` drop-in without editing
the administrator's main configuration, while compatible SDDM systems use the
CachyFreeze-owned SDDM drop-in. User creation itself never publishes Golden or
changes the scheduled boot mode.

Golden/Active replacement uses staged subvolumes and a durable transaction
journal. Early boot can roll forward interrupted publication. Boot-health resets
the failure counter only after a pending first-FROZEN validation proves the
expected boot ID, FROZEN mode, `@active` root, Golden/Active presence, home reset,
administrator restriction, and graphical managed-user session. Repeated failures
can restore the previous healthy Golden.

Finalization is logout-aware. The GUI asks the desktop to end the normal session,
while a persistent system service waits for managed sessions and processes to
leave before it publishes Golden and schedules FROZEN as one locked operation.
A timeout fails closed and leaves an auditable pending/error state.

The installed idle-power service reads the logind seat idle hint. After one hour
without activity it uses an RTC-timed suspend for one further hour. A complete
timed sleep powers off the workstation; a manual/early wake clears the RTC alarm,
cancels shutdown, and requires a new active-to-idle cycle. Missing RTC support is
reported as unsupported and never triggers a partial suspend policy.

Application provisioning, finalization, first-boot validation, diagnostics,
power policy, and state versioning are separate engine modules. Persistent state
has an explicit schema and idempotent migration record. Live deployment stages
and compiles the candidate, backs up only managed paths, migrates and verifies
the installation, and restores the allow-listed backup set on failure.

Diagnostic export is bounded and redacts user names, home paths, devices,
addresses, hardware identifiers, boot identifiers, credentials, tokens, hashes,
and sensitive key/value fields before creating a mode-0600 archive.
