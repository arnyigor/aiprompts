# ui/prompt_editor.py
import logging

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QTextEdit, QVBoxLayout, QLabel, QLineEdit, QPushButton, \
    QHBoxLayout, QListWidget, QListWidgetItem, QTabWidget, QMessageBox, QInputDialog

from models import Variable
from src.prompt_manager import PromptManager


class PromptEditor(QDialog):
    def __init__(self, prompt_manager: PromptManager, prompt_id=None):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.prompt_manager = prompt_manager
        self.prompt_id = prompt_id
        self.setWindowTitle("Редактор промпта")
        self.setGeometry(200, 200, 600, 400)

        # Поля формы
        self.title_field = QLineEdit()
        self.description_field = QTextEdit()  # Единое описание

        # Вкладки для контента
        self.content_tabs = QTabWidget()
        self.content_ru = QTextEdit()
        self.content_en = QTextEdit()
        self.content_tabs.addTab(self.content_ru, "RU контент")
        self.content_tabs.addTab(self.content_en, "EN контент")

        self.category_field = QLineEdit()
        self.tags_field = QLineEdit()
        self.variables_list = QListWidget()
        self.add_variable_btn = QPushButton("Добавить переменную")
        self.save_btn = QPushButton("Сохранить")

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Название:"))
        layout.addWidget(self.title_field)
        layout.addWidget(QLabel("Описание:"))
        layout.addWidget(self.description_field)
        layout.addWidget(QLabel("Контент:"))
        layout.addWidget(self.content_tabs)
        layout.addWidget(QLabel("Категория:"))
        layout.addWidget(self.category_field)
        layout.addWidget(QLabel("Теги (через запятую):"))
        layout.addWidget(self.tags_field)

        # Блок с переменными
        variables_layout = QHBoxLayout()
        variables_layout.addWidget(self.variables_list)
        variables_layout.addWidget(self.add_variable_btn)
        layout.addLayout(variables_layout)
        layout.addWidget(self.save_btn)

        self.setLayout(layout)

        # События
        self.add_variable_btn.clicked.connect(self.add_variable)
        self.save_btn.clicked.connect(self.save_prompt)

        if self.prompt_id:
            self.load_prompt_data()

    def load_prompt_data(self):
        """Загрузка данных существующего промпта"""
        self.logger.info(f"Загрузка промпта: {self.prompt_id}")

        # Получаем промпт через менеджер
        prompt = self.prompt_manager.get_prompt(self.prompt_id)

        if not prompt:
            self.logger.error("Промпт не найден")
            QMessageBox.warning(self, "Ошибка", "Промпт не существует")
            return

        # Добавляем в кеш
        # self.prompt_manager.prompts[self.prompt_id] = prompt - ошибка!!!!

        self.title_field.setText(prompt.title)
        self.description_field.setText(prompt.description)

        # Заполнение контента
        if 'ru' in prompt.content:
            self.content_ru.setText(prompt.content['ru'])
        if 'en' in prompt.content:
            self.content_en.setText(prompt.content['en'])

        self.category_field.setText(prompt.category)
        self.tags_field.setText(", ".join(prompt.tags))

        # Переменные
        self.variables_list.clear()
        for var in prompt.variables:
            item = QListWidgetItem(f"{var.name} ({var.type}): {var.description}")
            item.setData(Qt.ItemDataRole.UserRole, var)
            self.variables_list.addItem(item)

    def save_prompt(self):
        try:
            """Сохранение промпта с мультиязычным контентом"""
            variables = []
            for i in range(self.variables_list.count()):
                var_data = self.variables_list.item(i).data(Qt.ItemDataRole.UserRole)
                variables.append(Variable(**var_data))

            prompt_data = {
                "title": self.title_field.text(),
                "description": self.description_field.toPlainText(),
                "content": {  # Теперь словарь с языками
                    "ru": self.content_ru.toPlainText(),
                    "en": self.content_en.toPlainText()
                },
                "category": self.category_field.text(),
                "tags": [t.strip() for t in self.tags_field.text().split(",")],
                "variables": variables,
                "ai_model": "gpt-3"
            }

            if self.prompt_id:
                self.prompt_manager.edit_prompt(self.prompt_id, prompt_data)
            else:
                self.prompt_manager.add_prompt(prompt_data)

            self.accept()
        except Exception as e:
            self.logger.error(f"Ошибка сохранения промпта {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", str(e))

    def add_variable(self):
        """Добавление новой переменной через диалог"""
        name, ok = QInputDialog.getText(self, "Переменная", "Имя переменной:")
        if not ok or not name:
            return

        var_type, ok = QInputDialog.getItem(
            self,
            "Тип переменной",
            "Выберите тип:",
            ["string", "number", "list"],
            editable=False
        )
        if not ok:
            return

        description, ok = QInputDialog.getText(self, "Описание", "Введите описание:")
        if not ok:
            return

        examples = []
        if var_type == "list":
            examples_input, ok = QInputDialog.getText(
                self,
                "Примеры",
                "Введите примеры через запятую:"
            )
            if ok:
                examples = [ex.strip() for ex in examples_input.split(",")]

        var_data = {
            "name": name,
            "type": var_type,
            "description": description,
            "examples": examples
        }

        item = QListWidgetItem(f"{name} ({var_type}): {description}")
        item.setData(Qt.ItemDataRole.UserRole, var_data)
        self.variables_list.addItem(item)
