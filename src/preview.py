# preview.py
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import (QDialog, QTextEdit, QVBoxLayout, QLabel,
                             QPushButton, QHBoxLayout, QMessageBox, QWidget, QTabWidget,
                             QLineEdit, QFormLayout, QGroupBox)

from src.huggingface_api import HuggingFaceAPI
from src.huggingface_dialog import HuggingFaceDialog
from src.lmstudio_api import LMStudioInference
from src.lmstudio_dialog import LMStudioDialog
from src.prompt_editor import ExampleSelectionDialog


class PromptPreview(QDialog):
    def __init__(self, prompt, settings):
        super().__init__()
        self.prompt = prompt
        self.settings = settings
        self.variable_inputs = {}  # Словарь для хранения полей ввода переменных
        self.ru_history = []  # История изменений для русского текста
        self.en_history = []  # История изменений для английского текста

        # Инициализация API клиентов
        try:
            self.hf_api = HuggingFaceAPI(settings=self.settings)
        except Exception as e:
            self.hf_api = None

        try:
            self.lm_api = LMStudioInference()
        except Exception as e:
            self.lm_api = None

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

        # Variables input
        if self.prompt.variables:
            variables_group = QGroupBox("Заполните переменные:")
            variables_layout = QFormLayout()

            for var in self.prompt.variables:
                input_field = QLineEdit()
                if var.examples:
                    input_field.setPlaceholderText(f"Например: {', '.join(var.examples)}")
                    # Добавляем кнопку для вставки примеров
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

            # Добавляем две кнопки для применения переменных
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
        layout.addWidget(QLabel("Содержание:"))
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
        ru_undo_btn = QPushButton("↩ Отменить")
        ru_undo_btn.clicked.connect(lambda: self.undo_changes("ru"))
        ru_undo_btn.setToolTip("Вернуть к предыдущему состоянию")

        # Добавляем кнопки для выполнения промпта
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
        en_undo_btn = QPushButton("↩ Undo")
        en_undo_btn.clicked.connect(lambda: self.undo_changes("en"))
        en_undo_btn.setToolTip("Revert to previous state")

        # Добавляем кнопки для выполнения промпта
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

        en_container.setLayout(en_layout)
        self.content_tabs.addTab(en_container, "English")

        layout.addWidget(self.content_tabs)

        # Variables info
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
        created_at = self.prompt.created_at.strftime(
            "%d.%m.%Y %H:%M") if self.prompt.created_at else "Не указано"
        updated_at = self.prompt.updated_at.strftime(
            "%d.%m.%Y %H:%M") if self.prompt.updated_at else "Не указано"
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

    def apply_variables(self, lang: str):
        """Применяет введенные значения переменных к тексту промпта указанного языка"""
        if not self.variable_inputs:
            return

        text = self.prompt.content.get(lang, '')
        text_edit = self.ru_content_edit if lang == "ru" else self.en_content_edit
        history = self.ru_history if lang == "ru" else self.en_history

        # Сохраняем текущее состояние в историю
        history.append(text_edit.toPlainText())

        for var_name, input_field in self.variable_inputs.items():
            value = input_field.text().strip()
            if value:
                text = text.replace(f"[{var_name}]", value)

        text_edit.setPlainText(text)
        self.show_toast("Переменные применены!" if lang == "ru" else "Changes applied")

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

    def undo_changes(self, lang: str):
        """Отменить последнее изменение для указанного языка"""
        history = self.ru_history if lang == "ru" else self.en_history
        text_edit = self.ru_content_edit if lang == "ru" else self.en_content_edit

        if history:
            previous_text = history.pop()
            text_edit.setPlainText(previous_text)
            self.show_toast("Изменения отменены" if lang == "ru" else "Changes reverted")

    def show_toast(self, message):
        """Всплывающее уведомление"""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setText(message)
        msg.setWindowTitle(" ")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.show()
        QTimer.singleShot(1500, msg.close)

    def show_examples_dialog(self, variable, input_field):
        """Показать диалог выбора примеров"""
        dialog = ExampleSelectionDialog(variable, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_examples = dialog.get_selected_examples()
            if selected_examples:
                if len(selected_examples) == 1:
                    input_field.setText(selected_examples[0])
                else:
                    input_field.setText(", ".join(selected_examples))

    def execute_prompt(self, lang: str, api: str):
        """Выполнить промпт через выбранный API"""
        try:
            # Получаем текст промпта
            text_edit = self.ru_content_edit if lang == "ru" else self.en_content_edit
            prompt_text = text_edit.toPlainText()

            if not prompt_text.strip():
                QMessageBox.warning(
                    self,
                    "Предупреждение" if lang == "ru" else "Warning",
                    "Введите промпт" if lang == "ru" else "Enter prompt"
                )
                return

            if api == "hf":
                # Для Hugging Face всегда используем режим без улучшения
                dialog = HuggingFaceDialog(self.hf_api, self.settings, prompt_text, self,
                                           from_preview=True)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    result = dialog.get_result()
                    if result:
                        # Сохраняем текущее состояние в историю
                        history = self.ru_history if lang == "ru" else self.en_history
                        history.append(text_edit.toPlainText())
                        # Обновляем текст
                        text_edit.setPlainText(result)
                        self.show_toast(
                            "Результат получен!" if lang == "ru" else "Result received!"
                        )
                    else:
                        QMessageBox.warning(
                            self,
                            "Предупреждение" if lang == "ru" else "Warning",
                            "Получен пустой результат" if lang == "ru" else "Empty result received"
                        )
            else:
                # Для LMStudio
                dialog = LMStudioDialog(prompt_text, self, from_preview=True)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    result = dialog.get_result()
                    if result:
                        # Сохраняем текущее состояние в историю
                        history = self.ru_history if lang == "ru" else self.en_history
                        history.append(text_edit.toPlainText())
                        # Обновляем текст
                        text_edit.setPlainText(result)
                        self.show_toast(
                            "Результат получен!" if lang == "ru" else "Result received!"
                        )
                    else:
                        QMessageBox.warning(
                            self,
                            "Предупреждение" if lang == "ru" else "Warning",
                            "Получен пустой результат" if lang == "ru" else "Empty result received"
                        )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Ошибка" if lang == "ru" else "Error",
                f"Не удалось выполнить промпт: {str(e)}" if lang == "ru" else f"Failed to execute prompt: {str(e)}"
            )

    def add_huggingface_key(self):
        """Добавление или обновление API ключа Hugging Face"""
        try:
            # Получаем текущий ключ
            current_key = self.settings.get_api_key("huggingface")

            # Создаем диалог для ввода ключа
            dialog = QDialog(self)
            dialog.setWindowTitle("API ключ Hugging Face")
            layout = QVBoxLayout()

            # Поле для ввода ключа
            key_label = QLabel("Введите API ключ:")
            key_input = QLineEdit()
            key_input.setEchoMode(QLineEdit.EchoMode.Password)
            if current_key:
                key_input.setPlaceholderText("Введите новый ключ для обновления")
            else:
                key_input.setPlaceholderText("Введите API ключ")

            # Кнопка показать/скрыть ключ
            show_key = QPushButton("Показать ключ")
            show_key.setCheckable(True)
            show_key.clicked.connect(lambda: key_input.setEchoMode(
                QLineEdit.EchoMode.Normal if show_key.isChecked()
                else QLineEdit.EchoMode.Password
            ))

            # Кнопки управления
            buttons = QHBoxLayout()
            save_btn = QPushButton("Сохранить")
            cancel_btn = QPushButton("Отмена")

            # Добавляем виджеты в layout
            layout.addWidget(key_label)
            layout.addWidget(key_input)
            layout.addWidget(show_key)
            buttons.addWidget(save_btn)
            buttons.addWidget(cancel_btn)
            layout.addLayout(buttons)

            dialog.setLayout(layout)

            # Подключаем обработчики
            save_btn.clicked.connect(dialog.accept)
            cancel_btn.clicked.connect(dialog.reject)

            # Показываем диалог
            if dialog.exec() == QDialog.DialogCode.Accepted:
                new_key = key_input.text().strip()
                if new_key:
                    # Сохраняем ключ
                    self.settings.set_api_key("huggingface", new_key)

                    # Пересоздаем API клиент
                    self.hf_api = HuggingFaceAPI(settings=self.settings)

                    # Обновляем UI
                    self.init_ui()

                    QMessageBox.information(
                        self,
                        "Успех",
                        "API ключ успешно сохранен и применен"
                    )
                else:
                    QMessageBox.warning(self, "Ошибка", "API ключ не может быть пустым")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить API ключ: {str(e)}")
