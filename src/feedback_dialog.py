# src/feedback_dialog.py

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QTextEdit, QDialogButtonBox
)

class FeedbackDialog(QDialog):
    """
    Диалоговое окно для сбора и отправки обратной связи от пользователя.
    """
    def __init__(self, parent=None):
        """
        Инициализирует диалоговое окно.

        Args:
            parent: Родительский виджет.
        """
        super().__init__(parent)
        self.setWindowTitle("Обратная связь")
        self.setMinimumSize(400, 250)

        # Layout
        layout = QVBoxLayout(self)

        # Widgets
        self.label = QLabel("Пожалуйста, опишите вашу проблему или предложение:")
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("Введите ваше сообщение здесь...")

        # Кнопки "Отправить" и "Отмена"
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setText("Отправить")
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")

        # Add widgets to layout
        layout.addWidget(self.label)
        layout.addWidget(self.text_edit)
        layout.addWidget(self.button_box)

        # Connections
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

    def get_feedback_text(self) -> str:
        """
        Возвращает текст, введенный пользователем.

        Returns:
            Строка с текстом обратной связи.
        """
        return self.text_edit.toPlainText().strip()

