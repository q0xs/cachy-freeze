# Reviewed downstream recipe changes

## zoiper-bin 5.6.13-3

The AUR base revision in `AUR-REVISIONS.txt` expected SHA-256
`0f722b597d98da1d26cbe1cb243465c989fb1fbdf141a43924dc56face07ff97`.
On 2026-08-29 the official Zoiper Linux endpoint served a stable replacement
archive for the same 5.6.13 version with SHA-256
`91a9947f7b8447f57206aed2f052366a541bbdfc39b2c793227dbaf27d42a17e`.

Two independent HTTPS downloads were byte-identical (119,671,888 bytes). The
archive was opened successfully, contained the expected `Zoiper5/` payload,
and its `Zoiper5/zoiper` entry was a stripped 64-bit x86-64 ELF executable. The
reviewed recipe checksum was updated and `pkgrel` was bumped from 2 to 3. The
upstream binary is downloaded on the target and is not vendored here.
