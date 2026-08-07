# CachyFreeze test log

This file is the durable, English-only record of executed tests. Add results with
date, target, commit, command or scenario, result, and relevant non-sensitive notes.
Never record passwords, hashes, tokens, device UUIDs, or private user data.

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
