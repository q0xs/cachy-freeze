# Installer rules

- Apply `../AGENTS.md`.
- The public entry is the reproducible single-file graphical installer; other scripts are internal.
- Read secrets only from stdin and never expose them in arguments, environment, logs, or files.
- Require automatic preflight and writable maintenance `@`; retain a recoverable boot backup.
- Do not install workstation applications or package removed user-management features.
- Never reboot during package, initramfs, GRUB, or Golden writes.
- Run Bash, ShellCheck, static, single-file build, GUI setup, and safe disposable-target tests.
