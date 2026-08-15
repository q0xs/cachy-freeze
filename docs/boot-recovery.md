# Boot recovery

CachyFreeze keeps Golden and Active publication recoverable with staged names
and a persistent transaction journal. Early boot validates the expected Btrfs
device and subvolume names before completing or rolling back an interrupted step.

If FROZEN does not reach the graphical target repeatedly, boot-attempt tracking
can restore the previous healthy Golden. THAWED maintenance uses the fixed GRUB
username `cachyadmin` and the password chosen on the Setup page. `cachyadmin` is
a GRUB-only credential, not a Linux administrator account.

When recovery is needed:

1. Preserve the current and previous boot journals.
2. Check the kernel mode argument, mounted root, transaction journal, Golden,
   Active, and Btrfs device error counters without mutating them.
3. Use THAWED or recovery media only after identifying the failed phase.
4. Never run `btrfs check --repair` or manually delete managed subvolumes.

Physical destructive recovery tests require explicit approval and full backup readiness.
