"""Desktop application entry point."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtWidgets import QApplication

from .backend import BackendClient
from .i18n import configure, preferred_language
from .window import MainWindow


def _arguments(values: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--setup-source", type=Path)
    arguments, qt_arguments = parser.parse_known_args(values[1:])
    arguments.qt_arguments = [values[0], *qt_arguments]
    return arguments


def main() -> int:
    arguments = _arguments(sys.argv)
    application = QApplication(arguments.qt_arguments)
    application.setApplicationName("CachyFreeze Management Center")
    application.setOrganizationName("CachyOS Workstation")
    application.setWindowIcon(QIcon(str(Path(__file__).with_name("assets") / "cachy-freeze.png")))
    application.setFont(QFont("Noto Sans", 10))
    configure(preferred_language())
    backend = BackendClient(setup_root=arguments.setup_source)
    window = MainWindow(backend)
    window.show()
    if arguments.setup_source is not None:
        window.open_setup_page()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
