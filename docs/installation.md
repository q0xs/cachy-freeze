# Installation

Use the graphical `.run` installer for normal deployments. Target computers do
not need this repository.

## Requirements

- CachyOS or Arch Linux with KDE Plasma
- UEFI + GRUB
- Btrfs root subvolume `@`
- EFI mounted at `/boot/efi`
- no separate `/boot` filesystem
- internet access during setup
- recovery media and a restorable backup

The installer checks the platform before changing CachyFreeze-owned Btrfs,
initramfs, or GRUB state.

## Fresh Employee Machine

1. Install CachyOS with the supported Btrfs layout.
2. Create the administrator account.
3. Create the employee account as a standard user.
4. Log in once as the employee, then return to the administrator account.
5. Download `CachyFreeze-Installer-1.0.0rc10.run` and its `.sha256` file.
6. Verify the download:

```bash
sha256sum --check CachyFreeze-Installer-1.0.0rc10.run.sha256
chmod 0755 CachyFreeze-Installer-1.0.0rc10.run
```

7. Start the installer without `sudo`:

```bash
./CachyFreeze-Installer-1.0.0rc10.run
```

8. Approve the PolicyKit prompt.
9. Enter the employee username and click **INSTALL / REPAIR WORKSTATION**.
10. Log in as the employee and open Chrome, LibreOffice, AnyDesk, Zoiper, and
    MicroSIP once.
11. Return to the administrator account and click **CHECK WORKSTATION**.
12. Continue only if it reports `OVERALL: PASS` and `Ready for freeze: YES`.
    The graphical installer keeps **INSTALL CACHYFREEZE** disabled until this
    final check passes for the selected employee.
13. Enter the GRUB maintenance password twice.
14. Click **INSTALL CACHYFREEZE**.
15. Click **REBOOT NOW** after setup succeeds.

## Existing Installation

Run Workstation repair or system updates only from THAWED:

1. Open CachyFreeze.
2. Click **THAW COMPUTER**.
3. Click **REBOOT NOW**.
4. Confirm the app shows **THAWED** after reboot.
5. Install, repair, or check Workstation.
6. Test the employee apps manually.
7. Click **FREEZE COMPUTER**.
8. Click **REBOOT NOW**.

Never provision Workstation from FROZEN `@active`.

## GRUB Password

The maintenance user is always `cachyadmin`.

- FROZEN boots without the password.
- THAWED from GRUB requires `cachyadmin` and the password chosen during setup.
- The plaintext password is sent through process stdin and is not stored.

## Notes

- CachyFreeze never reboots automatically.
- FROZEN reboots create a fresh disposable `@active` from `@golden`.
- THAWED is the only mode for updates, repairs, and Workstation changes.
- Workstation health includes the employee account, applications, idle policy,
  and KDE login-screen preselection without automatic login.
- The standalone `CachyWorkstation-Setup-1.0.2.run` remains available only for
  CLI-only deployments.

## Build

```bash
bash packaging/build-installer.sh
```

The artifact and checksum are written to `dist/`.
