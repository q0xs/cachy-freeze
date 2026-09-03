# Development

Read all applicable `AGENTS.md` files. Keep host, loopback, VM, and physical
evidence separate. Never perform destructive acceptance testing on a normal
workstation.

Run repository-defined checks:

```bash
ruff check src app/cachy_freeze_gui tests
ruff format --check src app/cachy_freeze_gui tests
PYTHONPATH=src:app python -m unittest discover -s tests -v
SHELLCHECK_OPTS=--severity=error bash deepfreeze/tests/static.sh
QT_QPA_PLATFORM=offscreen bash deepfreeze/tests/ui-smoke.sh
bash deepfreeze/tests/grub-generation.sh
bash packaging/build-installer.sh
bash workstation/tests/static.sh
bash packaging/build-workstation-installer.sh
PYTHONPATH=src:app python -m unittest tests.test_ansible_contract -v
bash deepfreeze/tests/boot-acceptance-vm.sh
```

The workstation tests compile the KF6 KIdleTime agent, validate its root
supervisor with mocked lock/poweroff commands, check desktop/systemd files,
verify every vendored PKGBUILD against its `.SRCINFO`, and build the separate
portable payload. A live event-only test may run the compiled agent in a KDE
session with short thresholds; never connect those short test events to the
root supervisor.

`integration-btrfs.sh` and `integration-engine.sh` use disposable loopback Btrfs
filesystems and require root. `boot-acceptance-vm.sh` validates the generated
GRUB authentication boundary in a disposable QEMU/OVMF guest; it is not a
complete installed-OS lifecycle test. Full install/reboot/FROZEN/THAWED
acceptance requires a disposable CachyOS VM with a restorable disk snapshot.
Never point test overrides at the host root or host GRUB configuration.

In that disposable VM, validate this exact lifecycle: install; boot FROZEN;
create a marker; reboot FROZEN and prove it disappeared; THAW and prove a
persistent modification survives; FREEZE and prove that modification is the new
baseline; create another disposable marker and prove it disappears. Finally,
enumerate CachyFreeze-owned subvolumes and verify that no historical runtime or
Golden archive accumulated.

Record only executed results in `docs/testing/TEST-LOG.md`. Mark unavailable
checks `NOT RUN` or `BLOCKED`; do not infer success from source inspection.

Before completion inspect `git status`, `git diff`, and `git diff --check`, scan
for secrets and temporary artifacts, and preserve unrelated user changes.
