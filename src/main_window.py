# main_window.py
import logging

from PyQt6.QtWidgets import QMainWindow, QListWidget, QVBoxLayout, QWidget, QPushButton, \
    QHBoxLayout, QLineEdit, QLabel, QMessageBox

from prompt_editor import PromptEditor
from prompt_manager import PromptManager


class MainWindow(QMainWindow):
    def __init__(self, prompt_manager: PromptManager):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.prompt_manager = prompt_manager
        self.setWindowTitle("Prompt Manager")
        self.setGeometry(100, 100, 800, 600)

        # UI Components
        self.prompt_list = QListWidget()
        self.search_field = QLineEdit()
        self.add_button = QPushButton("Добавить промпт")
        self.edit_button = QPushButton("Редактировать")
        self.delete_button = QPushButton("Удалить")

        # Layout setup
        main_layout = QHBoxLayout()

        # Left panel (list + search)
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Поиск:"))
        left_layout.addWidget(self.search_field)
        left_layout.addWidget(self.prompt_list)

        # Right panel (buttons)
        button_layout = QVBoxLayout()
        button_layout.addWidget(self.add_button)
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

        # Load initial data
        self.load_prompts()

    def load_prompts(self):
        """Загрузка промптов в список"""
        self.prompt_list.clear()
        for prompt in self.prompt_manager.list_prompts():
            self.prompt_list.addItem(f"{prompt.title} ({prompt.id})")

    def filter_prompts(self):
        """Фильтрация промптов по поисковому запросу"""
        query = self.search_field.text().lower()
        filtered = self.prompt_manager.search_prompts(query)
        self.prompt_list.clear()
        for prompt in filtered:
            self.prompt_list.addItem(f"{prompt.title} ({prompt.id})")

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
