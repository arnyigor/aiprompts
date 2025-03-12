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
    QComboBox, QInputDialog, QCheckBox, QDoubleSpinBox, QSpinBox, QGroupBox, QWidget, QFormLayout
)

from src.category_manager import CategoryManager
from src.huggingface_api import HuggingFaceInference
from src.huggingface_dialog import HuggingFaceDialog
from src.lmstudio_api import LMStudioInference
from src.lmstudio_dialog import LMStudioDialog
from src.model_dialog import ModelConfigDialog
from src.prompt_manager import PromptManager


class PromptEditor(QDialog):
    def __init__(self, prompt_manager: PromptManager, prompt_id=None):
        super().__init__()

        # Базовая инициализация
        self.logger = logging.getLogger(__name__)
        try:
            self.hf_api = HuggingFaceInference()
        except Exception as e:
            self.logger.error(f"Ошибка инициализации HuggingFaceInference: {str(e)}", exc_info=True)
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

        # Добавляем предпросмотр JSON
        json_group = QGroupBox("Предпросмотр JSON")
        json_layout = QVBoxLayout()
        json_layout.addWidget(self.json_preview)
        json_group.setLayout(json_layout)
        json_group.setMaximumHeight(200)
        main_layout.addWidget(json_group)

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

        # История изменений
        history_group = QGroupBox("История изменений")
        history_layout = QVBoxLayout()
        self.history_list = QListWidget()
        history_layout.addWidget(self.history_list)
        history_group.setLayout(history_layout)

        layout.addLayout(search_layout)
        layout.addLayout(form)
        layout.addWidget(notes_group)
        layout.addWidget(history_group)

        tab.setLayout(layout)
        self.main_tabs.addTab(tab, "Метаданные")

    def create_variables_tab(self):
        """Вкладка с переменными"""
        tab = QWidget()
        layout = QVBoxLayout()

        # Список переменных
        self.variables_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        layout.addWidget(self.variables_list)

        # Кнопки управления
        buttons_layout = QHBoxLayout()

        add_btn = QPushButton("Добавить")
        add_btn.clicked.connect(self.add_variable)

        delete_btn = QPushButton("Удалить")
        delete_btn.clicked.connect(self.delete_variable)

        buttons_layout.addWidget(add_btn)
        buttons_layout.addWidget(delete_btn)
        layout.addLayout(buttons_layout)

        tab.setLayout(layout)
        self.main_tabs.addTab(tab, "Переменные")

    def delete_variable(self):
        """Удаление выбранной переменной"""
        current = self.variables_list.currentItem()
        if current:
            self.variables_list.takeItem(self.variables_list.row(current))

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
        if not current_item.data(Qt.ItemDataRole.UserRole):
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
            ],
            "Stability AI": [
                "stable-diffusion-xl",
                "stable-diffusion-2"
            ]
        }

        for provider, provider_models in models.items():
            provider_item = QListWidgetItem(provider)
            provider_item.setFlags(provider_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            provider_item.setBackground(self.palette().alternateBase())
            self.models_list.addItem(provider_item)

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
        
        # Кнопка Hugging Face
        ru_hf_btn = QPushButton("Выполнить через Hugging Face")
        ru_hf_btn.clicked.connect(lambda: self.show_huggingface_dialog("ru"))
        if not self.hf_api:
            ru_hf_btn.setEnabled(False)
            ru_hf_btn.setToolTip("HuggingFace API недоступен")
            
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
        
        ru_buttons.addWidget(ru_hf_btn)
        ru_buttons.addWidget(ru_lm_btn)
        ru_buttons.addWidget(ru_copy_btn)
        ru_buttons.addWidget(ru_clear_btn)

        ru_layout.addWidget(ru_prompt_group)
        ru_layout.addWidget(ru_result_group)
        ru_layout.addLayout(ru_buttons)
        ru_container.setLayout(ru_layout)

        # Английская вкладка
        en_container = QWidget()
        en_layout = QVBoxLayout()

        # Промпт на английском
        en_prompt_group = QGroupBox("Prompt")
        en_prompt_layout = QVBoxLayout()

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
        
        # Кнопка Hugging Face
        en_hf_btn = QPushButton("Execute with Hugging Face")
        en_hf_btn.clicked.connect(lambda: self.show_huggingface_dialog("en"))
        if not self.hf_api:
            en_hf_btn.setEnabled(False)
            en_hf_btn.setToolTip("HuggingFace API is not available")
            
        # Кнопка LMStudio
        en_lm_btn = QPushButton("Execute with LMStudio")
        en_lm_btn.clicked.connect(lambda: self.show_lmstudio_dialog("en"))
        if not self.lm_api:
            en_lm_btn.setEnabled(False)
            en_lm_btn.setToolTip("LMStudio API is not available")
            
        en_copy_btn = QPushButton("Copy result to prompt")
        en_copy_btn.clicked.connect(lambda: self.copy_result_to_prompt("en"))
        en_clear_btn = QPushButton("Clear")
        en_clear_btn.clicked.connect(lambda: self.clear_content("en"))
        
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

            dialog = HuggingFaceDialog(self.hf_api, user_prompt, self)
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

            dialog = LMStudioDialog(self.lm_api, user_prompt, self)
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
                index = self.category_selector.findData(prompt.category)
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

        # Получаем переменные и преобразуем их в словари
        variables = []
        for i in range(self.variables_list.count()):
            item = self.variables_list.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole):
                variable = item.data(Qt.ItemDataRole.UserRole)
                variables.append(variable.dict())  # Преобразуем в словарь

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
            "category": self.category_selector.currentData(),
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
