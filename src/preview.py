# preview.py
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import (QDialog, QTextEdit, QVBoxLayout, QLabel,
                             QPushButton, QHBoxLayout, QMessageBox, QWidget, QTabWidget)


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

        # Header с основной информацией
        header_layout = QVBoxLayout()
        self.title_label = QLabel()
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("font-size: 18px; font-weight: bold;")

        self.description_label = QLabel()
        self.description_label.setWordWrap(True)
        self.description_label.setStyleSheet("color: #666;")

        header_layout.addWidget(self.title_label)
        header_layout.addWidget(self.description_label)
        layout.addLayout(header_layout)

        # Metadata
        meta_layout = QVBoxLayout()

        # Первая строка метаданных
        meta_row1 = QHBoxLayout()
        self.version_label = QLabel()
        self.status_label = QLabel()
        self.rating_label = QLabel()
        meta_row1.addWidget(self.version_label)
        meta_row1.addWidget(self.status_label)
        meta_row1.addWidget(self.rating_label)

        # Вторая строка метаданных
        meta_row2 = QHBoxLayout()
        self.category_label = QLabel()
        self.tags_label = QLabel()
        meta_row2.addWidget(self.category_label)
        meta_row2.addWidget(self.tags_label)

        # Третья строка метаданных - даты
        meta_row3 = QHBoxLayout()
        self.created_at_label = QLabel()
        self.updated_at_label = QLabel()
        meta_row3.addWidget(self.created_at_label)
        meta_row3.addWidget(self.updated_at_label)

        meta_layout.addLayout(meta_row1)
        meta_layout.addLayout(meta_row2)
        meta_layout.addLayout(meta_row3)
        layout.addLayout(meta_layout)

        # Поддерживаемые модели
        layout.addWidget(QLabel("Поддерживаемые модели:"))
        self.models_text = QTextEdit()
        self.models_text.setReadOnly(True)
        self.models_text.setMaximumHeight(60)
        layout.addWidget(self.models_text)

        # Content с табами
        layout.addWidget(QLabel("Содержание:"))

        # Создаем табы для контента
        self.content_tabs = QTabWidget()

        # Русский контент
        ru_container = QWidget()
        ru_layout = QVBoxLayout()
        self.ru_content_edit = QTextEdit()
        self.ru_content_edit.setReadOnly(True)
        ru_layout.addWidget(self.ru_content_edit)

        ru_buttons = QHBoxLayout()
        ru_copy_btn = QPushButton("Копировать RU")
        ru_copy_btn.clicked.connect(lambda: self.copy_content("ru"))
        ru_buttons.addWidget(ru_copy_btn)
        ru_layout.addLayout(ru_buttons)

        ru_container.setLayout(ru_layout)
        self.content_tabs.addTab(ru_container, "Русский")

        # Английский контент
        en_container = QWidget()
        en_layout = QVBoxLayout()
        self.en_content_edit = QTextEdit()
        self.en_content_edit.setReadOnly(True)
        en_layout.addWidget(self.en_content_edit)

        en_buttons = QHBoxLayout()
        en_copy_btn = QPushButton("Copy EN")
        en_copy_btn.clicked.connect(lambda: self.copy_content("en"))
        en_buttons.addWidget(en_copy_btn)
        en_layout.addLayout(en_buttons)

        en_container.setLayout(en_layout)
        self.content_tabs.addTab(en_container, "English")

        layout.addWidget(self.content_tabs)

        # Variables
        self.vars_label = QLabel("Переменные:")
        layout.addWidget(self.vars_label)
        self.vars_text = QTextEdit()
        self.vars_text.setReadOnly(True)
        self.vars_text.setMaximumHeight(100)
        layout.addWidget(self.vars_text)

        # Author info
        author_layout = QHBoxLayout()
        self.author_label = QLabel()
        self.source_label = QLabel()
        author_layout.addWidget(self.author_label)
        author_layout.addWidget(self.source_label)
        layout.addLayout(author_layout)

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
        # Основная информация
        self.title_label.setText(self.prompt.title)
        self.description_label.setText(self.prompt.description)

        # Метаданные
        self.version_label.setText(f"Версия: {self.prompt.version}")
        self.status_label.setText(f"Статус: {self.prompt.status}")
        self.rating_label.setText(
            f"Рейтинг: {self.prompt.rating['score']} ({self.prompt.rating['votes']} голосов)"
        )

        self.category_label.setText(f"Категория: {self.prompt.category}")
        self.tags_label.setText(f"Теги: {', '.join(self.prompt.tags)}")

        # Даты создания и изменения
        created_at = self.prompt.created_at.strftime("%d.%m.%Y %H:%M") if self.prompt.created_at else "Не указано"
        updated_at = self.prompt.updated_at.strftime("%d.%m.%Y %H:%M") if self.prompt.updated_at else "Не указано"
        self.created_at_label.setText(f"Создан: {created_at}")
        self.updated_at_label.setText(f"Изменен: {updated_at}")

        # Поддерживаемые модели
        self.models_text.setPlainText(
            ', '.join(
                self.prompt.compatible_models) if self.prompt.compatible_models else "Не указаны"
        )

        # Загружаем контент в табы
        if isinstance(self.prompt.content, dict):
            # Для словаря с языками
            self.ru_content_edit.setPlainText(
                self.prompt.content.get('ru', "Нет русского контента")
            )
            self.en_content_edit.setPlainText(
                self.prompt.content.get('en', "No English content")
            )
        else:
            # Для строкового контента
            self.ru_content_edit.setPlainText(str(self.prompt.content))
            self.en_content_edit.setPlainText("No English content")

        # Variables
        if self.prompt.variables:
            variables = []
            for var in self.prompt.variables:
                var_text = f"• {var.name} ({var.type}) - {var.description}"
                if var.examples:
                    var_text += f"\nПримеры: {', '.join(var.examples)}"
                variables.append(var_text)
            self.vars_text.setPlainText("\n".join(variables))
        else:
            self.vars_text.setPlainText("Нет переменных")

        # Author info
        if hasattr(self.prompt, 'metadata'):
            author = self.prompt.metadata.get('author', {})
            author_name = author.get('name', 'Не указан')
            self.author_label.setText(f"Автор: {author_name}")

            source = self.prompt.metadata.get('source', '')
            if source:
                self.source_label.setText(f"Источник: {source}")
            else:
                self.source_label.hide()

    def copy_content(self, lang=None):
        """Копирование контента определенного языка"""
        clipboard = QGuiApplication.clipboard()

        if lang == "ru":
            text = self.ru_content_edit.toPlainText()
            message = "Русский контент скопирован в буфер!"
        elif lang == "en":
            text = self.en_content_edit.toPlainText()
            message = "English content copied to clipboard!"
        else:
            # Копируем весь контент
            text = []
            ru_content = self.ru_content_edit.toPlainText()
            en_content = self.en_content_edit.toPlainText()

            if ru_content and ru_content != "Нет русского контента":
                text.append(f"Русский:\n{ru_content}")
            if en_content and en_content != "No English content":
                text.append(f"English:\n{en_content}")

            text = "\n\n".join(text)
            message = "Весь контент скопирован в буфер!"

        clipboard.setText(text)
        self.show_toast(message)

    def copy_full(self):
        """Копирование полной информации"""
        text = f"""Промпт: {self.prompt.title}
    Версия: {self.prompt.version}
    Статус: {self.prompt.status}
    Категория: {self.prompt.category}
    Теги: {', '.join(self.prompt.tags)}
    Рейтинг: {self.prompt.rating['score']} ({self.prompt.rating['votes']} голосов)
    Создан: {self.prompt.created_at.strftime("%d.%m.%Y %H:%M") if self.prompt.created_at else "Не указано"}
    Изменен: {self.prompt.updated_at.strftime("%d.%m.%Y %H:%M") if self.prompt.updated_at else "Не указано"}

    Описание:
    {self.prompt.description}

    Поддерживаемые модели:
    {', '.join(self.prompt.compatible_models)}

    Контент:
    Русский:
    {self.ru_content_edit.toPlainText()}

    English:
    {self.en_content_edit.toPlainText()}

    Переменные:
    {self.vars_text.toPlainText()}

    Метаданные:
    Автор: {self.prompt.metadata.get('author', {}).get('name', 'Не указан')}
    Источник: {self.prompt.metadata.get('source', 'Не указан')}
    Заметки: {self.prompt.metadata.get('notes', '')}"""

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
