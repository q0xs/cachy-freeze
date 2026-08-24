# Repository rules

These rules apply to the entire repository. A nested `AGENTS.md` adds rules for its directory.

## Start-up

- Read this file, `README.md`, `docs/architecture.md`, `docs/installation.md`,
  `docs/development.md`, and `docs/testing/TEST-LOG.md` before making changes.
- Inspect status, remotes, and recent commits. Never discard or overwrite user changes.
- Keep VM and physical-device evidence separate and revalidate the actual target.

## Product contract

- The normal product has only FROZEN and THAWED modes. Do not add workstation,
  user, application, power, diagnostics, or snapshot-history management.
- The public installation entry is the reproducible graphical single-file
  installer. The installed GUI remains unprivileged; root work uses PolicyKit.
- Never promote FROZEN runtime data or retain historical runtime/Golden copies.

## Safety

- Never expose passwords, hashes, tokens, keys, device UUIDs, or private user data.
  Secrets use the existing stdin/write-channel only.
- Stop on unsupported UEFI/Btrfs/`@`/GRUB/EFI layouts. Never bypass preflight.
- Never run `btrfs check --repair` or manually damage/delete managed subvolumes.
- Never interrupt pacman, Golden publication, mkinitcpio, or GRUB writes.
- Destructive physical tests require explicit approval and full recovery readiness.

## Quality and GitHub

- Preserve locking, atomic writes, validation, transient transaction recovery,
  logical runtime non-retention, and unrelated Btrfs/GRUB state.
- Run Ruff, all Python tests, Bash/ShellCheck, systemd/desktop validation, and Qt smoke.
- Run boot-stack integration only on a disposable VM or approved pilot.
- Record actual results in `docs/testing/TEST-LOG.md`; never claim an unrun test passed.
- Stage only relevant files, review diffs, use focused commits, push directly to `main`
  unless the user requests a PR, and watch GitHub Actions to completion.
