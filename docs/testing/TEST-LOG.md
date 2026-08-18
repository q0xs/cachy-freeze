# CachyFreeze test log

This file is the durable, English-only record of executed tests. Add results with
date, target, commit, command or scenario, result, and relevant non-sensitive notes.
Never record passwords, hashes, tokens, device UUIDs, or private user data.

## 2026-08-18 — ZIP-first graphical installation — `agent/make-zip-graphical-install-primary`

- CHANGED — README and installation documentation now make GitHub **Code →
  Download ZIP**, full extraction, and `cachyfreeze-setup.desktop` the primary
  end-user path; no terminal command is required.
- FIXED — reviewed GTK 2 symlink semantics are restored in the isolated AUR
  build tree when GitHub ZIP materializes the link as a regular target-text
  file, making application installation consistent between ZIP and Git trees.
- PASS — Ruff check/format, 68/68 Python tests, repository-wide error-level
  ShellCheck, static/desktop contracts including the ZIP link and executable
  graphical launcher, Qt offscreen UI smoke, isolated GRUB generation, and
  `git diff --check`.
- PASS — downloaded the pushed GitHub branch ZIP through HTTPS, extracted it,
  verified the graphical launcher retained executable mode, and reran all 68
  Python tests plus the static gate from the extracted archive. The static gate
  also exercised restoration of GitHub ZIP's materialized GTK 2 symlink.
- NOT RUN — physical reinstall, boot-stack integration, reboot, and destructive
  recovery tests; the target already has a verified live installation.

## 2026-08-18 — ready-user application preflight — `agent/guard-ready-user-applications`

- FIXED — **Create ready user** now verifies the complete managed-application
  status before displaying or collecting values in the account dialog. Missing
  or unhealthy requirements are listed and the operator is redirected to the
  Updates page instead of creating and rolling back a partial account.
- FIXED — the public `install.sh` entry now uses `sudo` in a terminal and the
  graphical PolicyKit agent when launched from a desktop file manager. This
  addresses the observed no-terminal `sudo` failure from a complete checkout.
- PASS — the existing physical standard account has a Wine prefix, non-empty
  registry, official MicroSIP 3.22.12 executable matching the recorded
  executable checksum, correct ownership, seven desktop shortcuts, and a
  template copy. Its production launcher remained healthy until the 15-second
  isolated X display timeout.
- PASS — Ruff check and format, 68/68 Python unit/GUI/helper/boundary tests,
  error-level ShellCheck/static validation, Qt offscreen UI smoke, isolated GRUB
  generation, and `git diff --check`.
- PASS — downloaded the pushed GitHub branch archive through HTTPS, extracted
  it into a temporary directory, verified executable installer/helper modes,
  and reran all 68 Python tests plus the static gate from the extracted archive.
- NOT RUN — new privileged user creation, boot-stack integration, physical
  reboot, and recovery tests; no disposable target was needed for these entry
  point and GUI changes.

## 2026-08-18 — clean physical reinstall and exhaustive live validation — final working tree

- PASS — removed the previous physical installation, managed snapshots, state
  subvolume, boot hook, services, policies, and application files; rebuilt the
  standard initramfs and GRUB configuration, then verified zero managed
  subvolumes or boot-hook remnants before reinstalling from a fresh GitHub clone.
- PASS — temporary initramfs installation test built and inspected images for
  both installed kernels before the clean physical install.
- PASS — application installation and a second idempotency run installed and
  verified Google Chrome 151.0.7922.137, Slack 4.51.180, Wine 11.15,
  LibreOffice 26.2.5, Zoiper 5.6.13, AnyDesk 8.0.4, Xvfb, unzip, rsync,
  runuser, the exact managed Chrome policy, and MicroSIP 3.22.12 with archive
  and executable checksums. The AnyDesk service is enabled, active, and now a
  required application-status item.
- PASS — live temporary standard-user provisioning: exact display name, normal
  home and shell, standard-only initial group, seven validated desktop entries,
  KDE and MIME defaults, Chrome policy, Wine prefix, exact MicroSIP executable,
  ownership, permissions, and byte/metadata-identical reset template.
- PASS — live user operations: password change through stdin, lock/unlock,
  automatic-login enable/disable, administrator mutation rejection,
  unprivileged-backend rejection, duplicate-create rejection, FROZEN home reset,
  supplemental-group reporting, backed-up deletion, UID/GID/password/group
  preserving restore, duplicate-restore rejection, and immediate second delete
  with a distinct collision-resistant backup ID. All synthetic accounts,
  groups, backups, homes, and templates were removed afterward.
- PASS — every settings field changed together and restored exactly; minimum
  numeric boundaries, both locale/theme choices, disabled/enabled update paths,
  and automatic-snapshot created/interval-suppressed paths passed live.
- PASS — physical snapshots passed list, metadata verification, full Btrfs-send
  stream hashing, deletion, retention cleanup, and path comparison. A real
  15.8 GB stream passed export permissions, manifest/checksum validation,
  import, and imported-snapshot verification; all export/test artifacts were
  removed afterward.
- FIXED — `btrfs subvolume find-new` returned zero paths between independent
  read-only snapshots despite a verified root-path change. Comparison now uses
  a no-data incremental Btrfs send decoded through `btrfs receive --dump`, and
  the same physical snapshot pair reports the changed path correctly.
- FIXED — the application installer enabled but did not start AnyDesk, while
  status checked only for its executable. Installation now starts and verifies
  the service; status requires the live daemon.
- FIXED — the privileged-user integration cleanup suppressed a failed deletion
  and could leave its synthetic account. Cleanup now terminates its session,
  force-removes only the validated test account, fails if it remains, and left
  zero accounts in the retest.
- FIXED — root CLI execution could write root-owned bytecode into the source
  clone. The CLI now disables bytecode writes, and the live deployer atomically
  synchronizes the complete deployment tree plus launchers and policy files.
- PASS — final quality gate: Ruff check/format, 61/61 unit/GUI/helper/boundary
  tests, static/desktop/XML/JSON checks, Qt offscreen UI, GRUB generation,
  Python compilation, diff check, and warning-level ShellCheck across all 33
  first-party Bash files. Vendored AUR files remained byte-for-byte upstream.
- PASS — privileged loop integrations: early-boot Active recreation and
  power-loss recovery, automatic failed-Golden rollback, 25-snapshot stress,
  retention, compare, export/import, rollback, and transaction recovery.
- PASS — final physical state: source and installed trees match, only the
  administrator account remains, application status reports all 13 items ready,
  Btrfs health is clean with zero device errors, GRUB authentication is hashed,
  both initramfs images contain the reset program, two clean Golden-history
  snapshots remain, no transaction is pending, and the next boot is FROZEN.
- NOT RUN — a physical reboot and post-login visual session check. Rebooting the
  user's active workstation was intentionally not performed without a separate
  explicit confirmation; the destructive early-boot paths were exercised in
  loop-backed integrations instead.

## 2026-08-18 — user lifecycle and application readiness hardening — working tree based on `8866a9b`

- PASS — 59/59 Python unit, GUI contract, helper allow-list, boundary, and
  malformed-input tests; Ruff check and format check.
- PASS — temporary privileged user lifecycle: create, native group inspection,
  lock/unlock, automatic login, backed-up delete, UID/GID/group-preserving
  restore, FROZEN home reset, and unprivileged-backend rejection.
- PASS — loop-backed Btrfs engine integration with 25-snapshot stress,
  retention, compare, export/import, rollback, FROZEN/THAWED scheduling, and
  interrupted transaction recovery.
- PASS — loop-backed early-boot reset, repeated Active recreation, two
  power-loss recovery points, and automatic failed-Golden rollback.
- PASS — reviewed AUR sources and checksums for Google Chrome 151.0.7922.137,
  Slack 4.51.180, GTK 2.24.33, Zoiper 5.6.13, and AnyDesk 8.0.4; every generated
  `.SRCINFO` exactly matches its vendored recipe.
- PASS — physical target read-only preflight and health inspection: THAWED `@`,
  UEFI/Btrfs layout supported, no pending transaction, all five existing
  snapshots healthy, and zero reported Btrfs device errors.
- FIXED — the privileged user integration fixture attempted to run an ELF
  executable through Bash. It now uses a real temporary provisioner and passes.
- FIXED — administrator protection, group visibility and restore collision
  checks, in-memory automatic-login sequencing, exact helper arity, full
  application prerequisites, Chrome policy equality, and MicroSIP executable
  checksum verification.
- FIXED — new user-backup IDs include collision-resistant entropy while restore
  remains compatible with the earlier timestamp-only backup IDs.
- FIXED — all AUR inputs are now reviewed and vendored; the installer no longer
  clones unreviewed AUR HEAD recipes when a package directory is absent.
- FOUND — the pre-existing physical installation has none of the managed
  employee applications installed and cannot yet create an application-ready
  standard account.
- NOT RUN — clean physical reinstall, managed application installation, live
  application-ready user provisioning, and reboot validation are the next
  phase of this audit.

## 2026-08-15 — visible fixed GRUB username — local working tree after `b690f59`

- PASS — Setup displays the selectable fixed GRUB maintenance username
  `cachyadmin` beside the password fields.
- PASS — installer output, README, installation guide, and recovery guide agree
  that `cachyadmin` is a GRUB-only credential, not a Linux account.
- PASS — 42/42 Python tests, Ruff check and format check, Bash/static and
  ShellCheck, Qt offscreen smoke, isolated GRUB generation, and `git diff --check`.
- NOT RUN — live GRUB configuration, physical boot-stack mutation, and reboot.

## 2026-08-15 — final repository consistency audit — local working tree after `c5a7549`

- PASS — local `main` matched GitHub `origin/main` before the audit.
- PASS — 42/42 Python unit and GUI contract tests; Ruff check and format check.
- PASS — repository-wide ShellCheck, Bash/static, desktop, XML/JSON, and
  English-only first-party user-facing text checks.
- PASS — README and installation guide expose only the complete Git clone path;
  stale raw-script and ZIP installation references are absent.
- PASS — Qt offscreen seven-page smoke test, isolated GRUB generation test,
  Python bytecode compilation, and `git diff --check`.
- FIXED — replaced the stale partial-install command in `docs/installation.md`,
  removed the desktop category warning, and translated legacy installer/service
  messages to English.
- NOT RUN — privileged integration tests, physical boot-stack mutation, live
  installation, and reboot.

## 2026-08-15 — application branding and full-clone installer — local working tree after `18b7d86`

- PASS — generated 512×512 RGBA logo has a transparent background and is wired
  to the Qt application, desktop entries, full installer, and live-app deployer.
- PASS — README and static contracts expose only the complete Git repository
  clone installation path; partial raw-script and ZIP instructions are absent.
- PASS — Ruff check and format check; 25 Python files checked.
- PASS — 42/42 Python unit and GUI contract tests.
- PASS — repository-wide ShellCheck error-level scan and Bash/static contracts.
- PASS — Qt offscreen seven-page smoke test, isolated GRUB generation test,
  Python bytecode compilation, and `git diff --check`.
- NOT RUN — live icon deployment, physical boot-stack mutation, and reboot.

## 2026-08-15 — installer, README and CI refresh — local working tree after `b0a391c`

- PASS — Ruff 0.16.3 check and format check; 25 Python files checked.
- PASS — 42/42 Python unit and GUI contract tests.
- PASS — full ShellCheck 0.11.0 error-level scan of every repository Bash script.
- PASS — Bash/static, desktop, XML/JSON, installer-link and complete-repository
  download contracts.
- PASS — Qt offscreen seven-page smoke test with the refreshed English UI.
- PASS — isolated GRUB generation and syntax test; no installed GRUB file was changed.
- PASS — Python bytecode compilation and `git diff --check`.
- NOT RUN — privileged temporary-user/Btrfs integrations, live package installation,
  Golden publication, GRUB/initramfs writes, and reboot. This validation pass did
  not mutate the physical boot stack and did not restart the workstation.

## 2026-08-15 — ready-user and UI update — local working tree after `3466a8e`

- PASS — 42/42 Python unit and GUI contract tests.
- PASS — Bash syntax, desktop/XML/JSON/static contract gate; ShellCheck was not
  installed, so the gate reported its documented syntax-only fallback.
- PASS — Qt offscreen seven-page smoke test with the refreshed English UI.
- PASS — isolated GRUB generation and syntax test; no installed GRUB file was changed.
- PASS — Python bytecode compilation and `git diff --check`.
- NOT RUN — Ruff; Ruff is not installed on the target.
- NOT RUN — privileged temporary-user integration, application installation,
  Golden publication, GRUB/initramfs writes, and reboot. The target has no
  non-interactive privileged channel, and boot-stack mutation was outside this
  non-reboot test pass.

## 2026-08-07 — physical CachyOS pilot — commit `845a7eb`

Historical baseline before the independent-workflow update:

- PASS — Ruff check and format check.
- PASS — 36/36 Python unit tests.
- PASS — Bash/static/ShellCheck gate.
- PASS — Qt offscreen seven-page smoke test.
- PASS — installed helper matched the repository helper.
- PASS — live Management Center opened in Plasma and displayed FROZEN, Golden
  and Active verified, no pending transaction, no warning.
- PASS — boot-health oneshot exited successfully; boot-attempt count was zero.
- PASS — no CachyFreeze application error was found in the inspected journal.
- NOT RUN — privileged GUI mutations, reboot, destructive Btrfs/GRUB tests.

## 2026-08-07 — independent install/freeze workflow — commit `91116a0`

- PASS — Ruff check and format check; 25 Python files formatted.
- PASS — 37/37 Python unit tests, including independent install/freeze and first-freeze GRUB protection contracts.
- PASS — Bash/static/ShellCheck, desktop, XML/JSON, Python compile, and systemd gate.
- PASS — Qt offscreen seven-page smoke and launcher event-loop test.
- PASS — GRUB generation and syntax test.
- PASS — temporary Btrfs reset/recovery integration test.
- PASS — engine integration including 25-snapshot stress.
- PASS — temporary user lifecycle and privilege integration test.
- NOT RUN — temporary initramfs build. Its safety guard found installed target files
  and refused to overwrite `/usr/lib/cachy-freeze/cachy-freeze-reset`.
- NOT RUN — live install, Golden publication, reboot, and destructive physical tests.
