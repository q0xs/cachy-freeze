# GUI and PolicyKit rules

- Apply `../AGENTS.md`.
- Keep the GUI unprivileged. Root operations use the PolicyKit helper with an exact allow-list.
- Pass QProcess programs and arguments separately. Secrets use stdin/write-channel and are cleared.
- Validate counts, fixed values, modes, and paths; reject traversal.
- Expose only verified current/next mode, FREEZE, THAW, refresh, and explicit reboot.
- The graphical installer is one page and sends its GRUB secret through stdin only.
- GUI changes require mode, error/cancel, secret-channel, PolicyKit, and desktop-entry tests.
