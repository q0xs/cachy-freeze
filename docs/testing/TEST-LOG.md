# CachyFreeze test log

This file is the durable, English-only record of executed tests. Add results with
date, target, commit, command or scenario, result, and relevant non-sensitive notes.
Never record passwords, hashes, tokens, device UUIDs, or private user data.

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
