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
