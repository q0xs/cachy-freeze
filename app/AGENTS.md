# GUI and PolicyKit rules

- Apply `../AGENTS.md`.
- Keep the GUI unprivileged. Root operations use the PolicyKit helper with an exact allow-list.
- Pass QProcess programs and arguments separately. Secrets use stdin/write-channel and are cleared.
- Validate counts, fixed values, names, IDs, and paths; reject traversal.
- Preserve native CachyOS account rights.
- Installation, user creation, and FROZEN activation must remain independent.
- GUI changes require page, error/cancel, secret-channel, PolicyKit, and desktop-entry tests.
