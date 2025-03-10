# main_window.py
import logging

from PyQt6.QtWidgets import QMainWindow, QListWidget, QVBoxLayout, QWidget, QPushButton, \
    QHBoxLayout, QLineEdit, QLabel, QMessageBox, QComboBox

from src.preview import PromptPreview
from src.prompt_editor import PromptEditor
from src.prompt_manager import PromptManager


class MainWindow(QMainWindow):
    def __init__(self, prompt_manager: PromptManager):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.prompt_manager = prompt_manager
        self.setWindowTitle("Prompt Manager")
        self.setGeometry(100, 100, 800, 600)

        # Фильтр по языкам
        self.lang_filter = QComboBox()
        self.lang_filter.addItems(["Все", "RU", "EN"])
        # UI Components
        self.prompt_list = QListWidget()
        self.search_field = QLineEdit()
        self.add_button = QPushButton("Добавить промпт")
        self.preview_button = QPushButton("Просмотр")
        self.edit_button = QPushButton("Редактировать")
        self.delete_button = QPushButton("Удалить")

        # Добавляем выпадающий список категорий
        self.category_filter = QComboBox()
        self.category_filter.addItem("Все категории")
        self.category_filter.currentTextChanged.connect(self.filter_prompts)

        # Layout setup
        main_layout = QHBoxLayout()

        # Left panel (list + search)
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Поиск:"))
        left_layout.addWidget(self.search_field)
        left_layout.addWidget(self.prompt_list)
        # Обновленный layout
        left_layout.addWidget(QLabel("Язык:"))
        left_layout.addWidget(self.lang_filter)
        left_layout.addWidget(QLabel("Категория:"))
        left_layout.addWidget(self.category_filter)

        # Подключение обновленного поиска
        self.lang_filter.currentTextChanged.connect(self.filter_prompts)
        self.category_filter.currentTextChanged.connect(self.filter_prompts)
        # Right panel (buttons)
        button_layout = QVBoxLayout()
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.preview_button)
        button_layout.addWidget(self.edit_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addStretch()

        main_layout.addLayout(left_layout, 4)
        main_layout.addLayout(button_layout, 1)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        # Connect signals
        self.add_button.clicked.connect(self.open_editor)
        self.edit_button.clicked.connect(self.edit_selected)
        self.delete_button.clicked.connect(self.delete_selected)
        self.search_field.textChanged.connect(self.filter_prompts)
        self.prompt_list.itemDoubleClicked.connect(self.edit_selected)
        self.preview_button.clicked.connect(self.preview_selected)

        # Load initial data
        self.load_prompts()

    def load_prompts(self):
        """Загрузка промптов в список с обновлением кэша"""
        self.prompt_list.clear()
        prompts = self.prompt_manager.list_prompts()
        for prompt in prompts:
            self.prompt_list.addItem(f"{prompt.title} ({prompt.id})")
        categories = set()
        for prompt in self.prompt_manager.list_prompts():
            categories.add(prompt.category)
        self.category_filter.clear()
        self.category_filter.addItem("Все категории")
        self.category_filter.addItems(sorted(categories))

    def preview_selected(self):
        """Открытие предпросмотра"""
        selected_item = self.prompt_list.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "Ошибка", "Выберите промпт для просмотра")
            return

        try:
            prompt_id = selected_item.text().split('(')[-1].rstrip(')')
            prompt = self.prompt_manager.get_prompt(prompt_id)
            if prompt:
                preview = PromptPreview(prompt)
                preview.exec()
            else:
                QMessageBox.warning(self, "Ошибка", "Промпт не найден")
        except Exception as e:
            self.logger.error(f"Ошибка предпросмотра: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", "Не удалось открыть предпросмотр")

    def filter_prompts(self):
        """Фильтрация промптов по поисковому запросу"""
        try:
            query = self.search_field.text().lower()
            filtered = self.prompt_manager.search_prompts(query)
            self.prompt_list.clear()
            for prompt in filtered:
                self.prompt_list.addItem(f"{prompt.title} ({prompt.id})")
        except Exception as e:
            self.logger.error(f"Ошибка фильтрации: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Не удалось выполнить поиск {str(e)}")

    def open_editor(self):
        self.logger.debug("Открытие редактора...")
        try:
            editor = PromptEditor(self.prompt_manager)
            if editor.exec():
                self.logger.info("Данные сохранены, обновление списка")
                self.load_prompts()
        except Exception as e:
            self.logger.error("Ошибка в редакторе", exc_info=True)
            QMessageBox.critical(self, "Ошибка", "Не удалось открыть редактор")

    def edit_selected(self):
        """Редактирование выбранного промпта"""
        selected_item = self.prompt_list.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "Ошибка", "Выберите промпт для редактирования")
            return

        prompt_id = selected_item.text().split('(')[-1].rstrip(')')
        editor = PromptEditor(self.prompt_manager, prompt_id)
        if editor.exec():
            self.load_prompts()

    def delete_selected(self):
        """Удаление выбранного промпта"""
        selected_item = self.prompt_list.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "Ошибка", "Выберите промпт для удаления")
            return

        prompt_id = selected_item.text().split('(')[-1].rstrip(')')
        confirm = QMessageBox.question(
            self,
            "Подтверждение",
            "Вы уверены, что хотите удалить этот промпт?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if confirm == QMessageBox.StandardButton.Yes:
            self.prompt_manager.delete_prompt(prompt_id)
            self.load_prompts()
