# preview.py
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import (QDialog, QTextEdit, QVBoxLayout, QLabel,
                             QPushButton, QHBoxLayout, QMessageBox, QWidget, QTabWidget,
                             QLineEdit, QFormLayout, QGroupBox)
from functools import partial
from MarkdownPreviewDialog import MarkdownPreviewDialog
from huggingface_api import HuggingFaceAPI
from huggingface_dialog import HuggingFaceDialog
from lmstudio_api import LMStudioInference
from lmstudio_dialog import LMStudioDialog
from models import Prompt, Variable
from prompt_editor import ExampleSelectionDialog


class PromptPreview(QDialog):
    def __init__(self, prompt: Prompt, settings):
        super().__init__()
        self.prompt = prompt
        self.settings = settings
        self.variable_inputs = {}  # Словарь для хранения полей ввода переменных
        self.ru_history = []  # История изменений для русского текста
        self.en_history = []  # История изменений для английского текста

        self._init_apis()

        self.setWindowTitle("Предпросмотр промпта")
        self.setGeometry(300, 300, 800, 700)  # Увеличена высота

        self.init_ui()
        self.load_data()

    def _init_apis(self):
        # Инициализация API клиентов
        try:
            self.hf_api = HuggingFaceAPI(settings=self.settings)
        except Exception as e:
            self.hf_api = None
        try:
            self.lm_api = LMStudioInference()
        except Exception as e:
            self.lm_api = None

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

        meta_row1 = QHBoxLayout()
        self.version_label = QLabel()
        self.status_label = QLabel()
        self.rating_label = QLabel()
        meta_row1.addWidget(self.version_label)
        meta_row1.addWidget(self.status_label)
        meta_row1.addWidget(self.rating_label)

        meta_row2 = QHBoxLayout()
        self.category_label = QLabel()
        self.tags_label = QLabel()
        meta_row2.addWidget(self.category_label)
        meta_row2.addWidget(self.tags_label)

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

        # Variables input
        if self.prompt.variables:
            variables_group = QGroupBox("Заполните переменные:")
            variables_layout = QFormLayout()

            for var in self.prompt.variables:
                input_field = QLineEdit()
                if var.examples:
                    input_field.setPlaceholderText(f"Например: {', '.join(var.examples)}")
                    input_layout = QHBoxLayout()
                    input_layout.addWidget(input_field)
                    insert_examples_btn = QPushButton("📝")
                    insert_examples_btn.setFixedWidth(30)
                    insert_examples_btn.setToolTip("Вставить примеры")
                    insert_examples_btn.clicked.connect(
                        lambda checked, v=var, f=input_field: self.show_examples_dialog(v, f))
                    input_layout.addWidget(insert_examples_btn)
                    variables_layout.addRow(f"{var.description}:", input_layout)
                else:
                    input_field.setPlaceholderText(f"Введите {var.description}")
                    variables_layout.addRow(f"{var.description}:", input_field)
                self.variable_inputs[var.name] = input_field

            buttons_layout = QHBoxLayout()
            apply_ru_btn = QPushButton("Применить к RU")
            apply_ru_btn.clicked.connect(lambda: self.apply_variables("ru"))
            buttons_layout.addWidget(apply_ru_btn)
            apply_en_btn = QPushButton("Apply to EN")
            apply_en_btn.clicked.connect(lambda: self.apply_variables("en"))
            buttons_layout.addWidget(apply_en_btn)
            variables_layout.addRow("", buttons_layout)

            variables_group.setLayout(variables_layout)
            layout.addWidget(variables_group)

        # Content с табами
        layout.addWidget(QLabel("Основное содержание:"))
        self.content_tabs = QTabWidget()

        ru_container = QWidget()
        ru_layout = QVBoxLayout(ru_container)
        self.ru_content_edit = QTextEdit()
        self.ru_content_edit.setReadOnly(True)
        ru_layout.addWidget(self.ru_content_edit)
        ru_buttons = QHBoxLayout()
        ru_preview_btn = QPushButton("👁️ Просмотр")
        ru_preview_btn.clicked.connect(lambda: self.show_markdown_preview("ru"))
        ru_buttons.addWidget(ru_preview_btn)
        ru_buttons.addStretch()
        ru_copy_btn = QPushButton("Копировать RU")
        ru_copy_btn.clicked.connect(lambda: self.copy_content("ru"))
        ru_undo_btn = QPushButton("↩ Отменить")
        ru_undo_btn.clicked.connect(lambda: self.undo_changes("ru"))
        if self.hf_api:
            ru_hf_btn = QPushButton("Выполнить через Hugging Face")
            ru_hf_btn.clicked.connect(lambda: self.execute_prompt("ru", "hf"))
        else:
            ru_hf_btn = QPushButton("Добавить API ключ Hugging Face")
            ru_hf_btn.clicked.connect(self.add_huggingface_key)
            ru_hf_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        ru_lm_btn = QPushButton("Выполнить через LMStudio")
        ru_lm_btn.clicked.connect(lambda: self.execute_prompt("ru", "lm"))
        if not self.lm_api:
            ru_lm_btn.setEnabled(False)
            ru_lm_btn.setToolTip("LMStudio API недоступен")
        ru_buttons.addWidget(ru_copy_btn)
        ru_buttons.addWidget(ru_undo_btn)
        ru_buttons.addWidget(ru_hf_btn)
        ru_buttons.addWidget(ru_lm_btn)
        ru_layout.addLayout(ru_buttons)
        self.content_tabs.addTab(ru_container, "Русский")

        en_container = QWidget()
        en_layout = QVBoxLayout(en_container)
        self.en_content_edit = QTextEdit()
        self.en_content_edit.setReadOnly(True)
        en_layout.addWidget(self.en_content_edit)
        en_buttons = QHBoxLayout()
        en_preview_btn = QPushButton("👁️ View")
        en_preview_btn.clicked.connect(lambda: self.show_markdown_preview("en"))
        en_buttons.addWidget(en_preview_btn)
        en_buttons.addStretch()
        en_copy_btn = QPushButton("Copy EN")
        en_copy_btn.clicked.connect(lambda: self.copy_content("en"))
        en_undo_btn = QPushButton("↩ Undo")
        en_undo_btn.clicked.connect(lambda: self.undo_changes("en"))
        if self.hf_api:
            en_hf_btn = QPushButton("Execute with Hugging Face")
            en_hf_btn.clicked.connect(lambda: self.execute_prompt("en", "hf"))
        else:
            en_hf_btn = QPushButton("Add Hugging Face API Key")
            en_hf_btn.clicked.connect(self.add_huggingface_key)
            en_hf_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        en_lm_btn = QPushButton("Execute with LMStudio")
        en_lm_btn.clicked.connect(lambda: self.execute_prompt("en", "lm"))
        if not self.lm_api:
            en_lm_btn.setEnabled(False)
            en_lm_btn.setToolTip("LMStudio API is not available")
        en_buttons.addWidget(en_copy_btn)
        en_buttons.addWidget(en_undo_btn)
        en_buttons.addWidget(en_hf_btn)
        en_buttons.addWidget(en_lm_btn)
        en_layout.addLayout(en_buttons)
        self.content_tabs.addTab(en_container, "English")
        layout.addWidget(self.content_tabs)

        # Секция для вариантов промпта
        self.variants_group = QGroupBox("Варианты промпта:")
        self.variants_group.setVisible(False)
        variants_layout = QVBoxLayout(self.variants_group)
        self.variants_tabs = QTabWidget()
        variants_layout.addWidget(self.variants_tabs)
        layout.addWidget(self.variants_group)

        # Author info
        author_layout = QHBoxLayout()
        self.author_label = QLabel()
        self.source_label = QLabel()
        author_layout.addWidget(self.author_label)
        author_layout.addWidget(self.source_label)
        layout.addLayout(author_layout)

        # Buttons
        button_layout = QHBoxLayout()
        self.close_btn = QPushButton("Закрыть")
        self.close_btn.clicked.connect(self.close)
        button_layout.addStretch()
        button_layout.addWidget(self.close_btn)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def load_data(self):
        """Загрузка данных промпта"""
        self.title_label.setText(self.prompt.title)
        self.description_label.setText(self.prompt.description)

        self.version_label.setText(f"Версия: {self.prompt.version}")
        self.status_label.setText(f"Статус: {self.prompt.status}")
        if self.prompt.rating:
            self.rating_label.setText(
                f"Рейтинг: {self.prompt.rating.get('score', 0)} ({self.prompt.rating.get('votes', 0)} голосов)"
            )

        self.category_label.setText(f"Категория: {self.prompt.category}")
        if self.prompt.tags:
            self.tags_label.setText(f"Теги: {', '.join(self.prompt.tags)}")

        created_at = self.prompt.created_at.strftime("%d.%m.%Y %H:%M") if self.prompt.created_at else "Не указано"
        updated_at = self.prompt.updated_at.strftime("%d.%m.%Y %H:%M") if self.prompt.updated_at else "Не указано"
        self.created_at_label.setText(f"Создан: {created_at}")
        self.updated_at_label.setText(f"Изменен: {updated_at}")

        self.models_text.setPlainText(
            ', '.join(self.prompt.compatible_models) if self.prompt.compatible_models else "Не указаны"
        )

        if isinstance(self.prompt.content, dict):
            self.ru_content_edit.setPlainText(self.prompt.content.get('ru', "Нет русского контента"))
            self.en_content_edit.setPlainText(self.prompt.content.get('en', "No English content"))
        else:
            self.ru_content_edit.setPlainText(str(self.prompt.content))
            self.en_content_edit.setPlainText("No English content")

        if hasattr(self.prompt, 'prompt_variants') and self.prompt.prompt_variants:
            self.variants_group.setVisible(True)
            self.variants_tabs.clear()

            for i, variant in enumerate(self.prompt.prompt_variants):
                variant_widget = QWidget()
                variant_layout = QVBoxLayout(variant_widget)
                info_text = (
                    f"Тип: {variant.variant_id.type}, "
                    f"ID: {variant.variant_id.id}, "
                    f"Приоритет: {variant.variant_id.priority}"
                )
                info_label = QLabel(info_text)
                info_label.setStyleSheet("font-weight: bold; color: #333;")
                variant_layout.addWidget(info_label)

                content_edit = QTextEdit()
                content_edit.setReadOnly(True)

                ru_content = variant.content.get('ru', '')
                en_content = variant.content.get('en', '')
                full_content_text = []
                if ru_content:
                    full_content_text.append(f"--- RU ---\n{ru_content}")
                if en_content:
                    full_content_text.append(f"--- EN ---\n{en_content}")

                content_edit.setPlainText("\n\n".join(full_content_text).strip())
                variant_layout.addWidget(content_edit)

                # --- ИЗМЕНЕНИЯ ЗДЕСЬ ---
                # Создаем горизонтальный layout для кнопок
                button_layout = QHBoxLayout()
                button_layout.addStretch() # Прижимаем кнопки к правому краю

                # Кнопка просмотра Markdown
                preview_variant_btn = QPushButton("👁️ Просмотр")
                preview_variant_btn.setToolTip("Просмотреть контент варианта как Markdown")
                # Для просмотра мы можем просто объединить русский и английский текст
                combined_markdown = f"# Русский вариант\n\n{ru_content}\n\n---\n\n# Английский вариант\n\n{en_content}"
                # Используем аргументы по умолчанию для захвата текущих значений
                preview_variant_btn.clicked.connect(
                    lambda checked, text=combined_markdown, index=i: self.show_markdown_preview_for_variant(text, index + 1)
                )
                button_layout.addWidget(preview_variant_btn)

                # Кнопка копирования для этого варианта
                copy_variant_btn = QPushButton(f"Копировать")
                copy_variant_btn.setToolTip("Копировать текст этого варианта")
                copy_variant_btn.clicked.connect(
                    lambda checked, text=content_edit.toPlainText(): self.copy_text(text)
                )
                button_layout.addWidget(copy_variant_btn)

                variant_layout.addLayout(button_layout)

                tab_title = f"Вариант {i + 1} ({variant.variant_id.type})"
                self.variants_tabs.addTab(variant_widget, tab_title)

        if self.prompt.metadata:
            author_data = self.prompt.metadata.get('author', {})
            author_name = author_data.get('name', 'Не указан')
            self.author_label.setText(f"Автор: {author_name}")
            source = self.prompt.metadata.get('source', '')
            if source:
                self.source_label.setText(f"Источник: {source}")
                self.source_label.show()
            else:
                self.source_label.hide()

    def show_markdown_preview_for_variant(self, markdown_text: str, variant_index: int):
        """
        Открывает диалог предпросмотра Markdown для контента конкретного варианта.
        """
        title = f"Просмотр: {self.prompt.title} (Вариант {variant_index})"
        dialog = MarkdownPreviewDialog(markdown_text, window_title=title, parent=self)
        dialog.exec()

    def copy_text(self, text: str, message: str = "Текст скопирован в буфер!"):
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(text)
        self.show_toast(message)

    def apply_variables(self, lang: str):
        if not self.variable_inputs:
            return
        if isinstance(self.prompt.content, dict):
            text = self.prompt.content.get(lang, '')
        else: # Обработка старого формата
            text = str(self.prompt.content) if lang == 'ru' else ''

        text_edit = self.ru_content_edit if lang == "ru" else self.en_content_edit
        history = self.ru_history if lang == "ru" else self.en_history
        history.append(text_edit.toPlainText())

        for var_name, input_field in self.variable_inputs.items():
            value = input_field.text().strip()
            if value:
                text = text.replace(f"[{var_name}]", value)

        text_edit.setPlainText(text)
        self.show_toast("Переменные применены!" if lang == "ru" else "Variables applied!")

    def copy_content(self, lang: str):
        text_edit = self.ru_content_edit if lang == "ru" else self.en_content_edit
        message = "Русский контент скопирован!" if lang == "ru" else "English content copied!"
        self.copy_text(text_edit.toPlainText(), message)

    def undo_changes(self, lang: str):
        history = self.ru_history if lang == "ru" else self.en_history
        text_edit = self.ru_content_edit if lang == "ru" else self.en_content_edit
        if history:
            previous_text = history.pop()
            text_edit.setPlainText(previous_text)
            self.show_toast("Изменения отменены" if lang == "ru" else "Changes reverted")

    def show_toast(self, message):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setText(message)
        msg.setWindowTitle(" ")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.show()
        QTimer.singleShot(1500, msg.close)

    def show_examples_dialog(self, variable: Variable, input_field: QLineEdit):
        dialog = ExampleSelectionDialog(variable, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_examples = dialog.get_selected_examples()
            if selected_examples:
                input_field.setText(", ".join(selected_examples))

    def execute_prompt(self, lang: str, api: str):
        try:
            text_edit = self.ru_content_edit if lang == "ru" else self.en_content_edit
            prompt_text = text_edit.toPlainText()
            if not prompt_text.strip():
                QMessageBox.warning(self, "Предупреждение", "Промпт не может быть пустым.")
                return

            if api == "hf":
                dialog = HuggingFaceDialog(self.hf_api, self.settings, prompt_text, self, from_preview=True)
            elif api == "lm":
                dialog = LMStudioDialog(prompt_text, self, from_preview=True)
            else:
                return

            if dialog.exec() == QDialog.DialogCode.Accepted:
                result = dialog.get_result()
                if result:
                    history = self.ru_history if lang == "ru" else self.en_history
                    history.append(text_edit.toPlainText())
                    text_edit.setPlainText(result)
                    self.show_toast("Результат получен!")
                else:
                    QMessageBox.warning(self, "Предупреждение", "Получен пустой результат.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось выполнить промпт: {e}")

    def show_markdown_preview(self, lang: str):
        text_edit = self.ru_content_edit if lang == "ru" else self.en_content_edit
        title = f"Просмотр: {self.prompt.title} ({'RU' if lang == 'ru' else 'EN'})"
        dialog = MarkdownPreviewDialog(text_edit.toPlainText(), window_title=title, parent=self)
        dialog.exec()

    def add_huggingface_key(self):
        try:
            current_key = self.settings.get_api_key("huggingface")
            dialog = QDialog(self)
            dialog.setWindowTitle("API ключ Hugging Face")
            layout = QVBoxLayout()
            key_label = QLabel("Введите API ключ:")
            key_input = QLineEdit()
            key_input.setEchoMode(QLineEdit.EchoMode.Password)
            key_input.setPlaceholderText("Введите API ключ" if not current_key else "Введите новый ключ для обновления")
            show_key = QPushButton("Показать ключ")
            show_key.setCheckable(True)
            show_key.clicked.connect(lambda: key_input.setEchoMode(
                QLineEdit.EchoMode.Normal if show_key.isChecked() else QLineEdit.EchoMode.Password
            ))
            buttons = QHBoxLayout()
            save_btn = QPushButton("Сохранить")
            cancel_btn = QPushButton("Отмена")
            layout.addWidget(key_label)
            layout.addWidget(key_input)
            layout.addWidget(show_key)
            buttons.addWidget(save_btn)
            buttons.addWidget(cancel_btn)
            layout.addLayout(buttons)
            dialog.setLayout(layout)
            save_btn.clicked.connect(dialog.accept)
            cancel_btn.clicked.connect(dialog.reject)

            if dialog.exec() == QDialog.DialogCode.Accepted:
                new_key = key_input.text().strip()
                if new_key:
                    self.settings.set_api_key("huggingface", new_key)
                    self._init_apis() # Пересоздаем API клиент
                    # Полностью перестраиваем UI, чтобы обновить кнопки
                    # Удаляем старый layout
                    while self.layout().count():
                        child = self.layout().takeAt(0)
                        if child.widget():
                            child.widget().deleteLater()
                    # Создаем новый
                    self.init_ui()
                    self.load_data()
                    QMessageBox.information(self, "Успех", "API ключ успешно сохранен и применен.")
                else:
                    QMessageBox.warning(self, "Ошибка", "API ключ не может быть пустым.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить API ключ: {e}")