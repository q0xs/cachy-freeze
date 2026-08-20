# Development

Read the applicable `AGENTS.md` files before editing. Preserve user changes and
keep physical-device, VM, and CI evidence separate.

Run the local quality gate with CI-equivalent imports:

```bash
ruff check src app/cachy_freeze_gui tests
ruff format --check src app/cachy_freeze_gui tests
PYTHONPATH=src:app python -m unittest discover -s tests -v
SHELLCHECK_OPTS=--severity=error bash deepfreeze/tests/static.sh
QT_QPA_PLATFORM=offscreen bash deepfreeze/tests/ui-smoke.sh
bash deepfreeze/tests/grub-generation.sh
bash deepfreeze/tests/boot-acceptance-vm.sh
```

The UEFI authentication acceptance script uses temporary OVMF/QEMU guests and
requires `qemu-system-x86_64`, OVMF, Expect, and GRUB EFI tools. Safe
disposable-target integration scripts live in `deepfreeze/tests/`.
Never run Btrfs loop, initramfs, GRUB, reboot, recovery, or power-loss tests on
an ordinary workstation. Record every actual result in `testing/TEST-LOG.md`.

Before publishing, inspect `git status`, `git diff`, `git diff --check`, and the
staged diff. Stage named files only, scan for secrets, push without force, and
watch GitHub Actions to completion.
