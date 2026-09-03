# CachyFreeze test log

This file is the durable, English-only record of executed tests. Add results with
date, target, commit, command or scenario, result, and relevant non-sensitive notes.
Never record passwords, hashes, tokens, device UUIDs, or private user data.

## 2026-09-03 — Ansible syntax and Semaphore UI integration — local working tree

- FIXED — `ansible/roles/cachy_freeze/tasks/thaw.yml` now runs
  `cachy-freeze boot-success` immediately after the authorized reboot reconnects
  and before reading status, so Ansible consumes the one-time
  `cachy_remote_auth` flag deterministically instead of racing
  `cachy-freeze-boot-health.service`.
- UPDATED — provisioning copies only the runtime/install payload allowlist to
  `/opt/cachy-freeze` and sets `cachy_freeze_payload_staged`; the install role
  skips its own transfer when the provision play already staged the payload.
- ADDED — `ansible/test-syntax.sh`, GitHub Actions Ansible syntax checking,
  `ansible/docker-compose.semaphore.yml`, and the Turkish Semaphore operating
  guide.
- ADDED — GitHub Actions validates `docker-compose.semaphore.yml` with
  `docker compose config` and dummy CI-only environment values.
- PASS — `PATH=/tmp/cachy-freeze-ansible-venv/bin:$PATH bash
  ansible/test-syntax.sh`: all five playbooks passed `ansible-playbook
  --syntax-check`. Ansible reported the expected warning that the sample
  inventory contains only commented hosts.
- PASS — `PYTHONPATH=src:app QT_QPA_PLATFORM=offscreen python -m unittest
  discover -s tests -v`: 72 tests passed, including the new thaw, payload, and
  Semaphore contracts.
- PASS — `ruff check .` and `ruff format --check src app/cachy_freeze_gui
  tests`.
- PASS — `SHELLCHECK_OPTS=--severity=error bash deepfreeze/tests/static.sh`,
  `shellcheck ansible/setup-controller.sh ansible/test-syntax.sh`, and
  `bash workstation/tests/static.sh`.
- PASS — `QT_QPA_PLATFORM=offscreen bash deepfreeze/tests/ui-smoke.sh`,
  `bash deepfreeze/tests/grub-generation.sh`, `git diff --check`, and a YAML
  parse of `ansible/docker-compose.semaphore.yml`.
- NOT RUN — `docker compose -f ansible/docker-compose.semaphore.yml config` or
  `up`; Docker is not installed on this local workstation. The controller setup
  script installs Docker/Compose only when invoked with `--with-semaphore`.
- NOT RUN — root-only Btrfs loopback integration, QEMU/OVMF boot acceptance,
  physical install/reboot/FROZEN reset, or live Semaphore task execution.

## 2026-09-03 — Ansible fleet management and authorized remote thaw — local working tree

- ADDED — the monorepo `ansible/` control plane with controller bootstrap,
  fleet-tuned `ansible.cfg`, lab/production inventory groups, LocalAdm sudo
  bootstrap, Workstation provisioning/check roles, CachyFreeze status/thaw/
  freeze/install/verify roles, and provision/maintenance/status/thaw/freeze
  playbooks.
- ADDED — `cachy-freeze thaw --authorized` with `--remote` as an alias. The
  command writes a one-time `cachy_remote_auth=1` GRUB environment flag while
  scheduling THAWED and reports `remote_authorized_boot` in JSON.
- ADDED — THAWED boot verification consumes remote authorization by writing
  `cachy_remote_auth=0`. Recovery scheduling and normal freeze/thaw writes also
  reset the flag to fail closed.
- UPDATED — the managed GRUB entry permits THAWED boot without interactive
  `authenticate` only when `cachy_remote_auth=1`; otherwise THAWED still
  requires `cachyadmin` authentication.
- UPDATED — Workstation and graphical helper username validation accepts
  corporate uppercase usernames such as `WRW21166`.
- UPDATED — `VERSION`, `pyproject.toml`, and package metadata are prepared as
  `1.0.0rc9`; `workstation/VERSION` is prepared as `1.0.2`.
- PASS — `ruff check .` and `ruff format --check src app/cachy_freeze_gui
  tests`.
- PASS — `PYTHONPATH=src:app QT_QPA_PLATFORM=offscreen python -m unittest
  discover -s tests -v`: 69 tests passed, including the new Ansible contract,
  CLI authorized-thaw, remote GRUB flag, and boot-time consumption coverage.
- PASS — `SHELLCHECK_OPTS=--severity=error bash deepfreeze/tests/static.sh`,
  including ShellCheck for `ansible/setup-controller.sh`.
- PASS — `bash workstation/tests/static.sh`.
- PASS — `QT_QPA_PLATFORM=offscreen bash deepfreeze/tests/ui-smoke.sh` and
  `bash deepfreeze/tests/grub-generation.sh`.
- PASS — two consecutive installer builds produced identical
  `dist/CachyFreeze-Installer-1.0.0rc9.run` and
  `dist/CachyWorkstation-Setup-1.0.2.run` outputs; both checksum sidecars
  verified with `sha256sum --check`.
- PASS — payload inventory checks confirmed the rc9 installer embeds the
  authorized-thaw CLI/engine/GRUB changes and the Workstation 1.0.2 payload.
- NOT RUN — `ansible-playbook --syntax-check` and `ansible-lint`; this local
  host does not have Ansible installed. The repository contract tests validate
  FQCN module use, file layout, batch settings, JSON parsing, and fail-safe
  maintenance behavior without external Ansible tooling.
- NOT RUN — local QEMU/OVMF GRUB boot acceptance; this host is missing
  `expect`. The GitHub workflow installs the required VM tools before running
  the acceptance test.
- NOT RUN — destructive physical install/reboot/FROZEN reset and real fleet
  maintenance against lab or production hosts. These require an approved
  disposable VM, pilot machine, or lab inventory.

## 2026-09-03 — GitHub release audit and GRUB VM retry hardening — local working tree

- AUDITED — GitHub `main` and `v1.0.0rc8` now both show successful
  `Statik kontroller` workflow runs after rerunning the transient tag failure.
  The failed first tag attempt timed out while waiting for the GRUB password
  prompt in the QEMU/OVMF serial console; the rerun passed on the same commit.
- UPDATED — the GRUB UEFI VM test retry filter now treats timeout while waiting
  for the password prompt as the same transient serial transport symptom as the
  already-retried prompt/echo cases.
- UPDATED — `README.md` names the `v1.0.0rc8` release candidate directly
  instead of referring generically to the latest release, because GitHub's
  latest-release endpoint does not resolve while all public releases are
  pre-releases.
- PASS — `bash -n deepfreeze/tests/boot-acceptance-vm.sh` and
  `shellcheck deepfreeze/tests/boot-acceptance-vm.sh`.
- PASS — `bash deepfreeze/tests/static.sh`.
- NOT RUN — local `bash deepfreeze/tests/boot-acceptance-vm.sh`; this host is
  missing `expect`. The GitHub workflow installs `expect`, OVMF, GRUB EFI
  tools, and QEMU before running this acceptance test.

## 2026-09-03 — CachyFreeze v1.0.0rc8 release candidate — local working tree

- UPDATED — release metadata is synchronized across `VERSION`,
  `pyproject.toml`, and the Python package version as `1.0.0rc8`. Public
  download instructions in `README.md`, `KURULUM-TR.md`, and
  `docs/installation.md` point to the `v1.0.0rc8` GitHub release assets.
- UPDATED — the standalone Workstation payload version is `1.0.1`; CLI-only
  download instructions in `docs/workstation-provisioning.md` point to the
  Workstation asset attached to the `v1.0.0rc8` release.
- FIXED — the first Python unit-test run failed because `VERSION` had been
  bumped to `1.0.0rc8` while `src/cachy_freeze/__init__.py` still reported
  `1.0.0rc7`. The package version was corrected before release.
- PASS — `ruff check .`.
- PASS — `PYTHONPATH=src:app QT_QPA_PLATFORM=offscreen python -m unittest
  discover -s tests -v`: 59 tests passed after the version fix.
- PASS — `bash workstation/tests/static.sh`, `bash deepfreeze/tests/static.sh`,
  `bash deepfreeze/tests/ui-smoke.sh`, and
  `bash deepfreeze/tests/grub-generation.sh`.
- PASS — two consecutive `bash packaging/build-installer.sh` runs produced
  identical `dist/CachyFreeze-Installer-1.0.0rc8.run` files; the checksum
  sidecar verified with `sha256sum --check`.
- PASS — two consecutive `bash packaging/build-workstation-installer.sh` runs
  produced identical `dist/CachyWorkstation-Setup-1.0.1.run` files; the
  checksum sidecar verified with `sha256sum --check`.
- PASS — the embedded payload inventory for both `.run` files includes the
  updated Workstation login and health modules.
- NOT RUN — destructive physical installation, real GRUB/initramfs mutation,
  reboot, real 60/120-minute idle duration, and pilot-machine FROZEN reset.
  These remain approved-target tests, not local host tests.

## 2026-09-03 — KDE Workstation freeze gate, login preselection, and status display — local working tree

- FIXED — the graphical installer now presents Workstation preparation before
  the GRUB maintenance password and **INSTALL CACHYFREEZE** action. First
  CachyFreeze installation remains disabled until **CHECK WORKSTATION** passes
  for the selected employee username, so the initial Golden baseline cannot be
  created before application and workstation health validation.
- ADDED — Workstation provisioning configures the active KDE display manager to
  preselect the employee account without enabling automatic login. Plasma Login
  Manager writes the `[Greeter] PreselectedUser` and `PreselectedSession`
  settings in `/etc/plasmalogin.conf`; SDDM writes an owned local config
  drop-in and the state file's `[Last] User` and `Session` values.
- ADDED — Workstation health checks now verify the login-screen preselection
  and disabled autologin state. The graphical installer shows the detailed
  Workstation PASS/FAIL output in a visible report area.
- FIXED — the installed GUI mode badge now displays a known cached or kernel
  command-line mode as **FROZEN** or **THAWED** even before privileged status
  verification finishes. Mode-changing buttons remain disabled until verified
  state is available.
- VERIFIED — the idle policy remains 60 minutes to `loginctl lock-session` and
  120 minutes total idle to `systemctl --no-block poweroff`. The root supervisor
  still uses a sleep inhibitor so suspend cannot pause the 120-minute cleanup
  path; no suspend command is issued by the policy.
- PASS — `ruff check .`.
- PASS — `PYTHONPATH=src:app QT_QPA_PLATFORM=offscreen python -m unittest
  discover -s tests -v`: 59 tests passed, including new GUI order, freeze-gate,
  Workstation report, and unverified-mode display coverage.
- PASS — `bash workstation/tests/static.sh`: Bash syntax, ShellCheck, Ruff,
  idle-supervisor tests, desktop/systemd validation, KF6 KIdleTime agent build,
  path-safety checks, and vendored PKGBUILD/`.SRCINFO` checks passed.
- PASS — `bash deepfreeze/tests/static.sh`,
  `bash deepfreeze/tests/ui-smoke.sh`, and
  `bash deepfreeze/tests/grub-generation.sh`.
- PASS — `bash packaging/build-installer.sh` produced
  `dist/CachyFreeze-Installer-1.0.0rc7.run`; the generated checksum sidecar
  verified with `sha256sum --check`, and the embedded payload contains
  `workstation/lib/login.sh`.
- PASS — `bash packaging/build-workstation-installer.sh` produced
  `dist/CachyWorkstation-Setup-1.0.0.run`; its generated checksum sidecar
  verified with `sha256sum --check`.
- NOT RUN — root-only initramfs, Btrfs loopback, full QEMU/OVMF boot
  acceptance, physical Workstation provisioning, real 60/120-minute idle
  duration, CachyFreeze installation, GRUB/initramfs mutation, reboot, and
  FROZEN runtime reset. These remain disposable VM or approved pilot-machine
  tests.

## 2026-08-29 — portable CachyWorkstation provisioner — local working tree

- ADDED — a separate administrator CLI payload provisions an already-created
  non-administrator employee without changing the normal CachyFreeze GUI,
  installer, Btrfs engine, GRUB lifecycle, or FROZEN/THAWED product contract.
  Install/repair is fail-closed outside persistent THAWED `@`; FREEZE remains a
  later manual action after application tests and a passing health check.
- PASS — `bash workstation/tests/static.sh`: ShellCheck, Bash syntax, Ruff
  check/format, nine idle-supervisor unit tests, desktop-file and systemd unit
  validation, the managed-user symlink/traversal guard, KF6 KIdleTime C++
  compilation with release LTO, every vendored PKGBUILD/`.SRCINFO` pair, and
  the AUR revision manifest passed.
- PASS — current reviewed Google Chrome and AnyDesk recipes downloaded their
  official archives and produced installable packages as an unprivileged
  isolated build account. The official Zoiper endpoint was downloaded twice;
  both responses were byte-identical but differed from the then-current AUR
  checksum. The replacement archive structure and x86-64 executable were
  inspected, the downstream change was documented with a package-release bump,
  and the reviewed recipe produced an installable package. The vendored GTK 2
  fallback Git source and all patches passed `makepkg --verifysource`; the
  preferred signed CachyOS repository currently provides the same GTK 2
  package version.
- PASS — the official MicroSIP portable archive passed the pinned archive and
  executable checksums, archive-size/type/path checks, and 32-bit Windows GUI
  executable inspection. A one-byte-modified copy was rejected. This real-file
  test exposed and fixed a portable `file(1)` architecture-label difference
  before release.
- PASS — a controlled event-only test in the physical KDE Plasma 6 Wayland
  session emitted READY, LOCK, and POWER_OFF at short thresholds; simulated
  input emitted RESUMED and began a new idle interval. The test agent emitted
  text tokens only and was never connected to lock or shutdown commands. A
  separate live supervisor test found the active local Wayland session and its
  user-manager environment after a standard underscore-prefixed environment
  variable parser regression was fixed.
- PASS — two `SOURCE_DATE_EPOCH=0` workstation payload builds were identical
  and the generated checksum sidecar passed. Root extraction verified the
  embedded manifests and reached `--help`. A complete `--check` against the
  existing administrator account correctly failed the no-admin check and all
  absent managed components while still printing the complete summary. A normal
  install invocation on the physical FROZEN `@active` root stopped before any
  package or provisioning step.
- PASS — GitHub API reports the repository license as Apache-2.0;
  `pyproject.toml` identifies Atilla Mert Akkaya as author and the repository
  `NOTICE` records
  the same copyright owner for CachyFreeze and CachyWorkstation Setup. The
  reproducible workstation artifact contains byte-identical copies of both
  `LICENSE` and `NOTICE`. README documents the two independent executables and
  the mandatory fresh-machine and already-installed deployment sequences.
- FIXED — the first GitHub workstation job exposed that the minimal Arch
  container omitted `/run/systemd`; unprivileged `systemd-analyze verify`
  could not create that system runtime directory. CI now creates the empty
  runtime tree during its privileged dependency step without weakening the
  unprivileged workstation build and test boundary.
- PASS — [GitHub Actions run
  33258122247](https://github.com/q0xs/cachy-freeze/actions/runs/33258122247)
  passed all three jobs: workstation static/unit and reproducible payload
  checks, CachyFreeze static/Python/Btrfs lifecycle checks, and the QEMU/OVMF
  UEFI FROZEN/protected-THAWED acceptance test.
- PUBLISHED — the independent `workstation-v1.0.0` prerelease contains the
  executable and checksum sidecar. Both assets were downloaded from GitHub;
  the sidecar verified and both downloaded files matched the locally tested
  release artifacts byte for byte. The prerelease note retains the required
  physical application-launch and full-duration idle-policy acceptance gate.
- PASS — every Bash block in the Turkish copy/paste deployment guide passed
  `bash -n`; its README link resolves to the tracked guide. The guide's four
  version-pinned GitHub asset URLs were downloaded without a repository clone
  or GitHub login, and both published checksum sidecars verified. No guide
  command that provisions, freezes, powers off, or reboots a machine was run.
  After the employee-account step was made explicit, all nine numbered steps
  remained sequential and the five documented desktop shortcuts matched the
  installer launcher map; the complete workstation static suite passed again.
- PASS — the unchanged CachyFreeze product passed Ruff check/format,
  ShellCheck/static contracts, Qt offscreen smoke, isolated GRUB generation,
  all 53 Python tests, and two reproducible graphical-installer builds with a
  valid checksum sidecar. The Python suite ran inside a temporary mount
  namespace with an empty test kernel-command-line view because the physical
  host's real FROZEN marker must not override its mocked THAWED fixtures.
- BLOCKED locally — the two disposable Btrfs loopback integrations stopped at
  `losetup` before creating a filesystem because this running FROZEN kernel has
  no usable matching loop driver/module. The temporary directories and the
  test-created device node were removed. The QEMU/OVMF test is also unavailable
  locally because QEMU and Expect are not installed; both remain CI targets.
- NOT RUN — live provisioning of an employee on this test PC, actual
  application installation/launch, a real 60/120-minute lock and poweroff,
  physical CachyFreeze mutation, FREEZE publication, or reboot. The portable
  provisioner is intended for other THAWED target PCs; no physical shutdown was
  connected to the short idle-agent test.

## 2026-08-24 — rc6 idempotent FROZEN reset and single-mode GRUB menu

- DIAGNOSED — privileged read-only inspection after the rc5 FROZEN failure
  found a valid read-only Golden with a usable init and matching installed and
  embedded reset payloads. The failed boot had recorded a completed Active
  reset, but `@active` was absent afterward. The reset oneshot was also observed
  being requested twice during an ordinary THAWED initramfs sequence.
- ROOT CAUSE — the reset service was `Type=oneshot` without
  `RemainAfterExit=yes`. After its first successful run it returned to the dead
  state and could be started again in the same initramfs boot. A repeated start
  could recursively delete the already-mounted switch-root target, producing
  `switch root target contains no usable init` even though Golden itself was
  complete.
- FIXED — rc6 keeps the successful oneshot active, makes the reset program
  idempotent by kernel boot ID, rejects deletion of any mounted Active, stages
  and validates the replacement before deleting the old runtime, validates a
  usable init in Golden and Active, and requires matching reset proof during
  real-root boot health. A failed reset schedules the next boot as protected
  THAWED when the canonical GRUB environment remains writable. Recursive
  runtime cleanup uses portable nested subvolume-ID deletion rather than the
  newer `btrfs subvolume delete --recursive` option.
- CHANGED — the normal GRUB menu is visible for five seconds and contains only
  the scheduled FROZEN or THAWED entry. FROZEN remains passwordless and THAWED
  keeps the fail-closed `cachyadmin` authentication boundary. Unrelated vendor,
  firmware, snapshot, and custom entries remain generated inside an explicit
  administrator recovery gate.
- PASS — all 53 Python tests, Ruff 0.12.4 check/format, ShellCheck 0.11.0
  error-level validation, repository static/Bash contracts, Qt offscreen smoke,
  and isolated GRUB generation passed.
- PASS — privileged disposable-loop tests proved that a duplicate same-boot
  reset is a no-op, a mounted Active is never deleted, a changed boot ID
  recursively discards runtime data and multi-level nested subvolumes (including
  whitespace in their paths), THAWED cleanup removes the same nested layout,
  failed reset selects protected THAWED recovery, repeated lifecycle operations
  retain no Active or Golden history, and NOCOW baseline content remains
  supported.
- PASS — a temporary mount namespace generated and syntax-checked the complete
  physical CachyOS GRUB configuration without installing it; every unrelated
  entry remained inside the recovery gate and the managed entry was the only
  normal entry. A separately generated temporary initramfs contained the rc6
  reset program, single-run service, required tools, configuration, and target
  dependency. Neither test wrote the physical boot configuration.
- PASS — two `SOURCE_DATE_EPOCH=0 bash packaging/build-installer.sh` builds
  produced an identical `CachyFreeze-Installer-1.0.0rc6.run`; its checksum,
  embedded manifest, version, executable GRUB generators, and removal of the
  obsolete rc5 generator path were verified.
- PARTIAL — GitHub Actions run `32736656987` for commit `3f14f8f` passed the
  complete QEMU/OVMF GRUB authentication job. Its static job reached the new
  loopback test and failed because Ubuntu's btrfs-progs lacks the newer
  `subvolume delete --recursive` option; no product test assertion failed before
  that portability error.
- PASS — GitHub Actions run `32738331172` for commit `a4c9fc9` passed both jobs:
  ShellCheck, Ruff, all 53 Python/Qt/static checks, isolated GRUB generation,
  both privileged disposable Btrfs lifecycle tests on Ubuntu, and QEMU/OVMF
  authentication acceptance for passwordless FROZEN plus protected THAWED.
- PARTIAL — the later documentation-only run `32738514227` again passed the
  complete static/Btrfs job, but its otherwise identical QEMU job denied the
  correct-password case after emulated serial input. Run `32738897079` again
  passed static/Btrfs and made the transport fault visible by echoing the
  truncated username `cachyadmi`; the harness correctly rejected that result.
- FIXED/PASS — the QEMU harness now sends serial characters more slowly and
  retries only an incompletely echoed username or an allowed-case denial, using
  fresh OVMF variables each time. A real authentication failure must still fail
  all three attempts, and the passwordless case never retries. GitHub Actions
  run `32739279334` for commit `5cdceeb` passed both jobs. Its first wrong-
  password attempt detected incomplete input; the clean retry supplied the full
  username and was denied, while the correct password was accepted and FROZEN
  remained passwordless.
- NOT RUN locally — the disposable QEMU/OVMF authentication test because QEMU
  and Expect are unavailable on this workstation; the same repository test
  passed in GitHub Actions as recorded above.
- NOT RUN — rc6 installation, GRUB/initramfs deployment, reboot, and complete
  FROZEN/THAWED lifecycle on the physical machine. This pass changed no physical
  subvolume or boot configuration; the user plans a clean-format acceptance
  test with the released installer.

## 2026-08-24 — direct managed GRUB default — physical diagnosis and rc5 tests

- DIAGNOSED — after the rc4 installer scheduled FROZEN, the physical machine
  rebooted through the first stock CachyOS entry and remained on persistent
  THAWED `@`. The durable GRUB environment still requested FROZEN, while the
  running kernel had no CachyFreeze mode marker. The managed entry, Golden
  kernel, microcode, initramfs, embedded reset service/configuration, and
  read-only Golden state all passed privileged read-only inspection.
- ROOT CAUSE — the installer used `GRUB_DEFAULT=saved` and depended indirectly
  on `saved_entry=cachyos-current`; that saved selection was not applied by the
  physical boot. rc5 sets the stable managed entry ID directly as GRUB's
  default. Unrelated recovery and firmware entries remain generated but the
  normal one-second menu is hidden; Esc exposes the preserved menu.
- PASS — all 45 Python tests, Ruff 0.12.4 check/format, repository static/Bash
  contracts, isolated GRUB generation, Qt offscreen smoke, privileged
  disposable-loop engine and recursive-reset integrations, and `git diff
  --check` passed. ShellCheck was unavailable locally and was not represented
  as locally executed.
- PASS — GitHub Actions run `32730407596` for commit `5eb4b73` passed both
  jobs: ShellCheck, Ruff, all Python/Qt/static checks, isolated GRUB generation,
  and disposable QEMU/OVMF authentication acceptance for passwordless FROZEN
  plus protected THAWED.
- PASS — two `SOURCE_DATE_EPOCH=0 bash packaging/build-installer.sh` builds
  produced an identical `CachyFreeze-Installer-1.0.0rc5.run`; its SHA-256
  sidecar verified successfully.
- NOT RUN — deployment of rc5 to the physical boot stack and the subsequent
  FROZEN reboot/reset proof. No physical GRUB/initramfs write, Golden
  publication, or reboot was performed by this verification pass.

## 2026-08-24 — NOCOW baseline-copy regression — physical diagnosis and disposable tests

- DIAGNOSED — the physical rc3 installation stopped during the `preparing`
  phase while copying the read-only `@log` capture. Standard data before that
  point copied completely, but two systemd journal files were absent from the
  candidate. The incomplete Golden was never activated, GRUB remained THAWED,
  and the transaction metadata and staging subvolumes were retained for
  controlled recovery.
- ROOT CAUSE — systemd journal files carry the Btrfs NOCOW attribute. The rc3
  engine forced `cp --reflink=always`, and Btrfs rejected a forced clone of
  those files. An isolated disposable loopback reproduced the failure and
  verified that a normal-copy fallback preserves the file contents.
- FIXED — rc4 uses same-filesystem reflinks where supported and falls back to a
  normal copy for NOCOW data. Candidate Btrfs stubs are replaced with a normal
  directory before copying. The engine integration test now creates NOCOW data,
  and the test invokes the checked-out source explicitly so a partial host
  installation cannot substitute an older installed engine.
- PASS — all 44 Python tests, Ruff check/format, repository static/Bash checks,
  Qt offscreen smoke, isolated GRUB generation, the NOCOW engine loopback test,
  and the recursive FROZEN-reset loopback test passed. ShellCheck remains
  unavailable locally and was not represented as executed.
- PASS — two `SOURCE_DATE_EPOCH=0 bash packaging/build-installer.sh` builds
  produced an identical `CachyFreeze-Installer-1.0.0rc4.run`; its SHA-256
  sidecar verified successfully.
- NOT RUN — physical rc4 transaction recovery, baseline publication, reboot,
  and FROZEN reset. The physical system remains THAWED pending the corrected
  installer retry.

## 2026-08-24 — stock CachyOS Btrfs layout support — local rc3 working tree

- PASS — `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:app python -m unittest
  discover -s tests -v`: all 44 backend, GUI, helper, installer, lifecycle,
  runner, and migration tests passed.
- PASS — Ruff 0.12.4 `check` and `format --check` passed for `src`, the GUI,
  and `tests`.
- PASS — `bash deepfreeze/tests/static.sh`,
  `QT_QPA_PLATFORM=offscreen bash deepfreeze/tests/ui-smoke.sh`, and `bash
  deepfreeze/tests/grub-generation.sh` passed. ShellCheck was unavailable, so
  the static script performed Bash syntax validation without representing
  ShellCheck as executed.
- PASS — the privileged, disposable-loopback `integration-engine.sh` and
  `integration-btrfs.sh` tests passed. The engine flattened supported nested
  data into Golden, excluded third-party Snapper history, removed its temporary
  capture, and recursively discarded a nested FROZEN runtime without retaining
  history. No host subvolume or host boot configuration was a test target.
- PASS — `deepfreeze/tests/build-initramfs.sh` generated and inspected temporary
  initramfs images for both installed kernels, then removed its temporary
  installed test inputs. It did not overwrite a host initramfs image.
- PASS — the non-mutating privileged preflight completed against the physical
  workstation's stock CachyOS layout. It verified THAWED `@`, UEFI/GRUB/Btrfs,
  the standard data mounts, the supported systemd nested subvolumes, and the
  excluded Snapper tree. The temporary top-level inspection mount and audit
  file were removed; no Golden, Active, GRUB, or persistent configuration was
  changed.
- PASS — two `SOURCE_DATE_EPOCH=0 bash packaging/build-installer.sh` builds
  produced an identical `CachyFreeze-Installer-1.0.0rc3.run`; its generated
  SHA-256 sidecar verified successfully.
- BLOCKED locally — `deepfreeze/tests/boot-acceptance-vm.sh`:
  `qemu-system-x86_64` is unavailable on the workstation.
- PASS — GitHub Actions run `32726332134` for commit `ff5d2e2` passed both
  jobs. The static job executed ShellCheck, Ruff, all Python tests, and isolated
  GRUB generation. The disposable QEMU/OVMF job denied an incorrect THAWED
  password, accepted the correct THAWED password, and booted the FROZEN entry
  without authentication.
- NOT RUN — a full installer, reboot, FROZEN reset, THAWED persistence, and
  re-FREEZE lifecycle in a disposable CachyOS VM. No live installation,
  baseline publication, host GRUB write, host root replacement, or reboot was
  performed.

## 2026-08-24 — two-mode simplification — local unprivileged checkout

- PASS — `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:app python -m unittest
  discover -s tests -v`: 39 tests passed; 6 PyQt6-dependent GUI tests were
  skipped because PyQt6 is not installed in the development environment.
- PASS — `SHELLCHECK_OPTS=--severity=error bash deepfreeze/tests/static.sh`:
  repository Bash syntax, Python compilation contracts, desktop entries,
  PolicyKit XML, removed-feature contracts, and systemd inputs passed. ShellCheck
  itself was unavailable and was not represented as executed.
- PASS — `bash deepfreeze/tests/grub-generation.sh`: the generated managed GRUB
  entry passed its content and `grub-script-check` validation. FROZEN boot files
  are loaded from read-only Golden while the selected root remains disposable
  Active.
- PASS — `bash packaging/build-installer.sh`: generated the native single-file
  `.run` installer and matching SHA-256 sidecar. Two consecutive builds with the
  same inputs produced identical artifact checksums. Extraction verified the
  embedded per-file manifest, regular-file-only payload, executable helper mode,
  and absence of tests, documentation, vendor trees, bytecode, and legacy user
  assets from the runtime payload.
- BLOCKED — `QT_QPA_PLATFORM=offscreen bash deepfreeze/tests/ui-smoke.sh`:
  PyQt6 is not installed. The six equivalent unittest cases were skipped for the
  same explicit reason.
- BLOCKED — `bash deepfreeze/tests/integration-btrfs.sh` and `bash
  deepfreeze/tests/integration-engine.sh`: the current account is unprivileged.
  Both scripts stopped at their initial root guard; no loop device, Btrfs
  filesystem, host subvolume, or host boot state was changed.
- BLOCKED — `bash deepfreeze/tests/build-initramfs.sh`: the script stopped at its
  initial root guard; no installed file or initramfs image was changed.
- BLOCKED — `bash deepfreeze/tests/boot-acceptance-vm.sh`: the disposable GRUB
  guest prerequisites are unavailable (`expect` was the first missing command).
- NOT RUN — Ruff lint/format and ShellCheck; the executables are unavailable.
- NOT RUN — full disposable CachyOS install/FROZEN/THAWED/reboot lifecycle and
  physical-device validation. No host installation, GRUB modification, root
  replacement, subvolume deletion, or reboot was performed.

## 2026-08-21 — password-required login selection and reliable first FROZEN finalization — physical workstation

- RELEASE — these fixes are prepared as `v1.0.0rc2`; release metadata is
  synchronized across `VERSION`, `pyproject.toml`, the Python package, README,
  and static contracts.
- DIAGNOSED — local extracted source contained 14 functional changes beyond GitHub
  `main` at `c6df9f1`; the relevant local finalization and mode-detection fixes were
  preserved instead of replacing the tree with the older remote files.
- FIXED — the former automatic-login option now only preselects the managed account
  in Plasma Login Manager/SDDM state. The owned automatic-login drop-ins are disabled,
  `Relogin` is false, and PAM password authentication remains mandatory.
- FIXED — finalization disables legacy automatic login before logout, recovers an
  interrupted durable request when its service is no longer active, and can be retried
  safely instead of remaining permanently stuck in `waiting-for-logout`.
- FIXED — logout finalization restores managed homes from their existing clean templates
  before Golden publication. Files created by a normal or accidental user session are
  deleted instead of being captured into the FROZEN baseline.
- PASS — 113/113 Python unit and GUI tests, repository static/Bash contracts, Qt
  offscreen smoke, isolated GRUB generation and syntax, Python compilation, live
  rollback-capable application deployment, password-required greeter state, disabled
  automatic-login configuration, enabled reset/restriction/boot-health services, both
  installed initramfs reset payloads, and live Btrfs/snapshot health were verified.
- NOT RUN — Ruff and ShellCheck are unavailable on this workstation. No Golden/Active
  publication or reboot was performed; the next physical FROZEN boot and post-login
  reset proof remain pending explicit reboot execution.

## 2026-08-21 — fresh CachyOS guided setup and fail-closed automatic reboot — physical workstation

- FIXED — the initial pre-GRUB boot now derives THAWED/FROZEN from the mounted
  managed subvolume when kernel mode markers are not available; explicit kernel
  markers still take precedence.
- FIXED — localized question dialogs now use explicit Yes/No buttons with No as
  the safe default. Setup user creation proceeds through application readiness
  without a second silently-cancelled confirmation.
- FIXED — Setup controls enforce the five-step order, and Finish runs a final
  Btrfs/snapshot readiness check before requesting logout-aware publication.
- CHANGED — successful logout finalization now records the reboot through the
  backend and restarts automatically. A failed finalization never reaches the
  `ExecStartPost` reboot and remains fail-closed at the login screen.
- PASS — live preflight, installation, all 13 managed application checks,
  standard non-administrator user creation, home ownership, user-template and
  automatic-login configuration, GRUB authentication/hash/configuration, and
  zero failed systemd units were verified without recording identities or
  secrets.
- PASS — 109/109 Python unit and GUI tests, repository static/systemd contracts,
  Qt offscreen UI smoke, isolated GRUB generation and syntax checks, and the
  rollback-capable live application deployment completed successfully.
- INFO — the live deployment backup is managed under
  `/var/backups/cachy-freeze/app/`; no reboot was initiated by deployment.
- NOT RUN — the final physical FROZEN reboot, post-boot Golden reset proof, and
  boot-validation completion remain pending. Ruff and ShellCheck are unavailable
  on this workstation.

## 2026-08-21 — GUI reboot, mode guard, audit failure visibility, and simplified setup — local extracted source

- FIXED — the PolicyKit reboot helper now uses the JSON backend contract. The
  backend queues `systemctl reboot --no-block`, writes a durable reboot audit
  event, and returns a valid response before the desktop session is stopped.
- FIXED — privileged command failures now create bounded, non-secret audit
  events. The GUI reloads Audit Logs after a non-log operation fails.
- FIXED — FROZEN and unknown modes disable THAWED-only writes in the GUI and
  explain that the operator must schedule THAWED and reboot before user,
  application, Golden-publication, or mutable snapshot work can continue.
- CHANGED — Create user now performs the application readiness check itself.
  When preparation is needed, one confirmation starts it and the verified
  result returns directly to the normal user form; boot mode remains unchanged.
- CHANGED — Setup is now one vertical five-step workflow: preflight, install,
  optional user creation, GRUB maintenance password, then Finish and enable
  FROZEN. The old recovery/disposable checkboxes were removed; installation
  keeps one plain-language safety confirmation, while the GRUB password and
  final FROZEN publication are separate operations.
- PASS — 103/103 Python unit and GUI tests, repository static contracts, Qt
  offscreen UI smoke, isolated GRUB generation/syntax checks, and Python
  compilation completed successfully.
- NOT RUN — Ruff and ShellCheck are unavailable on this workstation. No live
  deployment, initramfs/GRUB write, user mutation, or reboot was performed by
  this validation pass.

## 2026-08-20 — local v1 hardening and UEFI acceptance — working tree based on `dc8a675`

- FIXED — Golden/FROZEN finalization now waits for normal managed-session logout,
  publishes and schedules FROZEN under one operation lock, fails closed on
  timeout, and validates the first real FROZEN boot before clearing boot-attempt
  state.
- FIXED — persistent state has an application version and schema migration;
  local deployment stages and compile-checks candidates, creates a bounded
  managed-path backup, verifies migration and installed files, and rolls back
  only its explicit allow-list on failure.
- FIXED — Plasma Login Manager automatic login now uses the owned
  `90-cachy-freeze-autologin.conf` drop-in. The migration preserves unrelated
  administrator configuration and compatible SDDM systems keep their owned
  drop-in path.
- ADDED — a redacted diagnostic ZIP, English/Turkish live GUI translation, and
  an installed power service implementing one hour idle, one hour timed sleep,
  then shutdown. Early manual wake cancels shutdown; absent RTC support fails
  safe and is visible in health/status.
- PASS — Ruff 0.16.3 check and format, 96/96 Python unit/GUI/helper tests,
  ShellCheck 0.11.0 error-level validation, repository static contracts, English
  and Turkish Qt offscreen UI smoke, and isolated GRUB generation/syntax checks.
- PASS — disposable OVMF/QEMU UEFI acceptance proved a wrong THAWED password
  cannot reach the protected load region, the test-only correct password can,
  and FROZEN reaches it without authentication. No production credential was
  used or recorded.
- NOT RUN — physical suspend, RTC wake, shutdown, real initramfs/GRUB deployment,
  reboot, or FROZEN reset. The active workstation was inspected read-only for
  `rtcwake`, writable RTC wake-alarm support, logind idle hints, and suspend mode,
  but was not power-state or boot-stack mutated.

## 2026-08-20 — fail-closed GRUB and ready-user workflow — working tree based on `6ecf6e8`

- FIXED — the managed GRUB entry now gates every kernel/initramfs load behind an
  explicit authorization result in THAWED mode. A rejected or cancelled
  `authenticate` command leaves the guard false and returns to the menu, while
  the FROZEN path remains passwordless.
- FIXED — Users now presents **1. Install / repair applications** followed by
  **2. Create ready user**. Missing prerequisites stay on the Users workflow,
  and successful user creation no longer publishes Golden or schedules FROZEN.
- FIXED — automatic login detects the active display manager. Current Plasma
  Login Manager installations update `/etc/plasmalogin.conf` without discarding
  unrelated settings; SDDM retains its managed drop-in. An existing valid
  CachyFreeze SDDM selection is migrated during installation or live deployment.
- FIXED — installation stops the grub-btrfs Snapper path and daemon that conflict
  with CachyFreeze's single managed GRUB entry, then clears their stale failures.
  This addresses the recurring `grub-btrfs-snapper.service` error caused by its
  attempt to execute the intentionally disabled `41_snapshots-btrfs` generator.
- PASS — Ruff 0.16.3 check and format, 72/72 Python unit/GUI/helper/boundary
  tests, ShellCheck 0.11.0 error-level validation of 35 first-party scripts,
  static/desktop/XML/JSON contracts, Qt offscreen UI smoke and Users-page visual
  capture, isolated GRUB generation plus syntax validation, and Python compile.
- PASS — read-only physical diagnosis confirmed a THAWED `@` boot, Plasma Login
  Manager as the active display manager, a dormant CachyFreeze SDDM automatic-
  login selection, and the enabled grub-btrfs Snapper path repeatedly failing
  with permission denied on the disabled snapshot generator.
- NOT RUN — privileged live deployment, physical GRUB regeneration, initramfs
  build, reboot, and wrong-password boot validation. No non-interactive root
  channel was available, and the active workstation was not rebooted or
  boot-stack-mutated during this pass.

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
