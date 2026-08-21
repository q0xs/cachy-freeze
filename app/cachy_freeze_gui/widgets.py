"""Qt widgets that retain source text and apply the active interface locale."""

from __future__ import annotations

from typing import Any

from PyQt6.QtWidgets import (
    QCheckBox as _QCheckBox,
)
from PyQt6.QtWidgets import (
    QComboBox as _QComboBox,
)
from PyQt6.QtWidgets import (
    QDialog as _QDialog,
)
from PyQt6.QtWidgets import (
    QDialogButtonBox as _QDialogButtonBox,
)
from PyQt6.QtWidgets import (
    QFormLayout as _QFormLayout,
)
from PyQt6.QtWidgets import (
    QGroupBox as _QGroupBox,
)
from PyQt6.QtWidgets import (
    QInputDialog as _QInputDialog,
)
from PyQt6.QtWidgets import (
    QLabel as _QLabel,
)
from PyQt6.QtWidgets import (
    QLineEdit as _QLineEdit,
)
from PyQt6.QtWidgets import (
    QMainWindow as _QMainWindow,
)
from PyQt6.QtWidgets import (
    QMessageBox as _QMessageBox,
)
from PyQt6.QtWidgets import (
    QPlainTextEdit as _QPlainTextEdit,
)
from PyQt6.QtWidgets import (
    QPushButton as _QPushButton,
)
from PyQt6.QtWidgets import (
    QSpinBox as _QSpinBox,
)
from PyQt6.QtWidgets import (
    QTableWidget as _QTableWidget,
)
from PyQt6.QtWidgets import (
    QTableWidgetItem as _QTableWidgetItem,
)
from PyQt6.QtWidgets import (
    QWidget,
)

from .i18n import tr


class _TextMixin:
    _source_text: str

    def setText(self, text: str) -> None:
        self._source_text = text
        super().setText(tr(text))  # type: ignore[misc]

    def retranslate(self) -> None:
        super().setText(tr(self._source_text))  # type: ignore[misc]


class QLabel(_TextMixin, _QLabel):
    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        self._source_text = text
        super().__init__(tr(text), parent)


class QPushButton(_TextMixin, _QPushButton):
    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        self._source_text = text
        super().__init__(tr(text), parent)


class QCheckBox(_TextMixin, _QCheckBox):
    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        self._source_text = text
        super().__init__(tr(text), parent)


class QGroupBox(_QGroupBox):
    def __init__(self, title: str = "", parent: QWidget | None = None) -> None:
        self._source_title = title
        super().__init__(tr(title), parent)

    def setTitle(self, title: str) -> None:
        self._source_title = title
        super().setTitle(tr(title))

    def retranslate(self) -> None:
        super().setTitle(tr(self._source_title))


class QLineEdit(_QLineEdit):
    def setPlaceholderText(self, text: str) -> None:
        self._source_placeholder = text
        super().setPlaceholderText(tr(text))

    def setToolTip(self, text: str) -> None:
        self._source_tooltip = text
        super().setToolTip(tr(text))

    def retranslate(self) -> None:
        if hasattr(self, "_source_placeholder"):
            super().setPlaceholderText(tr(self._source_placeholder))
        if hasattr(self, "_source_tooltip"):
            super().setToolTip(tr(self._source_tooltip))


class QPlainTextEdit(_QPlainTextEdit):
    def setPlaceholderText(self, text: str) -> None:
        self._source_placeholder = text
        super().setPlaceholderText(tr(text))

    def setPlainText(self, text: str) -> None:
        self._source_plain_text = text
        super().setPlainText(tr(text))

    def appendPlainText(self, text: str) -> None:
        super().appendPlainText(tr(text))

    def retranslate(self) -> None:
        if hasattr(self, "_source_placeholder"):
            super().setPlaceholderText(tr(self._source_placeholder))
        if hasattr(self, "_source_plain_text"):
            super().setPlainText(tr(self._source_plain_text))


class QMainWindow(_QMainWindow):
    def setWindowTitle(self, title: str) -> None:
        self._source_window_title = title
        super().setWindowTitle(tr(title))

    def retranslate(self) -> None:
        if hasattr(self, "_source_window_title"):
            super().setWindowTitle(tr(self._source_window_title))


class QDialog(_QDialog):
    def setWindowTitle(self, title: str) -> None:
        self._source_window_title = title
        super().setWindowTitle(tr(title))


class QFormLayout(_QFormLayout):
    def addRow(self, *arguments: Any) -> None:
        values = list(arguments)
        if values and isinstance(values[0], str):
            values[0] = QLabel(values[0])
        super().addRow(*values)


class QComboBox(_QComboBox):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._source_items: dict[int, str] = {}

    def addItem(self, text: str, user_data: Any = None) -> None:
        super().addItem(tr(text), user_data)
        self._source_items[self.count() - 1] = text

    def retranslate(self) -> None:
        for index, source in self._source_items.items():
            self.setItemText(index, tr(source))


class QTableWidget(_QTableWidget):
    def setHorizontalHeaderLabels(self, labels: list[str] | tuple[str, ...]) -> None:
        self._source_headers = list(labels)
        super().setHorizontalHeaderLabels([tr(label) for label in labels])

    def retranslate(self) -> None:
        if hasattr(self, "_source_headers"):
            super().setHorizontalHeaderLabels([tr(label) for label in self._source_headers])


class QTableWidgetItem(_QTableWidgetItem):
    def __init__(self, text: str = "", item_type: int = 0) -> None:
        super().__init__(tr(text), item_type)


class QMessageBox(_QMessageBox):
    @staticmethod
    def _show(
        icon: _QMessageBox.Icon,
        parent: QWidget | None,
        title: str,
        text: str,
        *arguments: Any,
    ):
        buttons = arguments[0] if arguments else _QMessageBox.StandardButton.Ok
        default_button = (
            arguments[1] if len(arguments) > 1 else _QMessageBox.StandardButton.NoButton
        )
        box = _QMessageBox(icon, tr(title), tr(text), buttons, parent)
        if default_button != _QMessageBox.StandardButton.NoButton:
            box.setDefaultButton(default_button)
        labels = {
            _QMessageBox.StandardButton.Ok: tr("OK"),
            _QMessageBox.StandardButton.Cancel: tr("Cancel"),
            _QMessageBox.StandardButton.Yes: tr("Yes"),
            _QMessageBox.StandardButton.No: tr("No"),
        }
        for standard_button, label in labels.items():
            button = box.button(standard_button)
            if button is not None:
                button.setText(label)
        return _QMessageBox.StandardButton(box.exec())

    @staticmethod
    def information(parent: QWidget | None, title: str, text: str, *arguments: Any):
        return QMessageBox._show(_QMessageBox.Icon.Information, parent, title, text, *arguments)

    @staticmethod
    def warning(parent: QWidget | None, title: str, text: str, *arguments: Any):
        return QMessageBox._show(_QMessageBox.Icon.Warning, parent, title, text, *arguments)

    @staticmethod
    def critical(parent: QWidget | None, title: str, text: str, *arguments: Any):
        return QMessageBox._show(_QMessageBox.Icon.Critical, parent, title, text, *arguments)

    @staticmethod
    def question(parent: QWidget | None, title: str, text: str, *arguments: Any):
        if not arguments:
            arguments = (
                _QMessageBox.StandardButton.Yes | _QMessageBox.StandardButton.No,
                _QMessageBox.StandardButton.No,
            )
        return QMessageBox._show(_QMessageBox.Icon.Question, parent, title, text, *arguments)


class QInputDialog(_QInputDialog):
    @staticmethod
    def getText(parent: QWidget | None, title: str, label: str, *arguments: Any):
        return _QInputDialog.getText(parent, tr(title), tr(label), *arguments)

    @staticmethod
    def getItem(
        parent: QWidget | None,
        title: str,
        label: str,
        items: list[str] | tuple[str, ...],
        *arguments: Any,
    ):
        return _QInputDialog.getItem(
            parent,
            tr(title),
            tr(label),
            [tr(item) for item in items],
            *arguments,
        )


class QDialogButtonBox(_QDialogButtonBox):
    def __init__(self, *arguments: Any, **keywords: Any) -> None:
        super().__init__(*arguments, **keywords)
        self.retranslate()

    def retranslate(self) -> None:
        translations = {
            self.StandardButton.Ok: tr("OK"),
            self.StandardButton.Cancel: tr("Cancel"),
            self.StandardButton.Yes: tr("Yes"),
            self.StandardButton.No: tr("No"),
        }
        for standard_button, translated in translations.items():
            button = self.button(standard_button)
            if button is not None:
                button.setText(translated)


class QSpinBox(_QSpinBox):
    def setSuffix(self, suffix: str) -> None:
        self._source_suffix = suffix
        super().setSuffix(tr(suffix))

    def retranslate(self) -> None:
        if hasattr(self, "_source_suffix"):
            super().setSuffix(tr(self._source_suffix))


def retranslate_tree(root: QWidget) -> None:
    if hasattr(root, "retranslate"):
        root.retranslate()  # type: ignore[attr-defined]
    for child in root.findChildren(QWidget):
        if hasattr(child, "retranslate"):
            child.retranslate()  # type: ignore[attr-defined]
