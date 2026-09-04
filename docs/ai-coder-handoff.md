# CachyFreeze AI Coder Handoff

This file is a compact technical handoff for the next Codex or AI-coder session.
It summarizes the current release posture, the areas that are intentionally not
validated on this workstation, and the safe next steps.

## Current repo state

- Repository: `https://github.com/q0xs/cachy-freeze`
- Default branch: `main`
- Current source version: `1.0.0rc10`
- Current public release candidate:
  `https://github.com/q0xs/cachy-freeze/releases/tag/v1.0.0rc10`
- Release status: prerelease by choice. Do not publish stable `v1.0.0` unless
  the operator explicitly requests it after pilot validation.
- Public installer asset:
  `CachyFreeze-Installer-1.0.0rc10.run`
- Workstation payload asset:
  `CachyWorkstation-Setup-1.0.2.run`

`v1.0.0rc10` exists mainly so GitHub downloaders receive the responsive PyQt6 UI
layout fixes. The UI keeps short button labels for compact windows:

- `INSTALL / REPAIR`
- `CHECK`

Do not rename these back to longer labels unless the layout is revalidated at
compact and high-DPI sizes.

## Stable release gate

Keep the project in prerelease status until Ansible fleet management and
Semaphore UI operation have been tested on real approved targets. Before a
stable `v1.0.0` release, complete and record these checks:

1. Run the full non-destructive local test set.
2. Run the GitHub Actions workflow to completion on `main`.
3. Test `ansible/test-syntax.sh` and the Semaphore Compose config.
4. Start Semaphore on an approved Master PC.
5. Create the documented Semaphore project, key store, repository, inventory,
   variable group, and task templates.
6. Run `Filo Durumu` against a lab inventory.
7. Run `Gece Bakimi` against lab before any production schedule.
8. Validate at least one disposable VM or approved pilot PC through the full
   install/reboot/FROZEN reset/THAWED persistence/FREEZE lifecycle.

Do not cut stable `v1.0.0` from source review alone. The stable release should
follow executed lab evidence.

## Release asset signing note

Current release assets have SHA-256 sidecar files. SHA-256 confirms that a
downloaded file matches the published checksum, but it does not prove authorship
if an attacker can replace both the installer and the checksum.

Before stable `v1.0.0`, decide whether to add Minisign or GPG signatures for
release assets. This would let users verify that the installer was signed by the
project's private release key, not only that the download matches a checksum.
For a 200-300 PC fleet where the installer runs with root privileges, signatures
are a useful release-hardening improvement. They are not required for the
current prerelease stage unless the operator chooses to add them earlier.

## Product boundaries

- The product has only two runtime modes: FROZEN and THAWED.
- Keep the existing Current Mode display working.
- Do not add snapshot history, user management, application management,
  diagnostics dashboards, or extra lifecycle modes to the normal GUI.
- Do not reboot, freeze, thaw, mutate GRUB, mutate Btrfs, or run physical
  lifecycle tests on the active workstation without explicit operator approval.
- Do not store passwords, private keys, tokens, hashes, device UUIDs, or private
  user data in git, logs, or test records.

## Key files

- GUI layout:
  - `app/cachy_freeze_gui/window.py`
  - `app/cachy_freeze_gui/styles.py`
  - `tests/test_gui.py`
- Core lifecycle:
  - `src/cachy_freeze/engine.py`
  - `src/cachy_freeze/cli.py`
  - `deepfreeze/bin/cachy-freeze`
  - `deepfreeze/grub/99_cachy_freeze`
- Installer:
  - `installer/install-cachyfreeze.sh`
  - `installer/install-freeze-engine.sh`
  - `packaging/build-installer.sh`
- Workstation provisioning:
  - `workstation/bin/workstation-setup`
  - `workstation/lib/`
  - `packaging/build-workstation-installer.sh`
- Ansible and Semaphore:
  - `ansible/playbooks/`
  - `ansible/roles/`
  - `ansible/docker-compose.semaphore.yml`
  - `ansible/setup-controller.sh`
  - `ansible/SEMAPHORE-REHBERI.md`

## Validated behavior

The current repository has test coverage for:

- PyQt6 compact layout regression and Current Mode behavior.
- CLI contract for `freeze`, `thaw`, `thaw --authorized`, `boot-success`,
  `reboot`, and removed management commands.
- Authorized remote THAWED boot: `cachy_remote_auth=1` is consumed with
  `boot-success` before Ansible reads post-reboot status.
- Ansible syntax checks for all playbooks.
- Semaphore Compose config validation in GitHub Actions.
- QEMU/OVMF GRUB authentication boundary in GitHub Actions.
- Reproducible single-file installer builds and checksum sidecars.

The latest known successful GitHub Actions workflow was `Statik kontroller` on
`main` after the rc10 release-verification documentation update.

## Local validation commands

Use these non-destructive checks first:

```bash
ruff check .
ruff format --check src app/cachy_freeze_gui tests
PYTHONPATH=src:app QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests -v
QT_QPA_PLATFORM=offscreen bash deepfreeze/tests/ui-smoke.sh
SHELLCHECK_OPTS=--severity=error bash deepfreeze/tests/static.sh
bash workstation/tests/static.sh
bash deepfreeze/tests/grub-generation.sh
```

If Ansible is not installed system-wide but the temporary venv exists:

```bash
PATH=/tmp/cachy-freeze-ansible-venv/bin:$PATH bash ansible/test-syntax.sh
```

If Docker is installed:

```bash
SEMAPHORE_DB_PASS=ci-db-pass \
SEMAPHORE_ADMIN_PASSWORD=ci-admin-pass \
SEMAPHORE_ACCESS_KEY_ENCRYPTION=MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNDU2Nzg5MDE= \
docker compose -f ansible/docker-compose.semaphore.yml config >/dev/null
```

Record only commands that were actually executed in `docs/testing/TEST-LOG.md`.
Mark unavailable checks as `NOT RUN`; do not infer success from source review.

## Semaphore live test plan

The repo contains Semaphore support, but a real controller UI run may still need
pilot validation. When an approved Master PC is available:

1. Clone the repo on the controller.
2. Run:

   ```bash
   cd cachy-freeze/ansible
   ./setup-controller.sh --with-semaphore
   ```

3. Confirm `ansible/.semaphore.env` exists and remains mode `0600`.
4. Confirm the Compose stack is healthy:

   ```bash
   sudo docker compose \
     -p cachy-freeze-semaphore \
     --env-file ansible/.semaphore.env \
     -f ansible/docker-compose.semaphore.yml \
     ps
   ```

5. Open `http://localhost:3000`.
6. Create the project, key store records, repository, inventory, variable group,
   and task templates exactly as described in `ansible/SEMAPHORE-REHBERI.md`.
7. Run `Filo Durumu` against `lab` first.
8. Run `Gece Bakimi` against `lab` before any production schedule.
9. Only after lab success, schedule production with conservative batching such
   as `batch_size: "20%"` or lower.

Do not start with production. Do not put the GRUB maintenance password in
inventory, repository files, task logs, or screenshots.

## Known intentional gaps

- The current public release is still a prerelease. GitHub's stable "latest
  release" API may not resolve while all public releases are prereleases. Use
  the direct `v1.0.0rc10` URL until a stable release is intentionally published.
- A full physical install/reboot/FROZEN reset/THAWED persistence lifecycle test
  requires a disposable CachyOS VM or approved pilot PC with a restorable disk
  snapshot.
- A real Semaphore browser session and live task execution require a controller
  with Docker/Compose and lab targets.
- Local installed metadata on a throwaway workstation may lag the source release
  if files were manually refreshed. Treat the GitHub release asset as the
  canonical installer for new machines.

## Suggested next decisions

- Run a real Semaphore controller pilot or keep it documentation/CI-only until
  the fleet controller is ready.
- After one successful disposable VM or pilot-PC lifecycle pass, decide whether
  to publish stable `v1.0.0`.
- Before stable `v1.0.0`, decide whether release assets need Minisign or GPG
  signatures in addition to SHA-256 sidecar files.
