# Boot recovery

Keep recovery media and a restorable backup before installation.

If a FROZEN boot stops in initramfs, record the CachyFreeze error and do not
delete or rename subvolumes manually. RC6 attempts to schedule the next boot as
the single password-protected THAWED entry. Reboot, select THAWED, and
authenticate as the fixed GRUB user `cachyadmin`. If that fallback could not be
written, use recovery media to inspect the filesystem read-only.

The normal GRUB menu intentionally exposes only the scheduled mode. Vendor,
firmware, snapshot, and custom entries are preserved in `grub.cfg` but appear
only while `cachy_recovery=1`. From an already verified THAWED system, an
administrator can expose them for the next recovery session with:

```bash
sudo grub-editenv /boot/grub/grubenv set cachy_recovery=1
```

Return to the normal single-entry boundary afterward with:

```bash
sudo grub-editenv /boot/grub/grubenv set cachy_recovery=0
```

Transaction-scoped `.next` and `.pending` names and `@cachy-capture` are part
of the recovery protocol. Their presence without a valid journal or an
expected initramfs transition is an integrity error, not permission to guess
which copy is valid.

Do not run `btrfs check --repair`. Do not delete `@`, `@golden`, `@active`,
`@cachy-state`, or similarly named objects based only on their names. Confirm
filesystem UUID, subvolume metadata, mounted root, CachyFreeze state, and backup
readiness first.

CachyFreeze intentionally has no historical snapshot rollback archive. Restore
from the administrator’s independent system backup when Golden and persistent
THAWED state cannot be verified.
