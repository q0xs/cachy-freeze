"""Desktop application entry point."""

from __future__ import annotations

import argparse
import stat
import sys
from pathlib import Path

from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtWidgets import QApplication

from .backend import BackendClient
from .window import MainWindow


def _arguments(values: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--setup-source", type=Path)
    arguments, qt_arguments = parser.parse_known_args(values[1:])
    if arguments.setup_source is not None:
        setup_root = arguments.setup_source.resolve()
        marker = setup_root / ".cachyfreeze-root-staged"
        try:
            metadata = setup_root.stat()
        except OSError as error:
            parser.error(f"invalid installer staging directory: {error}")
        if (
            not str(setup_root).startswith("/run/cachyfreeze-installer.")
            or not marker.is_file()
            or metadata.st_uid != 0
            or stat.S_IMODE(metadata.st_mode) != 0o755
        ):
            parser.error("installer staging directory is not root-owned and verified")
        arguments.setup_source = setup_root
    arguments.qt_arguments = [values[0], *qt_arguments]
    return arguments


def main() -> int:
    arguments = _arguments(sys.argv)
    application = QApplication(arguments.qt_arguments)
    application.setApplicationName("CachyFreeze")
    application.setOrganizationName("CachyFreeze")
    application.setWindowIcon(QIcon(str(Path(__file__).with_name("assets") / "cachy-freeze.png")))
    application.setFont(QFont("Noto Sans", 10))
    backend = BackendClient(setup_root=arguments.setup_source)
    window = MainWindow(backend)
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
