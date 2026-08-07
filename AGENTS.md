# Repository rules

These rules apply to the entire repository. A nested `AGENTS.md` adds rules for its directory.

## Start-up

- Read this file, `README.md`, `docs/architecture.md`, `docs/installation.md`,
  `docs/development.md`, and `docs/testing/TEST-LOG.md` before making changes.
- Inspect status, remotes, and recent commits. Never discard or overwrite user changes.
- Keep VM and physical-device evidence separate and revalidate the actual target.

## Product contract

- Engine installation, user management, and FROZEN activation are independent.
  A user account must never be required to install or freeze CachyFreeze.
- Public installation entries are the graphical setup launcher and documented
  one-command installer. The GUI remains unprivileged; root work uses PolicyKit.

## Safety

- Never expose passwords, hashes, tokens, keys, device UUIDs, or private user data.
  Secrets use the existing stdin/write-channel only.
- Stop on unsupported UEFI/Btrfs/`@`/GRUB/EFI layouts. Never bypass preflight.
- Never run `btrfs check --repair` or manually damage/delete managed subvolumes.
- Never interrupt pacman, Golden publication, mkinitcpio, or GRUB writes.
- Destructive physical tests require explicit approval and full recovery readiness.

## Quality and GitHub

- Preserve locking, atomic writes, validation, and transaction recovery.
- Run Ruff, all Python tests, Bash/ShellCheck, systemd/desktop validation, and Qt smoke.
- Run boot-stack integration only on a disposable VM or approved pilot.
- Record actual results in `docs/testing/TEST-LOG.md`; never claim an unrun test passed.
- Stage only relevant files, review diffs, use focused commits, push directly to `main`
  unless the user requests a PR, and watch GitHub Actions to completion.
