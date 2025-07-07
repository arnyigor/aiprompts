import logging
import re
import sys
from typing import List

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor
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
    QComboBox, QCheckBox, QDoubleSpinBox, QSpinBox, QGroupBox, QWidget, QFormLayout,
    QMenu
)

from src.MarkdownPreviewDialog import MarkdownPreviewDialog
from src.category_manager import CategoryManager
from src.huggingface_api import HuggingFaceAPI
from src.huggingface_dialog import HuggingFaceDialog
from src.lmstudio_api import LMStudioInference
from src.lmstudio_dialog import LMStudioDialog
from src.model_dialog import ModelConfigDialog
from src.models import Variable
from src.prompt_manager import PromptManager
from src.llm_settings import Settings


class JsonPreviewDialog(QDialog):
    """Диалог для предпросмотра JSON"""

    def __init__(self, json_text, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Предпросмотр JSON")
        self.setGeometry(300, 300, 600, 800)

        layout = QVBoxLayout()

        # Текстовое поле для JSON
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setPlainText(json_text)

        # Кнопка закрытия
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)

        layout.addWidget(self.text_edit)
        layout.addWidget(close_btn)

        self.setLayout(layout)


class VariableDialog(QDialog):
    """Диалог для создания/редактирования переменной"""

    def __init__(self, variable_text="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Редактирование переменной")
        self.setup_ui(variable_text)

    def setup_ui(self, variable_text):
        layout = QVBoxLayout()

        # Имя переменной
        name_layout = QHBoxLayout()
        name_label = QLabel("Имя переменной:")
        self.name_field = QLineEdit()
        self.name_field.setPlaceholderText("Только латинские буквы")
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_field)

        # Тип переменной
        type_layout = QHBoxLayout()
        type_label = QLabel("Тип:")
        self.type_combo = QComboBox()
        self.type_combo.addItems(["string", "number", "list"])
        type_layout.addWidget(type_label)
        type_layout.addWidget(self.type_combo)

        # Описание
        description_label = QLabel("Описание:")
        self.description_field = QTextEdit()
        self.description_field.setPlainText(variable_text)
        self.description_field.setMaximumHeight(100)

        # Примеры
        examples_label = QLabel("Примеры (через запятую):")
        self.examples_field = QLineEdit()

        # Кнопки
        buttons = QHBoxLayout()
        save_btn = QPushButton("Сохранить")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)

        # Добавляем все в основной layout
        layout.addLayout(name_layout)
        layout.addLayout(type_layout)
        layout.addWidget(description_label)
        layout.addWidget(self.description_field)
        layout.addWidget(examples_label)
        layout.addWidget(self.examples_field)
        layout.addLayout(buttons)

        self.setLayout(layout)

    def get_variable(self) -> Variable:
        """Получить объект Variable из заполненных полей"""
        try:
            name = self.name_field.text().strip()
            var_type = self.type_combo.currentText()
            description = self.description_field.toPlainText().strip()
            examples = [ex.strip() for ex in self.examples_field.text().split(",") if ex.strip()]

            return Variable(
                name=name,
                type=var_type,
                description=description,
                examples=examples
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось создать переменную: {str(e)}"
            )
            return None

    def set_variable(self, variable: Variable):
        """Заполнить поля данными из объекта Variable"""
        self.name_field.setText(variable.name)
        index = self.type_combo.findText(variable.type)
        if index >= 0:
            self.type_combo.setCurrentIndex(index)
        self.description_field.setPlainText(variable.description)
        if variable.examples:
            self.examples_field.setText(", ".join(variable.examples))


class ExampleSelectionDialog(QDialog):
    """Диалог для выбора примеров переменной"""

    def __init__(self, variable: Variable, parent=None):
        super().__init__(parent)
        self.variable = variable
        self.selected_examples = []
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Выбор примеров")
        layout = QVBoxLayout()

        # Информация о переменной
        info_text = f"Переменная: {self.variable.name} ({self.variable.type})\n{self.variable.description}"
        info_label = QLabel(info_text)
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Список примеров
        self.examples_list = QListWidget()
        self.examples_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        for example in self.variable.examples:
            item = QListWidgetItem(str(example))
            self.examples_list.addItem(item)
        layout.addWidget(self.examples_list)

        # Кнопки
        buttons = QHBoxLayout()
        insert_btn = QPushButton("Вставить")
        insert_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(insert_btn)
        buttons.addWidget(cancel_btn)

        layout.addLayout(buttons)
        self.setLayout(layout)

    def get_selected_examples(self) -> List[str]:
        """Получить выбранные примеры"""
        return [item.text() for item in self.examples_list.selectedItems()]


class PromptEditor(QDialog):
    def __init__(self, prompt_manager: PromptManager, settings: Settings, prompt_id=None):
        super().__init__()

        # Базовая инициализация
        self.logger = logging.getLogger(__name__)
        self.settings = settings
        try:
            self.hf_api = HuggingFaceAPI(settings=self.settings)
        except Exception as e:
            self.logger.error(f"Ошибка инициализации HuggingFaceAPI: {str(e)}", exc_info=True)
            self.hf_api = None

        try:
            self.lm_api = LMStudioInference()
        except Exception as e:
            self.logger.error(f"Ошибка инициализации LMStudioInference: {str(e)}", exc_info=True)
            self.lm_api = None

        self.prompt_manager = prompt_manager
        self.prompt_id = prompt_id
        self.cat_manager = CategoryManager()

        # Инициализация UI элементов
        self.title_field = QLineEdit()
        self.version_field = QLineEdit()
        self.status_selector = QComboBox()
        self.description_field = QTextEdit()
        self.is_local_checkbox = QCheckBox("Локальный промпт")
        self.is_favorite_checkbox = QCheckBox("Добавить в избранное")
        self.rating_score = QDoubleSpinBox()
        self.rating_votes = QSpinBox()
        self.content_tabs = QTabWidget()
        self.content_ru = QTextEdit()
        self.content_en = QTextEdit()
        self.ru_system_prompt = QTextEdit()
        self.ru_user_prompt = QTextEdit()
        self.en_system_prompt = QTextEdit()
        self.en_user_prompt = QTextEdit()
        self.result_ru = QTextEdit()
        self.result_en = QTextEdit()
        self.category_selector = QComboBox()
        self.analyze_btn = QPushButton("Определить категорию")
        self.models_group = QGroupBox("Совместимые модели")
        self.models_list = QListWidget()
        self.tags_field = QLineEdit()
        self.variables_group = QGroupBox("Переменные")
        self.variables_list = QListWidget()
        self.metadata_group = QGroupBox("Метаданные")
        self.author_id_field = QLineEdit()
        self.author_name_field = QLineEdit()
        self.source_field = QLineEdit()
        self.notes_field = QTextEdit()
        self.save_btn = QPushButton("Сохранить")
        self.save_btn.clicked.connect(self.save_prompt)
        # Настройка базовых полей
        self.setup_basic_info()

        # Настройка окна
        self.setWindowTitle("Редактор промпта")
        self.setGeometry(200, 200, 800, 800)

        # Добавляем вкладки верхнего уровня
        self.main_tabs = QTabWidget()

        # Добавляем поле предпросмотра JSON
        self.json_preview = QTextEdit()
        self.json_preview.setReadOnly(True)

        # Настройка UI
        self.setup_ui()

        # Загрузка данных если редактируем существующий промпт
        if self.prompt_id:
            self.load_prompt_data()

    def setup_basic_info(self):
        """Настройка базовых полей"""
        # Версия по умолчанию
        self.version_field.setText("1.0.0")

        # Статусы
        self.status_selector.clear()
        self.status_selector.addItems([
            "active",
            "draft",
            "archived",
            "deprecated"
        ])
        self.status_selector.setCurrentText("draft")  # По умолчанию

    def setup_ui(self):
        """Настройка пользовательского интерфейса"""
        main_layout = QVBoxLayout()

        # Создаем вкладки
        self.main_tabs = QTabWidget()

        # Создаем все вкладки
        self.create_basic_info_tab()  # Основная информация
        self.create_content_tab()  # Контент
        self.create_metadata_tab()  # Метаданные
        self.create_variables_tab()  # Переменные
        self.create_models_tab()  # Модели

        # Добавляем вкладки в основной layout
        main_layout.addWidget(self.main_tabs)

        # Кнопка предпросмотра JSON
        json_preview_btn = QPushButton("Открыть предпросмотр JSON")
        json_preview_btn.clicked.connect(self.show_json_preview)
        main_layout.addWidget(json_preview_btn)

        # Добавляем кнопки
        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.save_btn)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)
        main_layout.addLayout(buttons_layout)

        self.setLayout(main_layout)

        # Подключаем обновление JSON при изменении любого поля
        self.setup_json_update_triggers()

    def create_metadata_tab(self):
        """Вкладка с метаданными"""
        tab = QWidget()
        layout = QVBoxLayout()

        # Поиск
        search_layout = QHBoxLayout()
        search_field = QLineEdit()
        search_field.setPlaceholderText("Поиск по метаданным...")
        search_layout.addWidget(search_field)

        # Форма метаданных
        form = QFormLayout()
        form.addRow("ID автора:", self.author_id_field)
        form.addRow("Имя автора:", self.author_name_field)
        form.addRow("Источник:", self.source_field)

        # Заметки
        notes_group = QGroupBox("Заметки")
        notes_layout = QVBoxLayout()
        notes_layout.addWidget(self.notes_field)
        notes_group.setLayout(notes_layout)

        layout.addLayout(search_layout)
        layout.addLayout(form)
        layout.addWidget(notes_group)

        tab.setLayout(layout)
        self.main_tabs.addTab(tab, "Метаданные")

    def create_variables_tab(self):
        """Вкладка с переменными"""
        tab = QWidget()
        layout = QVBoxLayout()

        # Кнопка добавления
        add_btn = QPushButton("Добавить переменную")
        add_btn.clicked.connect(self.add_variable)

        # Список переменных
        self.variables_list = QListWidget()
        self.variables_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.variables_list.itemDoubleClicked.connect(self.edit_variable)

        layout.addWidget(add_btn)
        layout.addWidget(self.variables_list)

        tab.setLayout(layout)
        self.main_tabs.addTab(tab, "Переменные")

    def insert_variable(self, text_edit: QTextEdit):
        """Вставка переменной в текстовый редактор"""
        # Получаем список переменных
        variables = []
        for i in range(self.variables_list.count()):
            item = self.variables_list.item(i)
            if item:
                variable = item.data(Qt.ItemDataRole.UserRole)
                if variable:
                    variables.append(variable)

        if not variables:
            QMessageBox.warning(self, "Предупреждение",
                                "Сначала добавьте переменные во вкладке 'Переменные'")
            return

        # Создаем меню с переменными
        menu = QMenu(self)
        for var in variables:
            action = menu.addAction(f"{var.name} ({var.type}): {var.description}")
            action.setData(var)

        # Показываем меню
        action = menu.exec(QCursor.pos())
        if action:
            var = action.data()
            text_edit.insertPlainText(f"[{var.name}]")

    def undo_prompt(self, text_edit: QTextEdit):
        """Откат промпта к предыдущему состоянию"""
        if hasattr(text_edit, 'prompt_history') and text_edit.prompt_history:
            previous_text = text_edit.prompt_history.pop()
            text_edit.setPlainText(previous_text)

    def detect_variables(self, text_edit: QTextEdit):
        """Автоматическое определение переменных в тексте"""
        import re

        text = text_edit.toPlainText()

        # Сначала проверяем только квадратные скобки
        square_brackets = re.finditer(r'\[([^\]]+)\]', text)
        square_vars = [match.group(1).strip() for match in square_brackets]

        # Проверяем, все ли переменные в квадратных скобках уже существуют
        existing_vars = set()
        for i in range(self.variables_list.count()):
            item = self.variables_list.item(i)
            if item:
                var = item.data(Qt.ItemDataRole.UserRole)
                if var:
                    existing_vars.add(var.name)

        # Если все переменные в квадратных скобках уже существуют и других скобок нет
        if all(var in existing_vars for var in square_vars):
            # Проверяем наличие других типов скобок
            other_brackets = re.finditer(r'[\(\{\<]([^\)\}\>]+)[\)\}\>]', text)
            other_vars = [match.group(1).strip() for match in other_brackets]

            if not other_vars:
                QMessageBox.information(self, "Информация", "Все переменные уже добавлены")
                return

        # Паттерн для поиска текста в разных скобках
        patterns = [
            r'\[([^\]]+)\]',  # [...] 
            r'\(([^)]+)\)',  # (...)
            r'\{([^}]+)\}',  # {...}
            r'<([^>]+)>',  # <...>
        ]

        found_vars = []
        for pattern in patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                var_text = match.group(1).strip()
                # Пропускаем переменные, которые уже существуют
                if var_text not in existing_vars:
                    found_vars.append(var_text)

        if not found_vars:
            QMessageBox.information(self, "Информация", "Новые переменные не найдены")
            return

        # Для каждой найденной переменной показываем диалог
        for var_text in found_vars:
            dialog = VariableDialog(var_text, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                variable = dialog.get_variable()
                if variable.name:  # Проверяем, что имя не пустое
                    # Проверяем, что имя содержит только латинские буквы
                    if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', variable.name):
                        QMessageBox.warning(
                            self,
                            "Ошибка",
                            "Имя переменной должно содержать только латинские буквы, цифры и знак подчеркивания"
                        )
                        continue

                    # Проверяем уникальность имени
                    exists = False
                    for i in range(self.variables_list.count()):
                        item = self.variables_list.item(i)
                        if item:
                            var = item.data(Qt.ItemDataRole.UserRole)
                            if var and var.name == variable.name:
                                exists = True
                                break

                    if exists:
                        reply = QMessageBox.question(
                            self,
                            "Переменная существует",
                            f"Переменная {variable.name} уже существует. Обновить?",
                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                        )
                        if reply == QMessageBox.StandardButton.Yes:
                            # Обновляем существующую переменную
                            for i in range(self.variables_list.count()):
                                item = self.variables_list.item(i)
                                if item:
                                    var = item.data(Qt.ItemDataRole.UserRole)
                                    if var and var.name == variable.name:
                                        item.setText(
                                            f"{variable.name} ({variable.type}): {variable.description}")
                                        item.setData(Qt.ItemDataRole.UserRole, variable)
                                        break
                    else:
                        # Добавляем новую переменную
                        item = QListWidgetItem(
                            f"{variable.name} ({variable.type}): {variable.description}")
                        item.setData(Qt.ItemDataRole.UserRole, variable)
                        self.variables_list.addItem(item)

    def add_variable(self):
        """Добавление новой переменной"""
        dialog = VariableDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            variable = dialog.get_variable()
            if variable.name:  # Проверяем, что имя не пустое
                # Проверяем, что имя содержит только латинские буквы
                if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', variable.name):
                    QMessageBox.warning(
                        self,
                        "Ошибка",
                        "Имя переменной должно содержать только латинские буквы, цифры и знак подчеркивания"
                    )
                    return

                # Проверяем уникальность имени
                for i in range(self.variables_list.count()):
                    item = self.variables_list.item(i)
                    if item:
                        var = item.data(Qt.ItemDataRole.UserRole)
                        if var and var.name == variable.name:
                            QMessageBox.warning(
                                self,
                                "Ошибка",
                                f"Переменная с именем {variable.name} уже существует"
                            )
                            return

                # Добавляем новую переменную
                item = QListWidgetItem(f"{variable.name} ({variable.type}): {variable.description}")
                item.setData(Qt.ItemDataRole.UserRole, variable)
                self.variables_list.addItem(item)

    def edit_variable(self, item: QListWidgetItem):
        """Редактирование переменной"""
        try:
            variable = item.data(Qt.ItemDataRole.UserRole)
            if not variable:
                return

            dialog = VariableDialog(variable.description, self)
            dialog.set_variable(variable)

            if dialog.exec() == QDialog.DialogCode.Accepted:
                updated_variable = dialog.get_variable()
                if not updated_variable:  # Если произошла ошибка при создании переменной
                    return

                if not updated_variable.name:  # Проверяем, что имя не пустое
                    QMessageBox.warning(
                        self,
                        "Ошибка",
                        "Имя переменной не может быть пустым"
                    )
                    return

                # Проверяем, что имя содержит только латинские буквы
                if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', updated_variable.name):
                    QMessageBox.warning(
                        self,
                        "Ошибка",
                        "Имя переменной должно содержать только латинские буквы, цифры и знак подчеркивания"
                    )
                    return

                # Если имя изменилось, проверяем его уникальность
                if updated_variable.name != variable.name:
                    for i in range(self.variables_list.count()):
                        other_item = self.variables_list.item(i)
                        if other_item and other_item != item:
                            var = other_item.data(Qt.ItemDataRole.UserRole)
                            if var and var.name == updated_variable.name:
                                QMessageBox.warning(
                                    self,
                                    "Ошибка",
                                    f"Переменная с именем {updated_variable.name} уже существует"
                                )
                                return

                # Проверяем наличие примеров для списковых переменных
                if updated_variable.type == "list" and not updated_variable.examples:
                    QMessageBox.warning(
                        self,
                        "Ошибка",
                        f"Для списковых переменных необходимо указать примеры"
                    )
                    return

                # Обновляем переменную
                item.setText(
                    f"{updated_variable.name} ({updated_variable.type}): {updated_variable.description}")
                if updated_variable.examples:
                    item.setToolTip(f"Примеры: {', '.join(updated_variable.examples)}")
                item.setData(Qt.ItemDataRole.UserRole, updated_variable)

        except Exception as e:
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось отредактировать переменную: {str(e)}"
            )

    def create_models_tab(self):
        """Вкладка с моделями"""
        tab = QWidget()
        layout = QVBoxLayout()

        # Список моделей с группировкой по провайдерам
        models = {
            "OpenAI": [
                "gpt-4-turbo-preview",
                "gpt-4",
                "gpt-4-32k",
                "gpt-3.5-turbo",
                "gpt-3.5-turbo-16k",
                "dall-e-3",
                "dall-e-2"
            ],
            "Anthropic": [
                "claude-3-opus",
                "claude-3-sonnet",
                "claude-3-haiku",
                "claude-2.1",
                "claude-2.0",
                "claude-instant"
            ],
            "Google": [
                "gemini-pro",
                "gemini-ultra",
                "palm-2"
            ],
            "Meta": [
                "llama-2-70b",
                "llama-2-13b",
                "llama-2-7b"
            ],
            "Mistral AI": [
                "mistral-large",
                "mistral-medium",
                "mistral-small"
            ]
        }

        # Настройка списка моделей
        self.models_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)

        for provider, provider_models in models.items():
            # Добавляем заголовок провайдера
            provider_item = QListWidgetItem(provider)
            provider_item.setFlags(provider_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            provider_item.setBackground(self.palette().alternateBase())
            self.models_list.addItem(provider_item)

            # Добавляем модели провайдера
            for model in provider_models:
                self.models_list.addItem(model)

        layout.addWidget(self.models_list)
        tab.setLayout(layout)
        self.main_tabs.addTab(tab, "Модели")

    def edit_model(self):
        """Редактирование выбранной модели"""
        current_item = self.models_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Предупреждение", "Выберите модель для редактирования")
            return

        # Получаем текущую конфигурацию
        current_config = current_item.data(Qt.ItemDataRole.UserRole)

        # Создаем диалог и заполняем текущими данными
        dialog = ModelConfigDialog(self)
        dialog.name.setText(current_config.get('name', ''))
        provider_index = dialog.provider.findText(current_config.get('provider', ''))
        if provider_index >= 0:
            dialog.provider.setCurrentIndex(provider_index)
        dialog.max_tokens.setValue(current_config.get('max_tokens', 2000))
        dialog.temperature.setValue(current_config.get('temperature', 0.7))

        # Если пользователь подтвердил изменения
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_config = dialog.get_config()
            current_item.setText(f"{new_config['name']} ({new_config['provider']})")
            current_item.setData(Qt.ItemDataRole.UserRole, new_config)

    def delete_model(self):
        """Удаление выбранной модели"""
        current_item = self.models_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Предупреждение", "Выберите модель для удаления")
            return

        # Проверяем, не является ли элемент заголовком провайдера
        if not current_item.data(Qt.Flag.ItemIsSelectable):
            QMessageBox.warning(self, "Предупреждение", "Нельзя удалить заголовок провайдера")
            return

        # Запрашиваем подтверждение
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Вы уверены, что хотите удалить модель {current_item.text()}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.models_list.takeItem(self.models_list.row(current_item))

    def add_model(self):
        """Добавление новой модели"""
        dialog = ModelConfigDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            config = dialog.get_config()

            # Находим нужного провайдера или создаем новую группу
            provider = config['provider']
            provider_found = False

            for i in range(self.models_list.count()):
                item = self.models_list.item(i)
                if item.text() == provider:
                    provider_found = True
                    insert_index = i + 1
                    # Ищем конец группы этого провайдера
                    while (insert_index < self.models_list.count() and
                           self.models_list.item(insert_index).data(Qt.ItemDataRole.UserRole)):
                        insert_index += 1
                    break

            # Если провайдер не найден, добавляем новую группу в конец
            if not provider_found:
                provider_item = QListWidgetItem(provider)
                provider_item.setFlags(provider_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
                provider_item.setBackground(self.palette().alternateBase())
                self.models_list.addItem(provider_item)
                insert_index = self.models_list.count()

            # Добавляем новую модель
            new_item = QListWidgetItem(f"{config['name']} ({config['provider']})")
            new_item.setData(Qt.ItemDataRole.UserRole, config)
            self.models_list.insertItem(insert_index, new_item)

    def validate_data(self) -> bool:
        """Проверка корректности данных"""
        if not self.title_field.text().strip():
            QMessageBox.warning(self, "Ошибка", "Название не может быть пустым")
            return False

        # Проверяем наличие пользовательского промпта хотя бы на одном языке
        if not (
                self.ru_user_prompt.toPlainText().strip() or self.en_user_prompt.toPlainText().strip()):
            QMessageBox.warning(self, "Ошибка",
                                "Должен быть заполнен хотя бы один язык пользовательского промпта")
            return False

        if not self.category_selector.currentData():
            QMessageBox.warning(self, "Ошибка", "Необходимо выбрать категорию")
            return False

        return True

    def create_basic_info_tab(self):
        """Вкладка с основной информацией"""
        tab = QWidget()
        layout = QVBoxLayout()

        # Базовые поля
        form_layout = QFormLayout()
        # Устанавливаем политику роста полей, чтобы они растягивались по ширине.
        # Это сделает поведение на macOS таким же, как на Windows.
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form_layout.addRow("Название:", self.title_field)
        form_layout.addRow("Версия:", self.version_field)
        form_layout.addRow("Статус:", self.status_selector)
        form_layout.addRow("Описание:", self.description_field)

        # Флаги и рейтинг
        flags_rating = self.setup_flags_and_rating()

        layout.addLayout(form_layout)
        layout.addLayout(flags_rating)
        tab.setLayout(layout)
        # Ограничиваем высоту описания
        self.description_field.setMaximumHeight(60)
        self.description_field.setPlaceholderText("Краткое описание промпта...")
        self.main_tabs.addTab(tab, "Основное")

    def setup_json_update_triggers(self):
        """Подключение сигналов для обновления JSON"""
        # Основная информация
        self.title_field.textChanged.connect(self.update_json_preview)
        self.version_field.textChanged.connect(self.update_json_preview)
        self.status_selector.currentTextChanged.connect(self.update_json_preview)
        self.description_field.textChanged.connect(self.update_json_preview)
        self.is_local_checkbox.stateChanged.connect(self.update_json_preview)
        self.is_favorite_checkbox.stateChanged.connect(self.update_json_preview)
        self.rating_score.valueChanged.connect(self.update_json_preview)
        self.rating_votes.valueChanged.connect(self.update_json_preview)

        # Контент
        self.ru_system_prompt.textChanged.connect(self.update_json_preview)
        self.ru_user_prompt.textChanged.connect(self.update_json_preview)
        self.en_system_prompt.textChanged.connect(self.update_json_preview)
        self.en_user_prompt.textChanged.connect(self.update_json_preview)
        self.category_selector.currentIndexChanged.connect(self.update_json_preview)
        self.tags_field.textChanged.connect(self.update_json_preview)

        # Метаданные
        self.author_id_field.textChanged.connect(self.update_json_preview)
        self.author_name_field.textChanged.connect(self.update_json_preview)
        self.source_field.textChanged.connect(self.update_json_preview)
        self.notes_field.textChanged.connect(self.update_json_preview)

        # Переменные
        self.variables_list.model().rowsInserted.connect(self.update_json_preview)
        self.variables_list.model().rowsRemoved.connect(self.update_json_preview)
        self.variables_list.itemChanged.connect(self.update_json_preview)

    def update_json_preview(self):
        """Обновление предпросмотра JSON"""
        try:
            import json
            data = self.get_current_prompt_data()
            formatted_json = json.dumps(data, indent=2, ensure_ascii=False)
            self.json_preview.setPlainText(formatted_json)
        except Exception as e:
            self.logger.error(f"Ошибка формирования JSON: {str(e)}", exc_info=True)
            self.json_preview.setPlainText(f"Ошибка формирования JSON: {str(e)}")

    def setup_flags_and_rating(self):
        """Настройка флагов и рейтинга"""
        flags_rating_layout = QHBoxLayout()

        # Чекбоксы
        checkbox_layout = QVBoxLayout()
        self.is_local_checkbox.setChecked(True)
        checkbox_layout.addWidget(self.is_local_checkbox)
        checkbox_layout.addWidget(self.is_favorite_checkbox)

        # Рейтинг
        rating_layout = QHBoxLayout()
        self.rating_score.setRange(0, 5)
        self.rating_score.setSingleStep(0.5)
        self.rating_votes.setRange(0, 9999)
        rating_layout.addWidget(QLabel("Рейтинг:"))
        rating_layout.addWidget(self.rating_score)
        rating_layout.addWidget(QLabel("Голосов:"))
        rating_layout.addWidget(self.rating_votes)

        flags_rating_layout.addLayout(checkbox_layout)
        flags_rating_layout.addLayout(rating_layout)

        return flags_rating_layout

    def setup_models_section(self):
        """Настройка секции моделей"""
        models_layout = QVBoxLayout()
        self.models_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)

        models = {
            "OpenAI": [
                "gpt-4-turbo-preview",
                "gpt-4",
                "gpt-4-32k",
                "gpt-3.5-turbo",
                "gpt-3.5-turbo-16k",
                "dall-e-3",
                "dall-e-2"
            ],
            "Anthropic": [
                "claude-3-opus",
                "claude-3-sonnet",
                "claude-3-haiku",
                "claude-2.1",
                "claude-2.0",
                "claude-instant"
            ],
            "Google": [
                "gemini-pro",
                "gemini-ultra",
                "palm-2"
            ],
            "Meta": [
                "llama-2-70b",
                "llama-2-13b",
                "llama-2-7b"
            ],
            "Mistral AI": [
                "mistral-large",
                "mistral-medium",
                "mistral-small"
            ]
        }

        for provider, provider_models in models.items():
            provider_item = QListWidgetItem(provider)
            provider_item.setFlags(provider_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            provider_item.setBackground(self.palette().alternateBase())
            self.models_list.addItem(provider_item)

            # Добавляем модели провайдера
            for model in provider_models:
                self.models_list.addItem(model)

        self.models_list.setMaximumHeight(200)
        models_layout.addWidget(self.models_list)
        self.models_group.setLayout(models_layout)

    def create_content_tab(self):
        """Вкладка с контентом"""
        tab = QWidget()
        layout = QVBoxLayout()

        # Добавляем вкладки для контента
        self.content_tabs = QTabWidget()
        self.setup_content_tabs()  # Настраиваем вкладки RU и EN
        layout.addWidget(self.content_tabs)

        # Категория
        category_layout = self.setup_category_section()
        layout.addLayout(category_layout)

        tab.setLayout(layout)
        self.main_tabs.addTab(tab, "Контент")

    def setup_category_section(self):
        """Настройка секции категорий и тегов"""
        layout = QVBoxLayout()

        # Категории
        category_layout = QHBoxLayout()
        category_layout.addWidget(QLabel("Категория:"))

        # Заполняем категории второго уровня (дети general)
        self.category_selector.clear()
        categories = self.cat_manager.get_categories()

        # Выбираем категории, которые являются детьми general
        main_categories = {
            code: cat for code, cat in categories.items()
            if cat["parent"] == "general"
        }

        # Добавляем также general как основную категорию
        if "general" in categories:
            main_categories["general"] = categories["general"]

        # Сортируем категории по имени
        sorted_categories = sorted(
            main_categories.items(),
            key=lambda x: x[1]["name"]["ru"]
        )

        for code, cat in sorted_categories:
            self.category_selector.addItem(cat["name"]["ru"], code)

        category_layout.addWidget(self.category_selector)
        layout.addLayout(category_layout)

        # Теги
        tags_layout = QVBoxLayout()
        tags_layout.addWidget(QLabel("Теги:"))

        # Поле для тегов
        self.tags_field = QLineEdit()
        self.tags_field.setPlaceholderText("Теги через запятую...")
        tags_layout.addWidget(self.tags_field)

        # Список доступных тегов
        tags_list = QListWidget()
        tags_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        tags_list.setMaximumHeight(150)

        # Собираем все дочерние категории для тегов
        all_child_tags = set()
        for code, cat in categories.items():
            if cat["parent"] and cat[
                "parent"] != "general":  # Исключаем general и его прямых потомков
                # Добавляем код категории как тег
                all_child_tags.add(code)
                # Добавляем дочерние элементы
                all_child_tags.update(cat.get("children", []))

        # Сортируем теги
        sorted_tags = sorted(all_child_tags)
        for tag in sorted_tags:
            # Получаем локализованное имя тега, если это категория
            if tag in categories:
                tag_name = categories[tag]["name"]["ru"]
            else:
                tag_name = tag
            item = QListWidgetItem(tag_name)
            item.setData(Qt.ItemDataRole.UserRole, tag)  # Сохраняем оригинальный код тега
            tags_list.addItem(item)

        # Обработчик клика по тегу
        def on_tag_clicked(item):
            current_tags = [t.strip() for t in self.tags_field.text().split(",") if t.strip()]
            new_tag = item.data(Qt.ItemDataRole.UserRole)  # Используем код тега
            if new_tag not in current_tags:
                if current_tags:
                    self.tags_field.setText(f"{', '.join(current_tags)}, {new_tag}")
                else:
                    self.tags_field.setText(new_tag)

        tags_list.itemClicked.connect(on_tag_clicked)
        tags_layout.addWidget(tags_list)

        layout.addLayout(tags_layout)

        # Кнопка анализа
        self.analyze_btn = QPushButton("Определить категорию")
        self.analyze_btn.clicked.connect(self.analyze_content)
        layout.addWidget(self.analyze_btn)

        return layout

    def analyze_content(self):
        """Анализ контента для определения категории"""
        # Собираем весь текст из промптов
        ru_text = (self.ru_system_prompt.toPlainText() + " " +
                   self.ru_user_prompt.toPlainText())
        en_text = (self.en_system_prompt.toPlainText() + " " +
                   self.en_user_prompt.toPlainText())

        text = ru_text + " " + en_text

        # Получаем предложения по категории
        suggestions = self.cat_manager.suggest(text)

        if suggestions:
            category_code = suggestions[0]
            index = self.category_selector.findData(category_code)
            if index >= 0:
                self.category_selector.setCurrentIndex(index)
                QMessageBox.information(self, "Информация",
                                        f"Предложенная категория: {self.category_selector.currentText()}")
            else:
                QMessageBox.information(self, "Информация", "Нет подходящей категории")
        else:
            QMessageBox.information(self, "Информация", "Категория не определена")

    def setup_content_tabs(self):
        """Настройка вкладок контента"""
        # Русская вкладка
        ru_container = QWidget()
        ru_layout = QVBoxLayout()

        # Промпт на русском
        ru_prompt_group = QGroupBox("Промпт")
        ru_prompt_layout = QVBoxLayout()

        # Кнопки для работы с переменными
        ru_var_buttons = QHBoxLayout()

        ru_find_var_btn = QPushButton("Найти переменные")
        ru_find_var_btn.clicked.connect(lambda: self.detect_variables(self.ru_user_prompt))

        ru_insert_var_btn = QPushButton("Вставить переменную")
        ru_insert_var_btn.clicked.connect(lambda: self.insert_variable(self.ru_user_prompt))

        ru_var_buttons.addWidget(ru_find_var_btn)
        ru_var_buttons.addWidget(ru_insert_var_btn)
        ru_prompt_layout.addLayout(ru_var_buttons)

        # Поле ввода пользовательского промпта
        self.ru_user_prompt = QTextEdit()
        self.ru_user_prompt.setPlaceholderText("Введите промпт на русском...")
        ru_prompt_layout.addWidget(self.ru_user_prompt)
        ru_prompt_group.setLayout(ru_prompt_layout)

        # Результат на русском
        ru_result_group = QGroupBox("Результат")
        ru_result_layout = QVBoxLayout()
        self.result_ru = QTextEdit()
        self.result_ru.setReadOnly(True)
        self.result_ru.setPlaceholderText("Здесь появится результат обработки...")
        ru_result_layout.addWidget(self.result_ru)
        ru_result_group.setLayout(ru_result_layout)

        # Кнопки для русской версии
        ru_buttons = QHBoxLayout()

        ru_preview_btn = QPushButton("👁️ Просмотр")
        ru_preview_btn.setToolTip("Просмотреть как Markdown")
        ru_preview_btn.clicked.connect(lambda: self.show_markdown_preview("ru"))

        # Кнопки Hugging Face
        if self.hf_api:
            ru_hf_btn = QPushButton("Выполнить через Hugging Face")
            ru_hf_btn.clicked.connect(lambda: self.show_huggingface_dialog("ru"))
        else:
            ru_hf_btn = QPushButton("Выполнить через Hugging Face")
            ru_hf_btn.setEnabled(False)
            ru_hf_btn.setToolTip("API Hugging Face недоступен")

        # Кнопка LMStudio
        ru_lm_btn = QPushButton("Выполнить через LMStudio")
        ru_lm_btn.clicked.connect(lambda: self.show_lmstudio_dialog("ru"))
        if not self.lm_api:
            ru_lm_btn.setEnabled(False)
            ru_lm_btn.setToolTip("LMStudio API недоступен")

        ru_copy_btn = QPushButton("Копировать результат в промпт")
        ru_copy_btn.clicked.connect(lambda: self.copy_result_to_prompt("ru"))
        ru_clear_btn = QPushButton("Очистить")
        ru_clear_btn.clicked.connect(lambda: self.clear_content("ru"))

        ru_buttons.addWidget(ru_preview_btn)
        ru_buttons.addWidget(ru_hf_btn)
        ru_buttons.addWidget(ru_lm_btn)
        ru_buttons.addWidget(ru_copy_btn)
        ru_buttons.addWidget(ru_clear_btn)

        ru_layout.addWidget(ru_prompt_group)
        ru_layout.addWidget(ru_result_group)
        ru_layout.addLayout(ru_buttons)
        ru_container.setLayout(ru_layout)

        # Английский контент
        en_container = QWidget()
        en_layout = QVBoxLayout()

        # Промпт на английском
        en_prompt_group = QGroupBox("Prompt")
        en_prompt_layout = QVBoxLayout()

        # Кнопки для работы с переменными
        en_var_buttons = QHBoxLayout()

        en_find_var_btn = QPushButton("Find Variables")
        en_find_var_btn.clicked.connect(lambda: self.detect_variables(self.en_user_prompt))

        en_insert_var_btn = QPushButton("Insert Variable")
        en_insert_var_btn.clicked.connect(lambda: self.insert_variable(self.en_user_prompt))

        en_var_buttons.addWidget(en_find_var_btn)
        en_var_buttons.addWidget(en_insert_var_btn)
        en_prompt_layout.addLayout(en_var_buttons)

        # Поле ввода пользовательского промпта
        self.en_user_prompt = QTextEdit()
        self.en_user_prompt.setPlaceholderText("Enter your prompt...")
        en_prompt_layout.addWidget(self.en_user_prompt)
        en_prompt_group.setLayout(en_prompt_layout)

        # Результат на английском
        en_result_group = QGroupBox("Result")
        en_result_layout = QVBoxLayout()
        self.result_en = QTextEdit()
        self.result_en.setReadOnly(True)
        self.result_en.setPlaceholderText("Processing result will appear here...")
        en_result_layout.addWidget(self.result_en)
        en_result_group.setLayout(en_result_layout)

        # Кнопки для английской версии
        en_buttons = QHBoxLayout()

        en_preview_btn = QPushButton("👁️ View")
        en_preview_btn.setToolTip("View as Markdown")
        en_preview_btn.clicked.connect(lambda: self.show_markdown_preview("en"))

        # Кнопки Hugging Face
        if self.hf_api:
            en_hf_btn = QPushButton("Execute with Hugging Face")
            en_hf_btn.clicked.connect(lambda: self.show_huggingface_dialog("en"))
        else:
            en_hf_btn = QPushButton("Execute with Hugging Face")
            en_hf_btn.setEnabled(False)
            en_hf_btn.setToolTip("Hugging Face API is not available")

        # Кнопка LMStudio
        en_lm_btn = QPushButton("Execute with LMStudio")
        if  sys.platform != 'darwin':
            en_lm_btn.clicked.connect(lambda: self.show_lmstudio_dialog("en"))
        if not self.lm_api:
            en_lm_btn.setEnabled(False)
            en_lm_btn.setToolTip("LMStudio API is not available")

        en_copy_btn = QPushButton("Copy result to prompt")
        en_copy_btn.clicked.connect(lambda: self.copy_result_to_prompt("en"))
        en_clear_btn = QPushButton("Clear")
        en_clear_btn.clicked.connect(lambda: self.clear_content("en"))

        en_buttons.addWidget(en_preview_btn)
        en_buttons.addWidget(en_hf_btn)
        en_buttons.addWidget(en_lm_btn)
        en_buttons.addWidget(en_copy_btn)
        en_buttons.addWidget(en_clear_btn)

        en_layout.addWidget(en_prompt_group)
        en_layout.addWidget(en_result_group)
        en_layout.addLayout(en_buttons)
        en_container.setLayout(en_layout)

        # Добавляем вкладки
        self.content_tabs.addTab(ru_container, "RU контент")
        self.content_tabs.addTab(en_container, "EN контент")

    def show_markdown_preview(self, lang: str):
        """
        Открывает диалог для просмотра контента в виде отрендеренного Markdown.

        Args:
            lang (str): Язык ('ru' или 'en'), для которого нужно показать просмотр.
        """
        if lang == "ru":
            text_edit = self.ru_user_prompt
            title = f"Просмотр: {self.title_field.text()} (RU)"
        elif lang == "en":
            text_edit = self.en_user_prompt
            title = f"Preview: {self.title_field.text()} (EN)"
        else:
            return  # Неизвестный язык

        markdown_text = text_edit.toPlainText()

        # Создаем и показываем наш новый диалог
        dialog = MarkdownPreviewDialog(markdown_text, window_title=title, parent=self)
        dialog.exec()
    def show_huggingface_dialog(self, language):
        """Показывает диалог Hugging Face и обрабатывает результат"""
        try:
            # Получаем пользовательский промпт
            if language == "ru":
                user_prompt = self.ru_user_prompt.toPlainText()
                result_field = self.result_ru
            else:
                user_prompt = self.en_user_prompt.toPlainText()
                result_field = self.result_en

            if not user_prompt.strip():
                QMessageBox.warning(self, "Предупреждение", "Введите промпт")
                return

            dialog = HuggingFaceDialog(self.hf_api, self.settings, user_prompt, self,
                                       from_preview=False)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                result = dialog.get_result()
                if result:
                    result_field.setPlainText(result)
                    self.logger.debug("Результат успешно добавлен")
                else:
                    self.logger.warning("Получен пустой результат от диалога")
                    QMessageBox.warning(self, "Предупреждение", "Получен пустой результат")
            else:
                self.logger.debug("Диалог был закрыт без сохранения результата")

        except Exception as e:
            self.logger.error(f"Ошибка при открытии диалога: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть диалог: {str(e)}")

    def show_lmstudio_dialog(self, language):
        """Показывает диалог LMStudio и обрабатывает результат"""
        try:
            # Получаем пользовательский промпт
            if language == "ru":
                user_prompt = self.ru_user_prompt.toPlainText()
                result_field = self.result_ru
            else:
                user_prompt = self.en_user_prompt.toPlainText()
                result_field = self.result_en

            if not user_prompt.strip():
                QMessageBox.warning(self, "Предупреждение", "Введите промпт")
                return

            dialog = LMStudioDialog(user_prompt, self, from_preview=False)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                result = dialog.get_result()
                if result:
                    result_field.setPlainText(result)
                    self.logger.debug("Результат успешно добавлен")
                else:
                    self.logger.warning("Получен пустой результат от диалога")
                    QMessageBox.warning(self, "Предупреждение", "Получен пустой результат")
            else:
                self.logger.debug("Диалог был закрыт без сохранения результата")

        except Exception as e:
            self.logger.error(f"Ошибка при открытии диалога LMStudio: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть диалог LMStudio: {str(e)}")

    def copy_result_to_prompt(self, language):
        """Копирование результата в поле промпта"""
        if language == "ru":
            result_text = self.result_ru.toPlainText()
            current_text = self.ru_user_prompt.toPlainText()
            if current_text:
                self.ru_user_prompt.setPlainText(f"{current_text}\n\n{result_text}")
            else:
                self.ru_user_prompt.setPlainText(result_text)
        else:
            result_text = self.result_en.toPlainText()
            current_text = self.en_user_prompt.toPlainText()
            if current_text:
                self.en_user_prompt.setPlainText(f"{current_text}\n\n{result_text}")
            else:
                self.en_user_prompt.setPlainText(result_text)

    def clear_content(self, language):
        """Очистка полей контента"""
        if language == "ru":
            self.ru_system_prompt.clear()
            self.ru_user_prompt.clear()
            self.result_ru.clear()
        else:
            self.en_system_prompt.clear()
            self.en_user_prompt.clear()
            self.result_en.clear()

    def load_prompt_data(self):
        """Загрузка данных существующего промпта"""
        try:
            prompt = self.prompt_manager.get_prompt(self.prompt_id)
            if not prompt:
                return

            # Основная информация
            self.title_field.setText(prompt.title)
            self.version_field.setText(prompt.version)
            self.status_selector.setCurrentText(prompt.status)
            self.is_local_checkbox.setChecked(prompt.is_local)
            self.is_favorite_checkbox.setChecked(prompt.is_favorite)
            self.description_field.setText(prompt.description)

            # Рейтинг
            if hasattr(prompt, 'rating'):
                self.rating_score.setValue(prompt.rating.get('score', 0))
                self.rating_votes.setValue(prompt.rating.get('votes', 0))

            # Контент
            if hasattr(prompt, 'content'):
                if isinstance(prompt.content, dict):
                    # Новый формат (словарь с языками)
                    self.ru_user_prompt.setText(prompt.content.get('ru', ''))
                    self.en_user_prompt.setText(prompt.content.get('en', ''))
                else:
                    # Старый формат (строка)
                    self.ru_user_prompt.setText(str(prompt.content))
                    self.en_user_prompt.clear()

            # Категория
            if prompt.category:
                # Получаем все категории
                categories = self.cat_manager.get_categories()
                category = prompt.category

                # Если категория является подкатегорией, находим её родителя
                if category in categories and categories[category]["parent"] != "general":
                    parent = categories[category]["parent"]
                    if parent and parent != "general":
                        category = parent

                # Ищем индекс категории в селекторе
                index = self.category_selector.findData(category)
                if index >= 0:
                    self.category_selector.setCurrentIndex(index)
                else:
                    # Если категория не найдена, устанавливаем general
                    index = self.category_selector.findData("general")
                if index >= 0:
                    self.category_selector.setCurrentIndex(index)

            # Совместимые модели
            if hasattr(prompt, 'compatible_models'):
                for i in range(self.models_list.count()):
                    item = self.models_list.item(i)
                    if item and item.text() in prompt.compatible_models:
                        item.setSelected(True)

            # Теги
            if prompt.tags:
                self.tags_field.setText(", ".join(prompt.tags))

            # Переменные
            self.variables_list.clear()
            if prompt.variables:
                for var in prompt.variables:
                    item = QListWidgetItem(f"{var.name} ({var.type}): {var.description}")
                    item.setData(Qt.ItemDataRole.UserRole, var)
                    self.variables_list.addItem(item)

            # Метаданные
            if hasattr(prompt, 'metadata'):
                metadata = prompt.metadata
                if isinstance(metadata, dict):
                    author = metadata.get('author', {})
                    self.author_id_field.setText(author.get('id', ''))
                    self.author_name_field.setText(author.get('name', ''))
                    self.source_field.setText(metadata.get('source', ''))
                    self.notes_field.setText(metadata.get('notes', ''))

            # Обновляем предпросмотр JSON
            self.update_json_preview()

        except Exception as e:
            self.logger.error(f"Ошибка при загрузке данных промпта: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить данные промпта: {str(e)}")

    def variable_to_dict(self, var: Variable) -> dict:
        """Конвертация Variable в словарь для JSON"""
        return {
            "name": var.name,
            "type": var.type,
            "description": var.description,
            "examples": var.examples
        }

    def get_current_prompt_data(self) -> dict:
        """Получение текущих данных промпта"""
        # Получаем выбранные модели
        selected_models = []
        for i in range(self.models_list.count()):
            item = self.models_list.item(i)
            if item and item.isSelected():
                # Проверяем, что это не заголовок провайдера
                if item.flags() & Qt.ItemFlag.ItemIsSelectable:
                    selected_models.append(item.text())

        # Формируем контент
        content = {
            "ru": self.ru_user_prompt.toPlainText(),
            "en": self.en_user_prompt.toPlainText()
        }

        # Убедимся, что теги не пустые
        tags = [t.strip() for t in self.tags_field.text().split(",") if t.strip()]
        if not tags:
            tags = ["general"]

        # Получаем переменные и конвертируем их в словари
        variables = []
        for i in range(self.variables_list.count()):
            item = self.variables_list.item(i)
            if item:
                variable = item.data(Qt.ItemDataRole.UserRole)
                if variable:
                    variables.append(self.variable_to_dict(variable))

        # Получаем категорию
        category = self.category_selector.currentData()
        if not category:
            category = "general"

        # Формируем основной словарь данных
        data = {
            "title": self.title_field.text(),
            "version": self.version_field.text(),
            "status": self.status_selector.currentText(),
            "is_local": self.is_local_checkbox.isChecked(),
            "is_favorite": self.is_favorite_checkbox.isChecked(),
            "rating": {
                "score": self.rating_score.value(),
                "votes": self.rating_votes.value()
            },
            "description": self.description_field.toPlainText(),
            "content": content,
            "category": category,
            "tags": tags,
            "variables": variables,
            "metadata": {
                "author": {
                    "id": self.author_id_field.text(),
                    "name": self.author_name_field.text()
                },
                "source": self.source_field.text(),
                "notes": self.notes_field.toPlainText()
            }
        }

        # Добавляем поддерживаемые модели только если они выбраны
        if selected_models:
            data["compatible_models"] = selected_models

        return data

    def save_prompt(self):
        """Сохранение промпта с валидацией"""
        if not self.validate_data():
            return

        try:
            prompt_data = self.get_current_prompt_data()
            if self.prompt_id:
                self.prompt_manager.edit_prompt(self.prompt_id, prompt_data)
            else:
                self.prompt_manager.add_prompt(prompt_data)
            self.accept()
            self.logger.error(f"Промпт: {self.prompt_id} сохранен", exc_info=True)
        except Exception as e:
            self.logger.error(f"Ошибка сохранения: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", str(e))

    def show_info(self, title, message):
        QMessageBox.information(self, title, message)

    def update_api_buttons(self):
        """Обновление кнопок API после изменения ключа"""
        try:
            # Пересоздаем контент с обновленными кнопками
            self.content_tabs.clear()
            self.setup_content_tabs()

        except Exception as e:
            self.logger.error(f"Ошибка при обновлении кнопок API: {str(e)}", exc_info=True)

    def show_json_preview(self):
        """Показать диалог предпросмотра JSON"""
        try:
            import json
            data = self.get_current_prompt_data()
            formatted_json = json.dumps(data, indent=2, ensure_ascii=False)
            dialog = JsonPreviewDialog(formatted_json, self)
            dialog.exec()
        except Exception as e:
            self.logger.error(f"Ошибка формирования JSON: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Ошибка формирования JSON: {str(e)}")

    def show_variable_context_menu(self, position):
        """Показать контекстное меню для переменной"""
        item = self.variables_list.itemAt(position)
        if not item:
            return

        menu = QMenu()
        edit_action = menu.addAction("Редактировать")
        edit_action.triggered.connect(lambda: self.edit_variable(item))
        delete_action = menu.addAction("Удалить")
        delete_action.triggered.connect(lambda: self.delete_variable())

        menu.exec(self.variables_list.viewport().mapToGlobal(position))

    def delete_variable(self):
        """Удаление выбранной переменной"""
        current = self.variables_list.currentItem()
        if current:
            self.variables_list.takeItem(self.variables_list.row(current))
