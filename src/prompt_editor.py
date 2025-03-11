import logging

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QTextEdit,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QTabWidget,
    QMessageBox,
    QComboBox, QInputDialog, QWidget
)

from src.category_manager import CATEGORIES, CategoryManager
from src.huggingface_api import HuggingFaceInference
from src.huggingface_dialog import HuggingFaceDialog
from src.models import Variable
from src.prompt_manager import PromptManager


class PromptEditor(QDialog):
    def __init__(self, prompt_manager: PromptManager, prompt_id=None):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        try:
            self.hf_api = HuggingFaceInference()
        except Exception as e:
            self.logger.error(f"Ошибка инициализации HuggingFaceInference: {str(e)}", exc_info=True)
            raise

        self.prompt_manager = prompt_manager
        self.prompt_id = prompt_id
        self.cat_manager = CategoryManager()
        self.setWindowTitle("Редактор промпта")
        self.setGeometry(200, 200, 800, 600)  # Увеличение размера окна

        self.output_field = QTextEdit()
        self.output_field.setReadOnly(True)
        self.output_field.setMinimumHeight(200)

        # Категории
        self.category_selector = QComboBox()
        self.category_selector.addItem("Общее", "general")
        for code, cat in CATEGORIES.items():
            self.category_selector.addItem(
                cat["name"]["ru"],
                code
            )

        # Поля формы
        self.title_field = QLineEdit()
        self.description_field = QTextEdit()
        self.description_field.setMinimumHeight(30)  # Увеличение поля описания

        # Вкладки контента
        self.content_tabs = QTabWidget()

        # Русская вкладка с контейнером
        ru_container = QWidget()
        ru_layout = QVBoxLayout()
        self.content_ru = QTextEdit()
        self.content_ru.setMinimumHeight(200)
        ru_button_layout = QHBoxLayout()
        self.run_ru_prompt_btn = QPushButton("Выполнить через Hugging Face")
        self.run_ru_prompt_btn.clicked.connect(lambda: self.show_huggingface_dialog("ru"))
        ru_button_layout.addWidget(self.run_ru_prompt_btn)
        ru_layout.addWidget(self.content_ru)
        ru_layout.addLayout(ru_button_layout)
        ru_container.setLayout(ru_layout)

        # Английская вкладка с контейнером
        en_container = QWidget()
        en_layout = QVBoxLayout()
        self.content_en = QTextEdit()
        self.content_en.setMinimumHeight(200)
        en_button_layout = QHBoxLayout()
        self.run_en_prompt_btn = QPushButton("Execute with Hugging Face")
        self.run_en_prompt_btn.clicked.connect(lambda: self.show_huggingface_dialog("en"))
        en_button_layout.addWidget(self.run_en_prompt_btn)
        en_layout.addWidget(self.content_en)
        en_layout.addLayout(en_button_layout)
        en_container.setLayout(en_layout)

        self.content_tabs.addTab(ru_container, "RU контент")
        self.content_tabs.addTab(en_container, "EN контент")

        self.tags_field = QLineEdit()
        self.variables_list = QListWidget()
        self.variables_list.setMinimumHeight(50)
        self.add_variable_btn = QPushButton("Добавить переменную")
        self.save_btn = QPushButton("Сохранить")
        self.analyze_btn = QPushButton("Определить категорию")
        self.analyze_btn.clicked.connect(self.analyze_content)

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Название:"))
        layout.addWidget(self.title_field)
        layout.addWidget(QLabel("Описание:"))
        layout.addWidget(self.description_field)
        layout.addWidget(QLabel("Контент:"))
        layout.addWidget(self.content_tabs)
        layout.addWidget(QLabel("Результат:"))
        layout.addWidget(self.output_field)
        layout.addWidget(QLabel("Категория:"))
        layout.addWidget(self.category_selector)
        layout.addWidget(self.analyze_btn)
        layout.addWidget(QLabel("Теги (через запятую):"))
        layout.addWidget(self.tags_field)

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

    def show_huggingface_dialog(self, language):
        """Показывает диалог Hugging Face и обрабатывает результат"""
        try:
            content_field = self.content_ru if language == "ru" else self.content_en
            current_text = content_field.toPlainText()

            dialog = HuggingFaceDialog(self.hf_api, current_text, self)
            result = dialog.exec()  # Получаем результат выполнения диалога

            # Обновляем текст только если диалог был принят (нажата кнопка "Вернуть результат")
            if result == QDialog.DialogCode.Accepted:
                dialog_result = dialog.get_result()
                if dialog_result:
                    # Добавляем результат в конец текущего текста с разделителем
                    new_text = current_text
                    if new_text:
                        new_text += "\n\n"
                    new_text += dialog_result
                    content_field.setPlainText(new_text)
                    self.logger.debug("Результат успешно добавлен в редактор")
                else:
                    self.logger.warning("Получен пустой результат от диалога")
            else:
                self.logger.debug("Диалог был закрыт без сохранения результата")

        except Exception as e:
            self.logger.error(f"Ошибка при открытии диалога: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть диалог: {str(e)}")

    def get_current_prompt_data(self) -> dict:
        """Формирует данные текущего промпта из полей формы"""
        # Получаем переменные из списка
        variables = []
        for i in range(self.variables_list.count()):
            item = self.variables_list.item(i)
            if item:
                variables.append(item.data(Qt.ItemDataRole.UserRole))

        return {
            "title": self.title_field.text(),
            "description": self.description_field.toPlainText(),
            "content": {
                "ru": self.content_ru.toPlainText(),
                "en": self.content_en.toPlainText()
            },
            "category": self.category_selector.currentData(),
            "tags": [t.strip() for t in self.tags_field.text().split(",") if t.strip()],
            "variables": variables,
            "ai_model": "gpt-3"
        }

    def load_prompt_data(self):
        prompt = self.prompt_manager.get_prompt(self.prompt_id)
        if not prompt:
            return
        self.title_field.setText(prompt.title)
        self.description_field.setText(prompt.description)
        self.content_ru.setText(prompt.content.get('ru', ''))
        self.content_en.setText(prompt.content.get('en', ''))
        self.tags_field.setText(", ".join(prompt.tags))
        # Установка категории
        category_code = prompt.category
        index = self.category_selector.findData(category_code)
        if index >= 0:
            self.category_selector.setCurrentIndex(index)
        # Загрузка переменных
        self.variables_list.clear()
        for var in prompt.variables:
            item = QListWidgetItem(f"{var.name} ({var.type}): {var.description}")
            item.setData(Qt.ItemDataRole.UserRole, var)
            self.variables_list.addItem(item)

    def save_prompt(self):
        try:
            category_code = self.category_selector.currentData()
            variables = []
            for i in range(self.variables_list.count()):
                var_data = self.variables_list.item(i).data(Qt.ItemDataRole.UserRole)
                variables.append(Variable(**var_data))
            prompt_data = {
                "title": self.title_field.text(),
                "description": self.description_field.toPlainText(),
                "content": {
                    "ru": self.content_ru.toPlainText(),
                    "en": self.content_en.toPlainText()
                },
                "category": category_code,
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
            QMessageBox.critical(self, "Ошибка", str(e))

    def analyze_content(self):
        text = self.content_ru.toPlainText() + self.content_en.toPlainText()
        suggestions = self.cat_manager.suggest(text)
        if suggestions:
            category_code = suggestions[0]
            index = self.category_selector.findData(category_code)
            if index >= 0:
                self.category_selector.setCurrentIndex(index)
            else:
                self.show_info("Информация", "Нет подходящей категории")
        else:
            self.show_info("Информация", "Категория не определена")

    def show_info(self, title, message):
        QMessageBox.information(self, title, message)

        # Добавьте этот метод в класс:

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

        description, ok = QInputDialog.getText(
            self,
            "Описание",
            "Введите описание:"
        )
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
