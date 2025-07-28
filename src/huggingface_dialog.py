import logging
from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTextEdit, QComboBox, QMessageBox,
                             QCheckBox, QGroupBox)
from PyQt6.QtGui import QTextCursor
from huggingface_hub import HfApi

from .api_keys_dialog import ApiKeysDialog
from .hf_model_editor_dialog import ModelEditorDialog
from .huggingface_api import HuggingFaceAPI
from .llm_settings import Settings


class Worker(QThread):
    """Поток для выполнения запросов к API"""
    token_received = pyqtSignal(str)  # Сигнал для отправки токенов
    finished = pyqtSignal(str)  # Сигнал о завершении
    error = pyqtSignal(str)  # Сигнал об ошибке

    def __init__(self, api, model_name: str, prompt: str, **kwargs):
        super().__init__()
        self.api = api
        self.model_name = model_name
        self.prompt = prompt
        self.kwargs = kwargs
        self.full_response = ""  # Для хранения полного ответа
        self.logger = logging.getLogger(__name__)

    def run(self):
        try:
            self.logger.info(f"Запуск Worker для модели {self.model_name}")
            self.logger.debug(f"Промпт: {self.prompt}")
            self.logger.debug(f"Параметры: {self.kwargs}")
            
            # Форматируем запрос как сообщение
            messages = [{"role": "user", "content": self.prompt}]
            
            # Получаем генератор токенов
            try:
                for token in self.api.query_model(self.model_name, messages, **self.kwargs):
                    if token:  # Проверяем, что токен не пустой
                        self.full_response += token
                        self.token_received.emit(token)
                        self.logger.debug(f"Получен токен: {token}")
                
                # Отправляем полный ответ по завершении
                if self.full_response:  # Проверяем, что есть что отправлять
                    self.logger.info("Генерация завершена успешно")
                    self.logger.debug(f"Полный ответ: {self.full_response}")
                    self.finished.emit(self.full_response)
                else:
                    raise Exception("Не получено ответа от модели")
                    
            except Exception as e:
                error_msg = f"Ошибка при получении ответа: {str(e)}"
                self.logger.error(error_msg, exc_info=True)
                self.error.emit(error_msg)
                
        except Exception as e:
            error_msg = f"Ошибка в Worker: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            self.error.emit(error_msg)


class HuggingFaceDialog(QDialog):
    """Диалог для работы с Hugging Face API"""

    def __init__(self, api, settings: Settings, prompt: Optional[str] = None,
                 parent=None, from_preview: bool = False):
        super().__init__(parent)
        self.api = api
        self.model_manager = api.model_manager
        self.prompt = prompt
        self.settings = settings
        self.from_preview = from_preview
        self.logger = logging.getLogger(__name__)
        self.current_worker = None

        self.setWindowTitle("Hugging Face API")
        self.setGeometry(100, 100, 800, 600)
        self.setup_ui()

    def setup_ui(self):
        """Настройка интерфейса"""
        layout = QVBoxLayout()

        # ... (Код для 'api_group' и 'model_group' остается без изменений) ...
        api_group = QGroupBox("API ключ")
        api_layout = QHBoxLayout()
        self.api_key_label = QLabel()
        self.update_api_key_label()
        api_layout.addWidget(self.api_key_label)
        self.api_key_button = QPushButton("⚙️")
        self.api_key_button.setFixedWidth(30)
        self.api_key_button.setToolTip("Управление API ключами")
        self.api_key_button.clicked.connect(self.show_api_keys_dialog)
        api_layout.addWidget(self.api_key_button)
        api_group.setLayout(api_layout)
        layout.addWidget(api_group)

        model_group = QGroupBox("Модель")
        model_layout = QVBoxLayout()
        model_controls = QHBoxLayout()
        self.model_combo = QComboBox()
        self.model_combo.addItems(self.api.get_available_models())
        self.model_combo.currentTextChanged.connect(self.update_model_description)
        model_controls.addWidget(self.model_combo)
        buttons_layout = QHBoxLayout()
        self.check_button = QPushButton("Проверить модель")
        self.check_button.clicked.connect(self.check_model)
        buttons_layout.addWidget(self.check_button)
        self.add_model_button = QPushButton("Добавить модель")
        self.add_model_button.clicked.connect(self.add_model)
        buttons_layout.addWidget(self.add_model_button)
        self.edit_model_button = QPushButton("Редактировать")
        self.edit_model_button.clicked.connect(self.edit_model)
        buttons_layout.addWidget(self.edit_model_button)
        model_controls.addLayout(buttons_layout)
        model_layout.addLayout(model_controls)
        self.description_label = QLabel()
        self.description_label.setWordWrap(True)
        self.description_label.setStyleSheet("color: gray;")
        self.update_model_description()
        model_layout.addWidget(self.description_label)
        model_group.setLayout(model_layout)
        layout.addWidget(model_group)

        # Группа запроса
        prompt_group = QGroupBox("Запрос")
        prompt_layout = QVBoxLayout()

        # Улучшение промпта
        improve_layout = QHBoxLayout()
        self.improve_prompt_check = QCheckBox("Улучшить промпт")
        self.improve_prompt_check.setToolTip(
            "Автоматически улучшить промпт перед отправкой модели.\n"
            "Это может помочь получить более качественный ответ,\n"
            "но увеличит время обработки запроса."
        )
        improve_layout.addWidget(self.improve_prompt_check)

        # >>> ИЗМЕНЕНИЕ 1: Добавляем новую кнопку
        self.show_prompt_button = QPushButton("Показать итоговый промпт")
        self.show_prompt_button.setToolTip(
            "Показывает в поле 'Результат' тот промпт, который будет отправлен модели, для его копирования."
        )
        self.show_prompt_button.clicked.connect(self.show_final_prompt)
        improve_layout.addWidget(self.show_prompt_button)

        improve_layout.addStretch()
        prompt_layout.addLayout(improve_layout)

        # Поле для промпта
        if not self.from_preview:
            self.prompt_edit = QTextEdit()
            self.prompt_edit.setPlaceholderText("Введите текст запроса...")
            self.prompt_edit.setMinimumHeight(100)
            if self.prompt:
                self.prompt_edit.setText(self.prompt)
            prompt_layout.addWidget(self.prompt_edit)

            # Кнопка отправки
            send_layout = QHBoxLayout()
            self.process_button = QPushButton("Отправить запрос")
            self.process_button.clicked.connect(self.process_request)
            send_layout.addStretch()
            send_layout.addWidget(self.process_button)
            prompt_layout.addLayout(send_layout)

        prompt_group.setLayout(prompt_layout)
        layout.addWidget(prompt_group)

        # ... (Код для 'result_group' и кнопок диалога остается без изменений) ...
        result_group = QGroupBox("Результат")
        result_layout = QVBoxLayout()
        self.result_edit = QTextEdit()
        self.result_edit.setPlaceholderText("Здесь появится ответ модели...")
        self.result_edit.setReadOnly(True)
        self.result_edit.setMinimumHeight(150)
        result_layout.addWidget(self.result_edit)
        result_group.setLayout(result_layout)
        layout.addWidget(result_group)

        dialog_buttons_layout = QHBoxLayout()
        dialog_buttons_layout.addStretch()
        self.close_button = QPushButton("Закрыть")
        self.close_button.clicked.connect(self.reject)
        dialog_buttons_layout.addWidget(self.close_button)
        layout.addLayout(dialog_buttons_layout)

        self.setLayout(layout)

    def show_final_prompt(self):
        """
        Отображает итоговый промпт в поле результата для копирования.
        """
        try:
            final_prompt = self._get_final_prompt()
            if final_prompt:
                self.result_edit.setText(final_prompt)
                QMessageBox.information(
                    self,
                    "Промпт скопирован",
                    "Итоговый промпт помещен в поле 'Результат'. Теперь вы можете его скопировать."
                )
            else:
                QMessageBox.warning(self, "Ошибка", "Введите текст запроса, чтобы его можно было показать.")
        except Exception as e:
            self.logger.error(f"Ошибка при показе итогового промпта: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Не удалось показать промпт: {e}")

    def _get_final_prompt(self) -> Optional[str]:
        """
        Формирует и возвращает итоговый промпт на основе введенного текста
        и состояния чекбокса "Улучшить промпт".

        Returns:
            Сформированный промпт в виде строки или None, если исходный промпт пуст.
        """
        if self.from_preview:
            base_prompt = self.prompt
        else:
            base_prompt = self.prompt_edit.toPlainText().strip()

        if not base_prompt:
            return None

        if self.improve_prompt_check.isChecked():
            # Возвращаем промпт для улучшения промпта
            return (
                "Ты - опытный эксперт по промпт-инжинирингу. Твоя задача - улучшить следующий промпт, "
                "сделав его более эффективным и структурированным.\n\n"
                "ИСХОДНЫЙ ПРОМПТ:\n"
                f"{base_prompt}\n\n"
                "ИНСТРУКЦИИ ПО УЛУЧШЕНИЮ:\n"
                "1. Определи роль и цель: Четко укажи, какую роль должен играть ИИ и какой результат ожидается\n"
                "2. Добавь контекст: Предоставь необходимую предысторию и условия\n"
                "3. Уточни требования: Укажи конкретные параметры, ограничения и критерии качества\n"
                "4. Структурируй информацию: Используй четкие разделы и маркеры\n"
                "5. Задай формат ответа: Опиши желаемую структуру и стиль ответа\n"
                "6. Добавь примеры: Если уместно, включи образцы желаемого результата\n\n"
                "ВАЖНО:\n"
                "- Сохрани основную цель и смысл исходного промпта\n"
                "- Используй четкий и профессиональный язык\n"
                "- Добавь конкретные метрики успеха\n"
                "- Учитывай возможные ограничения модели\n\n"
                "Пожалуйста, верни только улучшенную версию промпта, без дополнительных пояснений."
            )
        else:
            # Возвращаем исходный промпт как есть
            return base_prompt

    def update_api_key_label(self):
        """Обновляет текст метки API ключа"""
        api_key = self.settings.get_api_key("huggingface")
        if api_key:
            masked_key = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "****"
            self.api_key_label.setText(f"API ключ: {masked_key}")
        else:
            self.api_key_label.setText("API ключ не установлен")

    def show_api_keys_dialog(self):
        """Показать диалог управления API ключами"""
        try:
            dialog = ApiKeysDialog(self.settings, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Пересоздаем API клиент
                self.api = HuggingFaceAPI(settings=self.settings)
                # Обновляем UI
                self.update_api_key_label()
                self.model_combo.clear()
                self.model_combo.addItems(self.api.get_available_models())
                self.update_model_description()
        except Exception as e:
            self.logger.error(f"Ошибка при открытии диалога API ключей: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть диалог: {str(e)}")

    def check_model(self):
        """Проверяет доступность выбранной модели"""
        try:
            model_name = self.model_combo.currentText()
            if not model_name:
                QMessageBox.warning(self, "Ошибка", "Выберите модель для проверки")
                return

            model_id = self.model_manager.get_model_path(model_name)

            # Получаем API ключ
            api_key = self.settings.get_api_key("huggingface")
            if not api_key:
                QMessageBox.warning(self, "Ошибка", "API ключ не установлен")
                return

            # Создаем клиент с API ключом
            api = HfApi(token=api_key)

            # Проверяем существование модели
            try:
                model_info = api.model_info(model_id)
                if model_info:
                    message = (
                        f"Модель {model_id} доступна\n"
                        f"Автор: {model_info.author}\n"
                        f"Лайков: {model_info.likes}\n"
                        f"Последнее обновление: {model_info.last_modified}"
                    )
                    QMessageBox.information(self, "Успех", message)
                else:
                    QMessageBox.warning(self, "Предупреждение", f"Модель {model_id} не найдена")
            except Exception as model_error:
                error_msg = str(model_error)
                if "401" in error_msg:
                    error_msg = (
                        "Ошибка авторизации в Hugging Face API.\n\n"
                        "Возможные причины:\n"
                        "1. API ключ не указан или указан неверно\n"
                        "2. У вас нет доступа к этой модели\n"
                        "3. Модель недоступна для использования через API\n\n"
                        "Рекомендации:\n"
                        "- Проверьте API ключ в настройках\n"
                        "- Убедитесь, что у вас есть доступ к модели\n"
                        "- Попробуйте использовать другую модель"
                    )
                elif "403" in error_msg:
                    error_msg = "У вас нет доступа к этой модели. Возможно, она приватная."
                elif "404" in error_msg:
                    error_msg = "Модель не найдена. Проверьте правильность пути к модели."

                QMessageBox.critical(self, "Ошибка", f"Модель недоступна:\n{error_msg}")

        except Exception as e:
            self.logger.error(f"Ошибка при проверке модели: {str(e)}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось проверить модель: {str(e)}")

    def update_model_description(self):
        """Обновляет описание выбранной модели"""
        try:
            model_name = self.model_combo.currentText()
            if model_name:
                description = self.api.get_model_description(model_name)
                self.description_label.setText(description)
            else:
                self.description_label.setText("")
        except Exception as e:
            self.logger.error(f"Ошибка при получении описания модели: {str(e)}")
            self.description_label.setText("Ошибка при получении описания модели")

    def add_model(self):
        """Открывает диалог добавления модели"""
        try:
            dialog = ModelEditorDialog(self.model_manager, parent=self)
            if dialog.exec():
                self.model_combo.clear()
                self.model_combo.addItems(self.api.get_available_models())
                # Выбираем последнюю добавленную модель
                if self.model_combo.count() > 0:
                    self.model_combo.setCurrentIndex(self.model_combo.count() - 1)
                    self.update_model_description()
        except Exception as e:
            self.logger.error(f"Ошибка при добавлении модели: {str(e)}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось добавить модель: {str(e)}")

    def edit_model(self):
        """Открывает диалог редактирования модели"""
        try:
            model_name = self.model_combo.currentText()
            if not model_name:
                QMessageBox.warning(self, "Ошибка", "Выберите модель для редактирования")
                return

            dialog = ModelEditorDialog(self.model_manager, model_name, parent=self)
            if dialog.exec():
                self.model_combo.clear()
                self.model_combo.addItems(self.api.get_available_models())
                self.update_model_description()
        except Exception as e:
            self.logger.error(f"Ошибка при редактировании модели: {str(e)}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось отредактировать модель: {str(e)}")

    def _handle_improve_response(self, response: str):
        """Обрабатывает ответ с улучшенным промптом"""
        try:
            if response:  # Проверяем, что ответ не пустой
                self.prompt_edit.setText(response)
                self._set_request_controls_enabled(True)
                self.logger.info("Промпт успешно улучшен")
                self.logger.debug(f"Улучшенный промпт: {response}")
                QMessageBox.information(
                    self,
                    "Промпт улучшен",
                    "Промпт был улучшен. Теперь вы можете отправить его модели."
                )
        except Exception as e:
            self.logger.error(f"Ошибка при обработке улучшенного промпта: {str(e)}", exc_info=True)
            self._handle_error(str(e))

    def process_request(self):
        """Обрабатывает запрос к модели"""
        try:
            # Получаем текст запроса
            final_prompt = self._get_final_prompt()
            if not final_prompt:
                QMessageBox.warning(self, "Ошибка", "Введите текст запроса")
                return

            # Получаем выбранную модель
            model_name = self.model_combo.currentText()
            if not model_name:
                QMessageBox.warning(self, "Ошибка", "Выберите модель")
                return

            # Блокируем только элементы управления запросом
            self._set_request_controls_enabled(False)

            # Получаем параметры модели
            params = self.model_manager.get_model_parameters(model_name)
            model_path = self.model_manager.get_model_path(model_name)

            # Корректируем max_new_tokens для phi-2
            if "phi-2" in model_path.lower():
                max_context = 2048
                input_tokens = len(final_prompt) // 4
                max_new_tokens = min(params.get('max_new_tokens', 2048), max_context - input_tokens - 100)
                if max_new_tokens <= 0:
                    QMessageBox.warning(
                        self, "Предупреждение",
                        f"Промпт слишком длинный для модели {model_name}. "
                        f"Максимальная длина контекста: {max_context} токенов"
                    )
                    self._set_request_controls_enabled(True)
                    return
                params['max_new_tokens'] = max_new_tokens
                self.logger.info(f"Скорректирован max_new_tokens для {model_name}: {max_new_tokens}")

            if self.improve_prompt_check.isChecked():
                # Улучшаем промпт
                improve_params = params.copy()
                improve_params['max_new_tokens'] = min(improve_params.get('max_new_tokens', 2048), 1000)

                worker = Worker(self.api, model_name, final_prompt, **improve_params)
                worker.token_received.connect(self._handle_token)
                worker.finished.connect(self._handle_improve_response) # Используем специальный обработчик
                worker.error.connect(self._handle_error)
            else:
                # Отправляем обычный запрос
                worker = Worker(self.api, model_name, final_prompt, **params)
                worker.token_received.connect(self._handle_token)
                worker.finished.connect(self._handle_response) # Обычный обработчик
                worker.error.connect(self._handle_error)

            self.current_worker = worker
            worker.start()
            self.result_edit.clear()

        except Exception as e:
            self.logger.error(f"Ошибка при обработке запроса: {str(e)}")
            QMessageBox.critical(self, "Ошибка", str(e))
            self._set_request_controls_enabled(True)

    def _set_request_controls_enabled(self, enabled: bool):
        """Включает/выключает элементы управления запросом"""
        if not self.from_preview:
            self.prompt_edit.setEnabled(enabled)
            self.process_button.setEnabled(enabled)
        self.improve_prompt_check.setEnabled(enabled)
        self.model_combo.setEnabled(enabled)
        self.add_model_button.setEnabled(enabled)
        self.edit_model_button.setEnabled(enabled)
        self.check_button.setEnabled(enabled)

    def _handle_token(self, token: str):
        """Обрабатывает полученный токен"""
        try:
            if token:  # Проверяем, что токен не пустой
                current_text = self.result_edit.toPlainText()
                self.result_edit.setText(current_text + token)
                # Прокручиваем до конца
                cursor = self.result_edit.textCursor()
                cursor.movePosition(QTextCursor.MoveOperation.End)
                self.result_edit.setTextCursor(cursor)
                self.logger.debug(f"Обработан токен: {token}")
        except Exception as e:
            self.logger.error(f"Ошибка при обработке токена: {str(e)}", exc_info=True)

    def _handle_response(self, response: str):
        """Обрабатывает ответ от модели"""
        try:
            if response:  # Проверяем, что ответ не пустой
                self.result_edit.setText(response)
                self._set_request_controls_enabled(True)
                self.logger.info("Обработка ответа завершена")
                self.logger.debug(f"Финальный ответ: {response}")
        except Exception as e:
            self.logger.error(f"Ошибка при обработке ответа: {str(e)}", exc_info=True)
            self._handle_error(str(e))

    def _handle_error(self, error: str):
        """Обрабатывает ошибку запроса"""
        try:
            self._set_request_controls_enabled(True)
            self.logger.error(f"Ошибка запроса: {error}")
            QMessageBox.critical(self, "Ошибка", error)
        except Exception as e:
            self.logger.error(f"Ошибка при обработке ошибки: {str(e)}", exc_info=True)

    def get_result(self) -> Optional[str]:
        """Возвращает результат обработки"""
        return self.result_edit.toPlainText().strip() or None
