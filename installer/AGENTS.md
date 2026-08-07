# Installer rules

- Apply `../AGENTS.md`.
- Public entries are `../install.sh` and the graphical setup page; other scripts are internal.
- Read secrets only from stdin and never expose them in arguments, environment, logs, or files.
- Require preflight and writable maintenance `@`; retain a recoverable boot backup.
- Do not build AUR packages as root or weaken download/archive validation.
- Preserve native account group membership and administrator rights.
- Never reboot during package, initramfs, GRUB, or Golden writes.
- Run Bash, ShellCheck, static, GUI setup, and safe disposable-target tests.
