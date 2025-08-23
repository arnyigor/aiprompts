# src/sync_log_dialog.py
from PyQt6.QtCore import pyqtSlot, Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPlainTextEdit, QDialogButtonBox
)

class SyncLogDialog(QDialog):
    """
    Диалоговое окно для отображения процесса синхронизации в реальном времени.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Процесс синхронизации")
        self.setMinimumSize(600, 400)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        # Основные компоненты
        self.status_label = QLabel("Подготовка к синхронизации...")
        self.log_text_edit = QPlainTextEdit()
        self.log_text_edit.setReadOnly(True)
        self.log_text_edit.setStyleSheet("font-family: Consolas, Courier New, monospace;")

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False) # Кнопка "Ок" неактивна, пока идет процесс
        self.button_box.accepted.connect(self.accept)

        # Компоновка
        layout = QVBoxLayout(self)
        layout.addWidget(self.status_label)
        layout.addWidget(self.log_text_edit)
        layout.addWidget(self.button_box)

    @pyqtSlot(str)
    def set_status(self, message: str):
        """Обновляет верхнюю метку статуса (основной шаг)."""
        self.status_label.setText(message)

    @pyqtSlot(str)
    def add_log_message(self, message: str):
        """Добавляет подробное сообщение в лог."""
        self.log_text_edit.appendPlainText(message)
        # Автоматически прокручиваем вниз
        self.log_text_edit.verticalScrollBar().setValue(
            self.log_text_edit.verticalScrollBar().maximum()
        )

    def mark_as_finished(self):
        """Вызывается по завершении процесса."""
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)
        self.status_label.setText("Синхронизация завершена.")