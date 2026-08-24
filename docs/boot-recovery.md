# Boot recovery

Keep recovery media and a restorable backup before installation.

If a FROZEN boot stops in initramfs, record the CachyFreeze error and do not
delete or rename subvolumes manually. Boot the persistent THAWED entry with the
GRUB maintenance password when that entry remains available, or use recovery
media to inspect the filesystem read-only.

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
