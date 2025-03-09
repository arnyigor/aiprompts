# preview.py
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import (QDialog, QTextEdit, QVBoxLayout, QLabel,
                             QPushButton, QHBoxLayout, QMessageBox)


class PromptPreview(QDialog):
    def __init__(self, prompt):
        super().__init__()
        self.prompt = prompt
        self.setWindowTitle("Предпросмотр промпта")
        self.setGeometry(300, 300, 800, 600)

        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout()

        # Header
        self.title_label = QLabel()
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(self.title_label)

        # Metadata
        self.meta_layout = QHBoxLayout()
        self.category_label = QLabel()
        self.tags_label = QLabel()
        self.model_label = QLabel()
        self.meta_layout.addWidget(self.category_label)
        self.meta_layout.addWidget(self.tags_label)
        self.meta_layout.addWidget(self.model_label)
        layout.addLayout(self.meta_layout)

        # Content
        self.content_edit = QTextEdit()
        self.content_edit.setReadOnly(True)
        layout.addWidget(QLabel("Содержание:"))
        layout.addWidget(self.content_edit)

        # Variables
        self.vars_label = QLabel("Переменные:")
        layout.addWidget(self.vars_label)
        self.vars_text = QTextEdit()
        self.vars_text.setReadOnly(True)
        layout.addWidget(self.vars_text)

        # Buttons
        button_layout = QHBoxLayout()
        self.copy_content_btn = QPushButton("Копировать контент")
        self.copy_full_btn = QPushButton("Копировать всё")
        self.close_btn = QPushButton("Закрыть")

        self.copy_content_btn.clicked.connect(self.copy_content)
        self.copy_full_btn.clicked.connect(self.copy_full)
        self.close_btn.clicked.connect(self.close)

        button_layout.addWidget(self.copy_content_btn)
        button_layout.addWidget(self.copy_full_btn)
        button_layout.addWidget(self.close_btn)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def load_data(self):
        """Загрузка данных промпта"""
        self.title_label.setText(self.prompt.title)
        self.category_label.setText(f"Категория: {self.prompt.category}")
        self.tags_label.setText(f"Теги: {', '.join(self.prompt.tags)}")
        self.model_label.setText(f"AI модель: {self.prompt.ai_model}")

        # Content with language tabs
        content_text = "\n\n".join(
            f"{text}"
            for lang, text in self.prompt.content.items()
            if text.strip()
        )
        self.content_edit.setPlainText(content_text)

        # Variables
        variables = "\n".join(
            f"• {var.name} ({var.type}) - {var.description}\nПримеры: {', '.join(var.examples)}"
            for var in self.prompt.variables
        )
        self.vars_text.setPlainText(variables or "Нет переменных")

    def copy_content(self):
        """Копирование основного контента"""
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(self.content_edit.toPlainText())
        self.show_toast("Контент скопирован в буфер!")

    def copy_full(self):
        """Копирование полной информации"""
        text = f"""Промпт: {self.prompt.title}
        Категория: {self.prompt.category}
        Теги: {', '.join(self.prompt.tags)}
        Модель: {self.prompt.ai_model}
        
        Контент:
        {self.content_edit.toPlainText()}
        
        Переменные:
        {self.vars_text.toPlainText()}"""

        clipboard = QGuiApplication.clipboard()
        clipboard.setText(text)
        self.show_toast("Полный текст скопирован!")

    def show_toast(self, message):
        """Всплывающее уведомление"""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setText(message)
        msg.setWindowTitle(" ")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.show()
        QTimer.singleShot(1500, msg.close)
