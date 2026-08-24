# Btrfs, initramfs, and GRUB rules

- Apply `../AGENTS.md`.
- Subvolume names and transaction phases are persistent recovery contracts.
- Mutate only under the operation lock and a verified top-level Btrfs mount.
- Keep Golden read-only and create Active from Golden; never retain the previous
  Active or a historical Golden after success; never destructively test real subvolumes.
- Keep the initramfs hook before `filesystems` and verify generated images.
- Generate one managed GRUB entry: FROZEN is passwordless; THAWED requires `cachyadmin`.
- Never run `btrfs check --repair` or deliberately damage physical EFI/GRUB.
- Preserve unrelated GRUB entries. Run engine, Btrfs loop, GRUB generation, and
  initramfs tests only on safe targets.
