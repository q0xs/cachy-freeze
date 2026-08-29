# Vendored package recipes

These are reviewed snapshots of AUR packaging recipes used only by the separate
CachyWorkstation portable provisioner. Upstream AUR base commit IDs are in
`aur/AUR-REVISIONS.txt`; any reviewed changes needed after an upstream download
changed are recorded in `aur/DOWNSTREAM-CHANGES.md`.

The recipes download applications from their upstream HTTPS locations and
verify the hashes maintained in the reviewed PKGBUILDs. They are built by a
dedicated unprivileged system account. Runtime installation prefers a signed
configured CachyOS repository package with the same name when available.

Package and application licenses remain those declared by each recipe and
upstream application. Vendoring a packaging recipe does not relicense the
downloaded proprietary application.
