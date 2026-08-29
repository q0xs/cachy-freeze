# Installer build

Run from an unprivileged checkout:

```bash
bash packaging/build-installer.sh
```

The reproducible self-extracting Linux installer is written to
`dist/CachyFreeze-Installer-<version>.run`, with a SHA-256 sidecar. Set
`SOURCE_DATE_EPOCH` to the release timestamp when producing release artifacts.

Opening the executable verifies its embedded file manifest, requests PolicyKit
authorization, copies the payload into a root-owned `/run` staging directory,
and verifies the same manifest again before launching the graphical installer.
Successful installation removes that staging copy; failed or cancelled staging
is transient and disappears on reboot. The artifact is a native Linux `.run`
installer, not a renamed Windows executable and not a Git checkout dependency.

## Portable workstation provisioner

The workstation application and idle-policy provisioner is a separate product
payload. Build it without modifying the CachyFreeze installer:

```bash
bash packaging/build-workstation-installer.sh
```

This creates `dist/CachyWorkstation-Setup-<version>.run` and its SHA-256
sidecar. The artifact embeds reviewed AUR recipes, MicroSIP source metadata,
launcher templates, the KDE idle-agent source, and the provisioning modules.
On a THAWED target workstation, run it as root with the already-created
standard username:

```bash
sudo ./CachyWorkstation-Setup-<version>.run wrw1166
```

Application binaries are intentionally not embedded. The target downloads the
reviewed versions from signed CachyOS repositories or pinned upstream HTTPS
locations and verifies the embedded hashes, so this artifact requires an
internet connection during provisioning.
