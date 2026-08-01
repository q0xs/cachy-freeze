"""Backend-specific exceptions with safe messages for the desktop client."""


class CachyFreezeError(RuntimeError):
    """Base exception for an expected Cachy Freeze failure."""


class ConfigurationError(CachyFreezeError):
    """Raised when the root-owned configuration is invalid."""


class CommandError(CachyFreezeError):
    """Raised when a required system command fails."""

    def __init__(self, command: list[str], returncode: int, detail: str) -> None:
        self.command = tuple(command)
        self.returncode = returncode
        self.detail = detail.strip()
        program = command[0] if command else "command"
        message = self.detail or f"{program} failed with exit code {returncode}"
        super().__init__(message)


class IntegrityError(CachyFreezeError):
    """Raised when snapshot metadata or a Btrfs object does not verify."""
